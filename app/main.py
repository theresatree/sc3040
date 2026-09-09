import onnxruntime
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging
import traceback
from pathlib import Path

from app.ml.state import load_models

from app.routers.users import router as users_router
from app.routers.timetables import router as timetables_router
from app.routers.auth import router as auth_router
from app.routers.attendance import router as attendance_router
from app.routers.register import router as register_router

CPU = True  # Set to False if you want to use GPU

# Silence onnxruntime's per-inference dynamic-shape noise (e.g. det_10g's
# VerifyOutputSizes). Severity 3 = errors only; must be set before sessions.
onnxruntime.set_default_logger_severity(3)

PROVIDERS = (
    ["CPUExecutionProvider"]
    if CPU
    else ["CUDAExecutionProvider", "CPUExecutionProvider"]
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Starting model loading...", flush=True)

    model_dir = str(Path(__file__).resolve().parent.parent / "ml_models")
    model_dir = str(Path(__file__).resolve().parent.parent / "ml_models")
    models = load_models(model_dir, cpu=CPU)


    app.state.detector = models.detector
    app.state.landmark = models.landmark
    app.state.recognizer = models.recognizer
    app.state.gender_age = models.gender_age
    app.state.spoofing = models.spoofing
    print("All face models loaded. Application ready.", flush=True)

    yield

    print("Shutting down face models...", flush=True)


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

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
app.include_router(timetables_router)
app.include_router(auth_router)
app.include_router(attendance_router)
app.include_router(register_router)

app.mount(
    "/",
    StaticFiles(directory="static", html=True),
    name="static",
)
