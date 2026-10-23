"""
Authentication and Authorization Tests.
"""
import pytest
from httpx import AsyncClient
from backend.app.models.user import User

@pytest.mark.asyncio
async def test_register_and_login(client: AsyncClient):
    # 1. Register
    reg_payload = {
        "email": "newuser@company.com",
        "full_name": "New User",
        "password": "Password123!",
        "role": "INTERN"
    }
    res = await client.post("/api/v1/auth/register", json=reg_payload)
    assert res.status_code == 201
    data = res.json()
    assert data["email"] == "newuser@company.com"
    assert data["role"] == "INTERN"

    # 2. Login
    login_data = {
        "username": "newuser@company.com",
        "password": "Password123!"
    }
    res_login = await client.post("/api/v1/auth/login", data=login_data)
    assert res_login.status_code == 200
    token_data = res_login.json()
    assert "access_token" in token_data
    assert token_data["role"] == "INTERN"

    # 3. Invalid Password
    res_fail = await client.post("/api/v1/auth/login", data={"username": "newuser@company.com", "password": "WrongPassword"})
    assert res_fail.status_code == 401

@pytest.mark.asyncio
async def test_get_me_protected(client: AsyncClient, test_users, auth_headers):
    intern = test_users["intern"]
    headers = auth_headers(intern)

    res = await client.get("/api/v1/auth/me", headers=headers)
    assert res.status_code == 200
    assert res.json()["email"] == intern.email
