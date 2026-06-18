import tempfile
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.auth import hash_password
from app.database import Base, get_db
from app.main import app
from app.models import Alert, Appointment, Event, Medication, Notification, Patient, Review, User  # noqa: F401


@pytest.fixture
def db_file() -> Generator[str, None, None]:
    with tempfile.NamedTemporaryFile(suffix=".db") as f:
        yield f.name


@pytest.fixture
def db_session(db_file: str) -> Generator[Session, None, None]:
    engine = create_engine(f"sqlite:///{db_file}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    test_session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = test_session()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client(db_file: str) -> Generator[TestClient, None, None]:
    engine = create_engine(f"sqlite:///{db_file}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    test_session = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    def override_get_db():
        db = test_session()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    test_client = TestClient(app)
    yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def seed_users(db_file: str) -> list[User]:
    engine = create_engine(f"sqlite:///{db_file}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    test_session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = test_session()
    try:
        users = [
            User(username="admin", password=hash_password("admin123"), role="admin"),
            User(username="doctor", password=hash_password("doctor123"), role="doctor"),
            User(username="nurse", password=hash_password("nurse123"), role="nurse"),
            User(username="reception", password=hash_password("reception123"), role="reception"),
        ]
        for user in users:
            session.add(user)
        session.commit()
        return users
    finally:
        session.close()


@pytest.fixture
def auth_headers(client: TestClient, seed_users: list[User]) -> dict[str, dict[str, str]]:
    tokens = {}
    for role in ["admin", "doctor", "nurse", "reception"]:
        response = client.post(
            "/auth/login",
            json={"username": role, "password": f"{role}123"},
        )
        token = response.json()["access_token"]
        tokens[role] = {"Authorization": f"Bearer {token}"}
    return tokens
