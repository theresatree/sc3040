"""
FastAPI WebSocket endpoint for face detection + tracking.

Client sends raw JPEG/PNG-encoded frame bytes over the WebSocket.
Server decodes each frame, runs det_10g.onnx (buffalo_l detector) +
ByteTrackTracker, and sends back JSON with per-face boxes and
persistent track IDs.

Requirements:
    pip install fastapi uvicorn[standard] trackers insightface onnxruntime opencv-python supervision

Run:
    uvicorn server:app --reload
"""

import json

import cv2
import numpy as np
import supervision as sv
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from insightface.model_zoo import model_zoo
from trackers import ByteTrackTracker

MODEL_PATH = "ml_models/det_10g.onnx"

# Number of consecutive frames a single track_id must appear in before
# it's considered "confirmed".
CONFIRM_FRAMES = 30

app = FastAPI()

# Load the detector once at startup and reuse it across all connections.
detector = model_zoo.get_model(MODEL_PATH)
detector.prepare(ctx_id=0, input_size=(640, 640))  # ctx_id=-1 to force CPU


@app.websocket("/ws/track")
async def track_ws(websocket: WebSocket):
    await websocket.accept()

    # One tracker per connection -- track IDs shouldn't be shared across
    # different clients/sessions, since ByteTrack keeps internal state
    # (Kalman filters, track history) tied to a single continuous stream.
    tracker = ByteTrackTracker()

    # Per-connection: how many consecutive frames each track_id has appeared in.
    # A track_id missing from a frame gets its count reset to 0 (see below),
    # so this only counts truly continuous appearances -- not ByteTrack's
    # internal "lost but not yet removed" buffer.
    streak_counts: dict[int, int] = {}

    try:
        while True:
            # Expect each message to be raw encoded image bytes (e.g. JPEG)
            data = await websocket.receive_bytes()

            frame = cv2.imdecode(np.frombuffer(data, dtype=np.uint8), cv2.IMREAD_COLOR)
            if frame is None:
                await websocket.send_text(
                    json.dumps({"error": "could not decode frame"})
                )
                continue

            bboxes, _ = detector.detect(frame, max_num=0, metric="default")

            tracks = []
            current_ids = set()

            if len(bboxes) > 0:
                boxes = bboxes[:, :4]
                scores = bboxes[:, 4]

                detections = sv.Detections(xyxy=boxes, confidence=scores)
                tracked = tracker.update(detections)

                for box, track_id, score in zip(
                    tracked.xyxy, tracked.tracker_id, tracked.confidence
                ):
                    track_id = int(track_id)
                    current_ids.add(track_id)

                    streak_counts[track_id] = streak_counts.get(track_id, 0) + 1
                    confirmed = streak_counts[track_id] >= CONFIRM_FRAMES

                    x1, y1, x2, y2 = box.tolist()
                    tracks.append(
                        {
                            "track_id": track_id,
                            "bbox": [x1, y1, x2, y2],
                            "confidence": float(score),
                            "streak": streak_counts[track_id],
                            "confirmed": confirmed,
                        }
                    )

            # Reset the streak for any track_id that didn't appear this frame,
            # so "confirmed" only reflects truly continuous presence.
            for stale_id in list(streak_counts.keys()):
                if stale_id not in current_ids:
                    del streak_counts[stale_id]

            await websocket.send_text(json.dumps({"tracks": tracks}))

            confirmed_track = next((t for t in tracks if t["confirmed"]), None)
            if confirmed_track is not None:
                await websocket.close(
                    code=1000,
                    reason=f"confirmed track_id={confirmed_track['track_id']}",
                )
                return

    except WebSocketDisconnect:
        pass
