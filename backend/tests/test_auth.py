"""Auth: register, login."""
import pytest
from httpx import AsyncClient

from tests.conftest import client, auth_headers


@pytest.mark.asyncio
async def test_register(client: AsyncClient):
    r = await client.post(
        "/auth/register",
        json={"email": "newuser@test.com", "password": "securepass123"},
    )
    assert r.status_code == 200
    data = r.json()
    assert "access_token" in data
    assert data["user"]["email"] == "newuser@test.com"
    assert "id" in data["user"]


@pytest.mark.asyncio
async def test_register_short_password(client: AsyncClient):
    r = await client.post(
        "/auth/register",
        json={"email": "short@test.com", "password": "abc"},
    )
    assert r.status_code == 422
    assert "8 characters" in r.json()["detail"]


@pytest.mark.asyncio
async def test_register_duplicate_email(client: AsyncClient, auth_headers: dict):
    # test@example.com already registered by auth_headers fixture
    r = await client.post(
        "/auth/register",
        json={"email": "test@example.com", "password": "otherpass"},
    )
    assert r.status_code == 400


@pytest.mark.asyncio
async def test_login(client: AsyncClient, auth_headers: dict):
    r = await client.post(
        "/auth/login",
        data={"username": "test@example.com", "password": "testpass123"},
    )
    assert r.status_code == 200
    data = r.json()
    assert "access_token" in data
    assert data["user"]["email"] == "test@example.com"


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient, auth_headers: dict):
    r = await client.post(
        "/auth/login",
        data={"username": "test@example.com", "password": "wrongpass"},
    )
    assert r.status_code == 401
