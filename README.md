# sc3040


# Tech stack
1. PostGres
    - PostGIS (Store geolocation)
    - pgvector (store vectors)


# NOTE: BEFORE PUSHING
Please run the linting and all the other checks in Makefile.
- This ensures consistency and make sure everything works.

E.g. for linting
```bash
make lint
```

# To Build and run

*Note: the download script might not run, given we need to have tqdm.
- In that case, run to create venv and download dependencies

```
uv sync
```

1. DOWNLOAD MODELS FIRST.
```python
python scripts/download_models.py
```

2. Run the backend.
```bash
docker compose up --build -d
```

*Note: I exposed the postgres to outside docker as 5433 instead of 5432 to prevent conflict with local postgres

3. To seed data:
```bash
docker compose exec api uv run python -m scripts.seed_db.main
```

\
\
To access FASTAPI docs
- http://www.localhost:8000/docs

To login:
For instance, for yao sheng
- username: yao.sheng@test.com
- password: password

To access the camera prototype
- http://www.localhost/ws-checkin.html

# To update alembic

To create new revision
```
docker compose exec api uv run alembic revision --autogenerate -m "describe your change"
```

To upgrade to latest head
```
docker compose exec api uv run alembic upgrade head
```

# Models used
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


