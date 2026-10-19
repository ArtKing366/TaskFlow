from uuid import uuid4


def test_register_success(client):
    email = f"register-{uuid4().hex}@example.com"

    response = client.post(
        "/auth/register",
        json={
            "email": email,
            "password": "TestPassword123!",
        },
    )

    assert response.status_code in (200, 201)
    assert response.json()["email"] == email
    assert "hashed_password" not in response.json()
    assert "password" not in response.json()


def test_duplicate_email_rejected(client):
    email = f"duplicate-{uuid4().hex}@example.com"
    payload = {
        "email": email,
        "password": "TestPassword123!",
    }

    first = client.post("/auth/register", json=payload)
    assert first.status_code in (200, 201)

    second = client.post("/auth/register", json=payload)
    assert second.status_code == 400


def test_login_success(client, user_factory):
    user = user_factory()

    response = client.post(
        "/auth/login",
        json={
            "email": user["email"],
            "password": user["password"],
        },
    )

    assert response.status_code == 200
    assert response.json()["access_token"]
    assert response.json()["token_type"].lower() == "bearer"


def test_login_wrong_password(client, user_factory):
    user = user_factory()

    response = client.post(
        "/auth/login",
        json={
            "email": user["email"],
            "password": "WrongPassword123!",
        },
    )

    assert response.status_code == 401


def test_me_returns_current_user(client, authenticated_user):
    response = client.get(
        "/auth/me",
        headers=authenticated_user["headers"],
    )

    assert response.status_code == 200
    assert response.json()["email"] == authenticated_user["email"]


def test_me_without_token_returns_401(client):
    response = client.get("/auth/me")

    assert response.status_code == 401