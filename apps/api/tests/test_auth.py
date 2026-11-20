import asyncio
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import async_sessionmaker

from tutor_api.core.passwords import hash_password
from tutor_api.core.settings import get_settings
from tutor_api.db.engine import create_database_engine
from tutor_api.models.identity import School, User


@pytest.mark.integration
def test_login_rotates_refresh_tokens_and_revokes_reuse(client: TestClient) -> None:
    code = f"t{uuid4().hex[:8]}"
    username = "ada"
    password = "orchard-maple-19"
    asyncio.run(_create_admin(code, username, password))

    login = client.post(
        "/api/v1/auth/login",
        json={"school_code": code, "username": username, "password": password},
    )
    assert login.status_code == 200
    body = login.json()
    access = body["access_token"]
    refresh = body["refresh_token"]

    me = client.get("/api/v1/auth/me", headers={"authorization": f"Bearer {access}"})
    assert me.status_code == 200
    assert me.json()["username"] == username

    browser = {"origin": "http://localhost:3000", "x-requested-with": "tutor"}
    rotated = client.post("/api/v1/auth/refresh", json={"refresh_token": refresh}, headers=browser)
    assert rotated.status_code == 200
    reused = client.post("/api/v1/auth/refresh", json={"refresh_token": refresh}, headers=browser)
    assert reused.status_code == 401
    assert reused.json()["code"] == "refresh_reused"

    accounts = client.get(
        "/api/v1/users",
        headers={"authorization": f"Bearer {rotated.json()['access_token']}"},
    )
    assert accounts.status_code == 200
    assert accounts.json()["items"][0]["username"] == username


async def _create_admin(code: str, username: str, password: str) -> None:
    engine = create_database_engine(get_settings())
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        school = School(name="Test School", code=code)
        session.add(school)
        await session.flush()
        session.add(
            User(
                school_id=school.id,
                role="admin",
                username=username,
                display_name="Ada",
                password_hash=hash_password(password),
            )
        )
        await session.commit()
    await engine.dispose()
