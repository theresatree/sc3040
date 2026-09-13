from types import SimpleNamespace

import pytest
import pytest_asyncio
from asgi_lifespan import LifespanManager
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from testcontainers.postgres import PostgresContainer

import app.image as image_module
from app.db.database import get_db
from app.db.enums import UserRole
from app.db.models import Base
from app.main import app
from scripts.seed_db.register import seed_register
from scripts.seed_db.rooms import seed_room
from scripts.seed_db.timetable import seed_timetable
from scripts.seed_db.users import seed_user


@pytest.fixture(scope="session", autouse=True)
def cleanup_uploads(tmp_path_factory):
    # Register saves face crops into UPLOAD_DIR during tests: redirect it to a
    # session temp dir (auto-deleted by pytest) so tests never touch the real
    # uploads/ folder.
    original = image_module.UPLOAD_DIR
    image_module.UPLOAD_DIR = tmp_path_factory.mktemp("users_uploads")
    yield
    image_module.UPLOAD_DIR = original


@pytest.fixture(scope="session")
def postgres_container():
    with PostgresContainer("pgvector-postgis") as postgres:
        yield postgres


@pytest_asyncio.fixture(scope="session")
async def engine(postgres_container):
    url = postgres_container.get_connection_url().replace(
        "postgresql+psycopg2://", "postgresql+psycopg://", 1
    )
    engine = create_async_engine(url)

    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis"))

    yield engine
    await engine.dispose()


@pytest_asyncio.fixture(scope="session")
async def setup_database(engine):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture(scope="session", autouse=True)
async def seed_data(engine, setup_database):
    # Seed once per test session with the same seed code used for the dev
    # database. Face embeddings are skipped (embed_faces=False) because they
    # are slow and only face check-in tests need them -- those can call
    # seed_user.seed(..., state=app_state.state) explicitly.
    session_factory = async_sessionmaker(bind=engine, expire_on_commit=False)

    async with session_factory() as db:
        users = await seed_user.seed(
            db,
            staff_count=5,
            student_count=45,
            embed_faces=False,
        )

        rooms = await seed_room.seed(db)

        staffs = [user for user in users if user.role == UserRole.STAFF]
        students = [user for user in users if user.role == UserRole.STUDENT]

        timetables = await seed_timetable.seed(db, staffs, rooms)
        await seed_register.seed(db, timetables, students)

    yield SimpleNamespace(
        users=users,
        rooms=rooms,
        staffs=staffs,
        students=students,
        timetables=timetables,
    )


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


@pytest_asyncio.fixture()
async def logged_in_student(client):

    payload = {
        "email": "edmund@test.com",
        "password": "password",
    }

    response = await client.post(
        "/auth/login",
        json=payload,
    )

    assert response.status_code == 200, response.json()
    return response.json()


@pytest_asyncio.fixture()
async def logged_in_staff(client):
    payload = {
        "email": "samantha.davis@test.com",
        "password": "password",
    }

    response = await client.post(
        "/auth/login",
        json=payload,
    )

    assert response.status_code == 200, response.json()
    return response.json()
