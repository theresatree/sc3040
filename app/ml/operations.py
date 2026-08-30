import cv2
import numpy as np
from insightface.app.common import Face

# _crop_face() and _preprocess() is needed for the spoofing.

def _crop_face(img: np.ndarray, bbox: tuple, expansion: float) -> np.ndarray:
    """Extract square face crop from bbox with expansion. Pad edges with reflection."""
    original_height, original_width = img.shape[:2]
    x, y, w, h = bbox

    w = w - x
    h = h - y

    if w <= 0 or h <= 0:
        raise ValueError("Invalid bbox dimensions")

    max_dim = max(w, h)
    center_x = x + w / 2
    center_y = y + h / 2

    x = int(center_x - max_dim * expansion / 2)
    y = int(center_y - max_dim * expansion / 2)
    crop_size = int(max_dim * expansion)

    crop_x1 = max(0, x)
    crop_y1 = max(0, y)
    crop_x2 = min(original_width, x + crop_size)
    crop_y2 = min(original_height, y + crop_size)

    top_pad = int(max(0, -y))
    left_pad = int(max(0, -x))
    bottom_pad = int(max(0, (y + crop_size) - original_height))
    right_pad = int(max(0, (x + crop_size) - original_width))

    if crop_x2 > crop_x1 and crop_y2 > crop_y1:
        img = img[crop_y1:crop_y2, crop_x1:crop_x2, :]
    else:
        img = np.zeros((0, 0, 3), dtype=img.dtype)

    result = cv2.copyMakeBorder(
        img,
        top_pad,
        bottom_pad,
        left_pad,
        right_pad,
        cv2.BORDER_REFLECT_101,
    )

    if result.shape[0] != crop_size or result.shape[1] != crop_size:
        raise ValueError(
            f"Crop size mismatch: expected {crop_size}x{crop_size}, "
            f"got {result.shape[0]}x{result.shape[1]}"
        )

    return result


def _preprocess(crop: np.ndarray, model_img_size: int = 128) -> np.ndarray:
    """Resize with letterboxing, normalize to [0,1], convert to CHW."""
    new_size = model_img_size
    old_size = crop.shape[:2]

    ratio = float(new_size) / max(old_size)
    scaled_shape = tuple([int(x * ratio) for x in old_size])

    interpolation = cv2.INTER_LANCZOS4 if ratio > 1.0 else cv2.INTER_AREA
    crop = cv2.resize(
        crop, (scaled_shape[1], scaled_shape[0]), interpolation=interpolation
    )

    delta_w = new_size - scaled_shape[1]
    delta_h = new_size - scaled_shape[0]
    top, bottom = delta_h // 2, delta_h - (delta_h // 2)
    left, right = delta_w // 2, delta_w - (delta_w // 2)

    crop = cv2.copyMakeBorder(crop, top, bottom, left, right, cv2.BORDER_REFLECT_101)

    return crop.transpose(2, 0, 1).astype(np.float32) / 255.0


def get_face_embedding(
    image_bytes: bytes,
    detector,
    landmark,
    recognizer,
) -> list[float]:
    """
    Detect > 3D landmarks > Recognise > Embed
    """

    img = cv2.imdecode(
        np.frombuffer(image_bytes, np.uint8),
        cv2.IMREAD_COLOR,
    )

    if img is None:
        raise ValueError("Invalid image")

    # 1. Detect
    bboxes, kpss = detector.detect(img)

    if len(bboxes) == 0:
        raise ValueError("No face detected")

    if len(bboxes) > 1:
        raise ValueError("Multiple faces detected")

    # 2. Create Face object on the first person.
    face = Face(
        bbox=bboxes[0],
        kps=kpss[0],
    )

    # 3. Generate 3D landmarks
    landmark.get(img, face)

    # 4. Recognize / generate embedding
    embedding = recognizer.get(img, face)

    return embedding.tolist()

def check_spoofing(
    image_bytes: bytes,
    detector,
    spoofing,
    threshold: float = 0.0, # apparently it uses logits, so 0.0 logits = 0.5
) -> bool:
    """
    Checks whether image is genuine or a spoof (photo/screen).

    Returns True if the face is real.
    """
    img = cv2.imdecode(
        np.frombuffer(image_bytes, np.uint8),
        cv2.IMREAD_COLOR,
    )

    if img is None:
        raise ValueError("Invalid image")

    bboxes, _ = detector.detect(img)

    if len(bboxes) == 0:
        raise ValueError("No face detected")

    if len(bboxes) > 1:
        raise ValueError("Multiple faces detected")

    x1, y1, x2, y2 = bboxes[0][:4].astype(int)

    # Model was trained on RGB crops
    img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

    face_crop = _crop_face(img_rgb, (x1, y1, x2, y2), expansion=1.5)
    input_tensor = _preprocess(face_crop, model_img_size=128)[None, ...]

    input_name = spoofing.get_inputs()[0].name
    logits = spoofing.run(None, {input_name: input_tensor})[0][0]

    real_logit = float(logits[0])
    spoof_logit = float(logits[1])

    return real_logit - spoof_logit >= threshold


