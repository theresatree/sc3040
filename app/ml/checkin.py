import asyncio
import os
from concurrent.futures import ThreadPoolExecutor

import numpy as np

from app.ml.operations import check_in_test


def match_detection(
    tracked_box: np.ndarray,
    bboxes: np.ndarray,
    kpss: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    """Match ByteTrack box to the original Buffalo detection."""
    x1, y1, x2, y2 = map(int, tracked_box[:4])
    bx1, by1, bx2, by2 = bboxes[:, :4].T

    ix = np.maximum(0, np.minimum(x2, bx2) - np.maximum(x1, bx1))
    iy = np.maximum(0, np.minimum(y2, by2) - np.maximum(y1, by1))
    inter = ix * iy

    tracked_area = max(0, x2 - x1) * max(0, y2 - y1)
    buffalo_area = (bx2 - bx1) * (by2 - by1)
    union = tracked_area + buffalo_area - inter

    idx = int(np.argmax(inter / np.maximum(union, 1e-6)))
    return bboxes[idx], kpss[idx]


def decode_and_detect(data: bytes, detector):
    import cv2

    frame = cv2.imdecode(
        np.frombuffer(data, dtype=np.uint8),
        cv2.IMREAD_COLOR,
    )

    if frame is None:
        return None, None, None

    bboxes, kpss = detector.detect(
        frame,
        max_num=0,
        metric="default",
    )

    return frame, bboxes, kpss


class CheckInProcessor:
    def __init__(
        self,
        state,
        user_iom_embedding: np.ndarray,
        projection: np.ndarray,
        workers: int | None = None,
        queue_size: int = 8,
        focus_frames: int = 10,
        threshold: float = 0.45,
        max_spoof_attempts: int = 2,
        lock_release_misses: int = 2,
    ):
        self.state = state
        self.user_iom_embedding = user_iom_embedding
        self.projection = projection
        self.focus_frames = focus_frames
        self.threshold = threshold
        self.max_spoof_attempts = max_spoof_attempts
        self.lock_release_misses = lock_release_misses

        if workers is None:
            providers = state.detector.session.get_providers()
            on_gpu = any("CUDA" in p.upper() for p in providers)
            workers = 1 if on_gpu else max(1, os.cpu_count() - 2)

        self.workers = workers
        self.pool = ThreadPoolExecutor(max_workers=workers)
        self.queue = asyncio.Queue(maxsize=queue_size)
        self.loop = asyncio.get_running_loop()
        self._task = None

        self.track_sims = {}
        self.track_streaks = {}
        self.track_spoof = {}

        self.locked_track_id = None
        self._lock_misses = 0

        self.confirm_track_id = None
        self.confirm_similarity = 0.0

        self.spoof_attempts = 0
        self.spoof_blocked = False

    def start(self):
        self._task = asyncio.create_task(self._consumer())

    async def stop(self):
        if self._task:
            self._task.cancel()
        self.pool.shutdown(wait=False)

    def submit(self, data, box, kps, track_id):
        try:
            self.queue.put_nowait((data, box, kps, track_id))
        except asyncio.QueueFull:
            pass

    def note_visible_tracks(self, track_ids: set[int]):
        if self.locked_track_id is None:
            return

        if self.locked_track_id not in track_ids:
            self._lock_misses += 1

            if self._lock_misses >= self.lock_release_misses:
                self.locked_track_id = None
                self._lock_misses = 0

    @property
    def attempts_remaining(self):
        return max(
            0,
            self.max_spoof_attempts - self.spoof_attempts,
        )

    def _test(self, data, box, kps):
        return check_in_test(
            data,
            self.state,
            box,
            kps,
            self.user_iom_embedding,
            self.projection,
        )

    async def _consumer(self):
        while True:
            batch = [await self.queue.get()]

            while len(batch) < self.workers:
                try:
                    batch.append(self.queue.get_nowait())
                except asyncio.QueueEmpty:
                    break

            results = await asyncio.gather(
                *[
                    self.loop.run_in_executor(
                        self.pool,
                        self._test,
                        data,
                        box,
                        kps,
                    )
                    for data, box, kps, _ in batch
                ],
                return_exceptions=True,
            )

            for (data, box, kps, track_id), result in zip(batch, results):
                if isinstance(result, Exception):
                    sim, spoofed = -1.0, False
                else:
                    sim, spoofed = result

                self.track_sims[track_id] = sim
                self.track_spoof[track_id] = spoofed

                if spoofed:
                    self.spoof_attempts += 1

                    if self.spoof_attempts >= self.max_spoof_attempts:
                        self.spoof_blocked = True

                streak = self.track_streaks.get(track_id, 0)
                self.track_streaks[track_id] = (
                    streak + 1 if sim >= self.threshold else 0
                )

                if sim >= self.threshold:
                    if self.locked_track_id == track_id:
                        self._lock_misses = 0
                    elif self.locked_track_id is None:
                        self.locked_track_id = track_id
                        self._lock_misses = 0

                elif track_id == self.locked_track_id:
                    self._lock_misses += 1

                    if self._lock_misses >= self.lock_release_misses:
                        self.locked_track_id = None
                        self._lock_misses = 0

                if (
                    self.track_streaks[track_id] >= self.focus_frames
                    and self.confirm_track_id is None
                ):
                    self.confirm_track_id = track_id
                    self.confirm_similarity = sim
