from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import insightface
import onnxruntime as ort
import logging
import traceback

from app.routers.users import router as users_router
from app.routers.rooms import router as rooms_router
from app.routers.timetables import router as timetables_router
from app.routers.registrations import router as registrations_router
from app.routers.auth import router as auth_router
from app.routers.attendance import router as attendance_router

CPU = True  # Set to False if you want to use GPU

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Starting model loading...", flush=True)

    model_dir = "/app/ml_models"
    ctx_id = -1 if CPU else 0

    print("Loading face detector...", flush=True)
    detector = insightface.model_zoo.get_model(
        f"{model_dir}/det_10g.onnx"
    )
    detector.prepare(ctx_id=ctx_id)  # type: ignore
    print("Face detector loaded.", flush=True)

    # print("Loading 2D landmarks model...", flush=True)
    # landmark_2d = insightface.model_zoo.get_model(
    #     f"{model_dir}/2d106det.onnx"
    # )
    # landmark_2d.prepare(ctx_id=ctx_id)  # type: ignore
    # print("2D landmarks model loaded.", flush=True)

    print("Loading 3D landmarks model...", flush=True)
    landmark = insightface.model_zoo.get_model(
        f"{model_dir}/1k3d68.onnx"
    )
    landmark.prepare(ctx_id=ctx_id)  # type: ignore
    print("3D landmarks model loaded.", flush=True)

    print("Loading face recognition model...", flush=True)
    recognizer = insightface.model_zoo.get_model(
        f"{model_dir}/w600k_r50.onnx"
    )
    recognizer.prepare(ctx_id=ctx_id)  # type: ignore
    print("Face recognition model loaded.", flush=True)

    print("Loading age/gender model...", flush=True)
    gender_age = insightface.model_zoo.get_model(
        f"{model_dir}/genderage.onnx"
    )
    gender_age.prepare(ctx_id=ctx_id)  # type: ignore
    print("Age/gender model loaded.", flush=True)

    print("Loading anti-spoofing model...", flush=True)
    spoofing = ort.InferenceSession(
        f"{model_dir}/spoofing_model.onnx",
        providers=["CPUExecutionProvider"],
    )
    print("Anti-spoofing model loaded.", flush=True)

    app.state.detector = detector
    # app.state.landmark_2d = landmark_2d
    app.state.landmark = landmark
    app.state.recognizer = recognizer
    app.state.gender_age = gender_age
    app.state.spoofing = spoofing

    print("All face models loaded. Application ready.", flush=True)

    yield

    print("Shutting down face models...", flush=True)


app = FastAPI(lifespan=lifespan)

logger = logging.getLogger("uvicorn.error")


@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError):
    return JSONResponse(status_code=400, content={"detail": str(exc)})


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.error(traceback.format_exc())
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal Server Error"},
    )


app.include_router(users_router)
app.include_router(rooms_router)
app.include_router(timetables_router)
app.include_router(registrations_router)
app.include_router(auth_router)
app.include_router(attendance_router)
