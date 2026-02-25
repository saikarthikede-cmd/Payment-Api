import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


os.environ["DATABASE_URL"] = "sqlite:///./test.db"
os.environ["JWT_SECRET_KEY"] = "test-secret-key"

from app.db import get_db  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Base  # noqa: E402


TEST_DB_URL = "sqlite:///./test.db"
engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


def auth_headers(access_token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {access_token}"}


def signup_payload():
    return {
        "user_id": "CUST-001",
        "email": "customer@example.com",
        "full_name": "John Doe",
        "phone": "+91-9876543210",
        "password": "Str0ngPassw0rd!",
    }


def test_health_and_root():
    root = client.get("/")
    assert root.status_code == 200
    assert root.json()["message"] == "Payment API is running"


    health = client.get("/health")
    assert health.status_code == 200
    assert health.json()["status"] == "healthy"


def test_auth_signup_signin_and_protected_access():
    signup = client.post("/auth/signup", json=signup_payload())
    assert signup.status_code == 201
    assert signup.json()["user_id"] == "CUST-001"

    signin = client.post(
        "/auth/signin",
        json={"email": "customer@example.com", "password": "Str0ngPassw0rd!"},
    )
    assert signin.status_code == 200
    token = signin.json()["access_token"]
    assert token

    protected = client.get("/users/CUST-001", headers=auth_headers(token))
    assert protected.status_code == 200
    assert protected.json()["email"] == "customer@example.com"

    unauthorized = client.get("/users/CUST-001")
    assert unauthorized.status_code == 401


def test_auth_invalid_signin():
    client.post("/auth/signup", json=signup_payload())
    bad_signin = client.post(
        "/auth/signin",
        json={"email": "customer@example.com", "password": "WrongPass123"},
    )
    assert bad_signin.status_code == 401


def test_users_endpoints():
    created = client.post("/auth/signup", json=signup_payload())
    assert created.status_code == 201

    signin = client.post(
        "/auth/signin",
        json={"email": "customer@example.com", "password": "Str0ngPassw0rd!"},
    )
    token = signin.json()["access_token"]

    get_user = client.get("/users/CUST-001", headers=auth_headers(token))
    assert get_user.status_code == 200
    assert get_user.json()["user_id"] == "CUST-001"

    list_users = client.get("/users", headers=auth_headers(token))
    assert list_users.status_code == 200
    assert len(list_users.json()) == 1


def test_orders_endpoints():
    client.post("/auth/signup", json=signup_payload())
    signin = client.post(
        "/auth/signin",
        json={"email": "customer@example.com", "password": "Str0ngPassw0rd!"},
    )
    token = signin.json()["access_token"]

    unauthorized = client.post(
        "/orders",
        json={"customer_id": "CUST-001", "amount": 100.0, "currency": "INR"},
    )
    assert unauthorized.status_code == 401

    created = client.post(
        "/orders",
        json={
            "customer_id": "CUST-001",
            "amount": 499.99,
            "currency": "INR",
            "idempotency_key": "order-abc-123",
        },
        headers=auth_headers(token),
    )
    assert created.status_code == 201
    assert created.json()["status"] == "created"

    listed = client.get(
        "/orders",
        params={"customer_id": "CUST-001"},
        headers=auth_headers(token),
    )
    assert listed.status_code == 200
    assert len(listed.json()) == 1

    forbidden = client.get(
        "/orders",
        params={"customer_id": "CUST-999"},
        headers=auth_headers(token),
    )
    assert forbidden.status_code == 403


def test_wallet_endpoints():
    client.post("/auth/signup", json=signup_payload())
    signin = client.post(
        "/auth/signin",
        json={"email": "customer@example.com", "password": "Str0ngPassw0rd!"},
    )
    token = signin.json()["access_token"]

    credit = client.post(
        "/wallet/CUST-001/credit",
        json={"amount": 1000.0},
        headers=auth_headers(token),
    )
    assert credit.status_code == 200
    assert credit.json()["balance"] == 1000.0

    debit = client.post(
        "/wallet/CUST-001/debit",
        json={"amount": 250.0},
        headers=auth_headers(token),
    )
    assert debit.status_code == 200
    assert debit.json()["balance"] == 750.0

    wallet = client.get("/wallet/CUST-001", headers=auth_headers(token))
    assert wallet.status_code == 200
    assert wallet.json()["balance"] == 750.0

    forbidden = client.get("/wallet/CUST-999", headers=auth_headers(token))
    assert forbidden.status_code == 403
