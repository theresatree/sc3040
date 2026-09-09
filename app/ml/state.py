from dataclasses import dataclass
from pathlib import Path

import insightface
import onnxruntime as ort


@dataclass
class ModelState:
    detector: object
    landmark: object
    recognizer: object
    gender_age: object
    spoofing: object


def load_models(model_dir: str, cpu: bool = True) -> ModelState:
    ctx_id = -1 if cpu else 0
    providers = (
        ["CPUExecutionProvider"]
        if cpu
        else ["CUDAExecutionProvider", "CPUExecutionProvider"]
    )

    print("Loading face detector...", flush=True)
    detector = insightface.model_zoo.get_model(f"{model_dir}/det_10g.onnx", providers=providers)
    detector.prepare(ctx_id=ctx_id) # type: ignore

    print("Loading 3D landmarks model...", flush=True)
    landmark = insightface.model_zoo.get_model(f"{model_dir}/1k3d68.onnx", providers=providers)
    landmark.prepare(ctx_id=ctx_id) # type: ignore

    print("Loading face recognition model...", flush=True)
    recognizer = insightface.model_zoo.get_model(f"{model_dir}/w600k_r50.onnx", providers=providers)
    recognizer.prepare(ctx_id=ctx_id) # type: ignore

    print("Loading age/gender model...", flush=True)
    gender_age = insightface.model_zoo.get_model(f"{model_dir}/genderage.onnx", providers=providers)
    gender_age.prepare(ctx_id=ctx_id) #type: ignore

    print("Loading anti-spoofing model...", flush=True)
    spoofing = ort.InferenceSession(f"{model_dir}/spoofing_model.onnx", providers=["CPUExecutionProvider"])

    print("All face models loaded.", flush=True)
    return ModelState(
        detector=detector,
        landmark=landmark,
        recognizer=recognizer,
        gender_age=gender_age,
        spoofing=spoofing,
    )
