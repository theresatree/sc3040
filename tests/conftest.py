import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from asgi_lifespan import LifespanManager
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from app.main import app
from app.db.database import get_db
from app.db.models import Base

from testcontainers.postgres import PostgresContainer

@pytest.fixture(scope="session")
def postgres_container():
    with PostgresContainer("pgvector/pgvector:pg18") as postgres:
        yield postgres


@pytest_asyncio.fixture(scope="session")
async def engine(postgres_container):
    url = postgres_container.get_connection_url().replace(
        "postgresql+psycopg2://", "postgresql+psycopg://", 1
    )
    engine = create_async_engine(url)
    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture(scope="session")
async def setup_database(engine):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture()
async def db_session(engine, setup_database):
    connection = await engine.connect()
    transaction = await connection.begin()
    session = async_sessionmaker(bind=connection, expire_on_commit=False)()

    yield session

    await session.close()
    await transaction.rollback()
    await connection.close()


@pytest_asyncio.fixture(scope="session")
async def app_state():
    # LifespanManager runs your app's startup/shutdown (loads onnx models
    # into app.state) — needed because register() reads request.app.state.
    # Session-scoped so models load ONCE for the whole test run.
    async with LifespanManager(app) as manager:
        yield manager.app


@pytest_asyncio.fixture()
async def client(db_session, app_state):
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app_state)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


############### PRE-CONFIG DATA ################
from tests.constants import IMAGE_PATH

@pytest_asyncio.fixture()
async def registered_user(client):
    payload = {
        "name": "Test",
        "email": "student@example.com",
        "password": "password",
        "gender": "male",
        "role": "student",
    }
    with open(IMAGE_PATH, "rb") as f:
        response = await client.post(
            "/auth/register",
            data=payload,
            files={"image": (IMAGE_PATH.name, f, "image/jpeg")},
        )
    assert response.status_code == 201
    return payload

@pytest_asyncio.fixture()
async def registered_admin(client):
    payload = {
        "name": "Admin",
        "email": "admin@example.com",
        "password": "password",
        "gender": "male",
        "role": "admin",
    }
    with open(IMAGE_PATH, "rb") as f:
        response = await client.post(
            "/auth/register",
            data=payload,
            files={"image": (IMAGE_PATH.name, f, "image/jpeg")},
        )
    assert response.status_code == 201
    return payload
