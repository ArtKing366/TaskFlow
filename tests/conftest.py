import os
from uuid import uuid4

import pytest
from dotenv import load_dotenv
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

load_dotenv()

from app import models as _models
from app.database import Base, get_db
from app.main import app


TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")

if not TEST_DATABASE_URL:
    raise RuntimeError(
        "Set TEST_DATABASE_URL in .env before running tests."
    )

database_name = make_url(TEST_DATABASE_URL).database

if not database_name or "test" not in database_name.lower():
    raise RuntimeError(
        "Safety check failed: TEST_DATABASE_URL must point "
        "to a database whose name contains 'test'."
    )

test_engine = create_engine(
    TEST_DATABASE_URL,
    pool_pre_ping=True,
)


@pytest.fixture(scope="session", autouse=True)
def prepare_test_database():
    Base.metadata.create_all(bind=test_engine)

    yield

    test_engine.dispose()


@pytest.fixture
def db(prepare_test_database):
    connection = test_engine.connect()
    transaction = connection.begin()

    session = Session(
        bind=connection,
        join_transaction_mode="create_savepoint",
        expire_on_commit=False,
    )

    try:
        yield session
    finally:
        session.close()

        if transaction.is_active:
            transaction.rollback()

        connection.close()


@pytest.fixture
def client(db):
    def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db

    test_client = TestClient(app)

    try:
        yield test_client
    finally:
        test_client.close()
        app.dependency_overrides.pop(get_db, None)


@pytest.fixture
def user_factory(client):
    def create_user(email=None, password="TestPassword123!"):
        email = email or f"user-{uuid4().hex}@example.com"

        registration = client.post(
            "/auth/register",
            json={
                "email": email,
                "password": password,
            },
        )

        assert registration.status_code in (200, 201), (
            f"Registration failed: "
            f"{registration.status_code} {registration.text}"
        )

        user_data = registration.json()

        login = client.post(
            "/auth/login",
            json={
                "email": email,
                "password": password,
            },
        )

        assert login.status_code == 200, (
            f"Login failed: {login.status_code} {login.text}"
        )

        token = login.json()["access_token"]

        return {
            "id": user_data["id"],
            "email": email,
            "password": password,
            "token": token,
            "headers": {
                "Authorization": f"Bearer {token}",
            },
        }

    return create_user


@pytest.fixture
def authenticated_user(user_factory):
    return user_factory()


@pytest.fixture
def owner(client, user_factory):
    user = user_factory()

    response = client.post(
        "/workspaces",
        json={"name": f"Workspace-{uuid4().hex[:8]}"},
        headers=user["headers"],
    )

    assert response.status_code in (200, 201), (
        f"Workspace creation failed: "
        f"{response.status_code} {response.text}"
    )

    user["workspace"] = response.json()
    return user


@pytest.fixture
def workspace(owner):
    return owner["workspace"]


@pytest.fixture
def member_factory(client, user_factory, owner):
    def create_member(role="member"):
        member = user_factory()

        response = client.post(
            f"/workspaces/{owner['workspace']['id']}/members",
            json={
                "user_id": member["id"],
                "role": role,
            },
            headers=owner["headers"],
        )

        assert response.status_code in (200, 201), (
            f"Adding member failed: "
            f"{response.status_code} {response.text}"
        )

        member["role"] = role
        return member

    return create_member


@pytest.fixture
def project_headers():
    def build(user, key=None):
        headers = dict(user["headers"])
        headers["Idempotency-Key"] = key or f"pytest-{uuid4().hex}"
        return headers

    return build


@pytest.fixture
def project_payload():
    def build(workspace_id, title=None):
        return {
            "workspace_id": workspace_id,
            "title": title or f"Project-{uuid4().hex[:8]}",
            "description": "Created by automated tests",
        }

    return build


@pytest.fixture
def project_factory(
    client,
    project_headers,
    project_payload,
):
    def create(user, workspace_id, title=None):
        response = client.post(
            f"/workspaces/{workspace_id}/projects/",
            json=project_payload(workspace_id, title),
            headers=project_headers(user),
        )

        assert response.status_code == 201, (
            f"Project creation failed: "
            f"{response.status_code} {response.text}"
        )

        return response.json()

    return create