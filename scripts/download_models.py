from pathlib import Path
from urllib.request import urlopen
import zipfile

from tqdm import tqdm


MODEL_DIR = Path(__file__).resolve().parent.parent / "ml_models"
MODEL_DIR.mkdir(parents=True, exist_ok=True)


# ── InsightFace buffalo_l ─────────────────────────────

INSIGHTFACE_URL = (
    "https://github.com/deepinsight/insightface"
    "/releases/download/v0.7/buffalo_l.zip"
)

INSIGHTFACE_ZIP = MODEL_DIR / "buffalo_l.zip"
INSIGHTFACE_DIR = MODEL_DIR / "buffalo_l"


if INSIGHTFACE_DIR.exists():
    print("InsightFace buffalo_l already exists.", flush=True)
else:
    print("Downloading InsightFace buffalo_l...", flush=True)

    with urlopen(INSIGHTFACE_URL) as response:
        total = int(response.headers.get("Content-Length", 0))

        with open(INSIGHTFACE_ZIP, "wb") as f:
            with tqdm(
                total=total,
                unit="B",
                unit_scale=True,
                desc="buffalo_l",
            ) as progress:
                while chunk := response.read(8192):
                    f.write(chunk)
                    progress.update(len(chunk))

    print("Extracting InsightFace buffalo_l...", flush=True)

    with zipfile.ZipFile(INSIGHTFACE_ZIP, "r") as zip_ref:
        zip_ref.extractall(MODEL_DIR)

    INSIGHTFACE_ZIP.unlink()

    print("InsightFace buffalo_l ready.", flush=True)


# ── Anti-spoofing model ───────────────────────────────

SPOOF_URL = (
    "https://github.com/facenox/face-antispoof-onnx"
    "/releases/download/v1.0.0/best_model_quantized.onnx"
)

SPOOF_PATH = MODEL_DIR / "spoofing_model.onnx"


if SPOOF_PATH.exists():
    print("Anti-spoofing model already exists.", flush=True)
else:
    print("Downloading anti-spoofing model...", flush=True)

    with urlopen(SPOOF_URL) as response:
        total = int(response.headers.get("Content-Length", 0))

        with open(SPOOF_PATH, "wb") as f:
            with tqdm(
                total=total,
                unit="B",
                unit_scale=True,
                desc="anti-spoof",
            ) as progress:
                while chunk := response.read(8192):
                    f.write(chunk)
                    progress.update(len(chunk))

    print("Anti-spoofing model downloaded.", flush=True)


print("All models ready.", flush=True)
