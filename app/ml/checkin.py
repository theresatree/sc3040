import asyncio
import os

import numpy as np

from concurrent.futures import ThreadPoolExecutor

from app.ml.operations import check_in_test


def match_kps(box: np.ndarray, bboxes: np.ndarray, kpss: np.ndarray) -> np.ndarray:
    """Pick the kps of the raw detection that best overlaps a tracked box."""
    x1, y1, x2, y2 = map(int, box[:4])
    bx1, by1, bx2, by2 = bboxes[:, :4].T
    ix = np.maximum(0, np.minimum(x2, bx2) - np.maximum(x1, bx1))
    iy = np.maximum(0, np.minimum(y2, by2) - np.maximum(y1, by1))
    inter = ix * iy
    union = (x2 - x1) * (y2 - y1) + (bx2 - bx1) * (by2 - by1) - inter
    return kpss[int(np.argmax(inter / np.maximum(union, 1e-6)))]


class CheckInProcessor:
    """
    Async pipeline for websocket check-in testing.

    Producer (the websocket loop) submits face samples via submit().
    A single consumer task drains the queue and runs
    app.ml.operations.check_in_test() on a thread pool, maintaining
    per-track similarity/streak/spoof state and confirming a match
    after FOCUS_FRAMES consecutive matches.
    """

    def __init__(
        self,
        state,
        user_iom_embedding: np.ndarray,
        projection: np.ndarray,
        workers: int | None = None,
        queue_size: int = 8,
        focus_frames: int = 15,
        threshold: float = 0.5,
        max_spoof_attempts: int = 3,
    ):
        self.state = state
        self.user_iom_embedding = user_iom_embedding
        self.projection = projection
        self.focus_frames = focus_frames
        self.threshold = threshold
        self.max_spoof_attempts = max_spoof_attempts

        if workers is None:
            det_providers = state.detector.session.get_providers()
            on_gpu = any("CUDA" in p.upper() for p in det_providers)
            workers = 1 if on_gpu else max(1, os.cpu_count() - 2)

        self.workers = workers
        self.pool = ThreadPoolExecutor(max_workers=workers)
        self.queue: asyncio.Queue = asyncio.Queue(maxsize=queue_size)
        self.loop = asyncio.get_running_loop()
        self._task: asyncio.Task | None = None

        self.track_sims: dict[int, float] = {}
        self.track_streaks: dict[int, int] = {}
        self.track_spoof: dict[int, bool] = {}
        self.confirm_track_id: int | None = None
        self.confirm_similarity = 0.0

        self.spoof_attempts = 0
        self.spoof_blocked = False

    def start(self) -> None:
        self._task = asyncio.create_task(self._consumer())

    async def stop(self) -> None:
        if self._task is not None:
            self._task.cancel()
        self.pool.shutdown(wait=False)

    def submit(self, data: bytes, box: np.ndarray, kps: np.ndarray, track_id: int) -> None:
        try:
            self.queue.put_nowait((data, box, kps, track_id))
        except asyncio.QueueFull:
            pass

    @property
    def attempts_remaining(self) -> int:
        return max(0, self.max_spoof_attempts - self.spoof_attempts)

    def _test(self, data: bytes, box: np.ndarray, kps: np.ndarray) -> tuple[float, bool]:
        return check_in_test(
            data,
            self.state,
            box,
            kps,
            self.user_iom_embedding,
            self.projection,
        )

    async def _consumer(self) -> None:
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
                        self.pool, self._test, data, box, kps
                    )
                    for (data, box, kps, _track_id) in batch
                ],
                return_exceptions=True,
            )

            for (data, box, kps, track_id), res in zip(batch, results):
                if isinstance(res, Exception):
                    sim, spoofed = -1.0, False
                else:
                    sim, spoofed = res

                self.track_sims[track_id] = sim
                self.track_spoof[track_id] = spoofed

                if spoofed:
                    self.spoof_attempts += 1
                    if self.spoof_attempts >= self.max_spoof_attempts:
                        self.spoof_blocked = True

                streak = self.track_streaks.get(track_id, 0)
                streak = streak + 1 if sim >= self.threshold else 0
                self.track_streaks[track_id] = streak

                if streak >= self.focus_frames and self.confirm_track_id is None:
                    self.confirm_track_id = track_id
                    self.confirm_similarity = sim
