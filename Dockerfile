FROM python:3.14-slim

# We need this to download models apparently lol
RUN apt-get update && apt-get install -y \
    libxcb1 \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/ 

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen

COPY app ./app
COPY scripts ./scripts
COPY alembic.ini ./
COPY alembic ./alembic

CMD ["sh", "-c", "uv run alembic upgrade head && uv run fastapi dev --host 0.0.0.0"]
