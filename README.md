# sc3040

***** RUN

python scripts/download_models.py

*Note:
https://github.com/deepinsight/insightface/tree/master/model_zoo
InsightFace uses both 128x128 and 640x640
- det_10g.onnx	
    - Face detection — finds faces + bounding boxes
- 2d106det.onnx	
    - 2D facial landmarks — eyes, nose, mouth, etc.
- 1k3d68.onnx	
    - 3D facial landmarks
- genderage.onnx
    - Age/gender estimation
- w600k_r50.onnx
    - Face recognition/embedding

https://github.com/facenox/face-antispoof-onnx
For the anti-spooofing
- It requires 128x128. Thus, we need to resize the input image to 128x128 before passing it to the anti-spooofing model.
- InsightFace returns a bounding-box, so we can just resize from there.
- spoofing_model.onnx	


To seed data:
docker compose exec api env PYTHONPATH=/app uv run python scripts/seed_data.py
