import pytest

from medialab_web.auth import ConfigError, check_startup_config, issue_session, session_is_valid
from medialab_web.config import AppConfig
from medialab_web.constants import SESSION_COOKIE_NAME
from tests.conftest import PASSWORD


async def test_wrong_password_is_401(client):
    response = await client.post("/login", data={"password": "nope"})
    assert response.status_code == 401
    assert SESSION_COOKIE_NAME not in response.cookies
    assert "Wrong password" in response.text


async def test_right_password_sets_cookie_and_redirects_home(client):
    response = await client.post("/login", data={"password": PASSWORD})
    assert response.status_code == 303
    assert response.headers["location"] == "/"
    assert SESSION_COOKIE_NAME in response.cookies


async def test_unauthenticated_page_redirects_to_login(client):
    response = await client.get("/")
    assert response.status_code == 303
    assert response.headers["location"] == "/login"


async def test_unauthenticated_fragment_redirects_too(client):
    response = await client.get("/partials/jobs")
    assert response.status_code == 303


async def test_tampered_cookie_is_rejected(client):
    client.cookies.set(SESSION_COOKIE_NAME, "ok.forged")
    response = await client.get("/")
    assert response.status_code == 303


async def test_logout_clears_session(logged_in):
    response = await logged_in.post("/logout")
    assert response.status_code == 303
    logged_in.cookies.clear()
    assert (await logged_in.get("/")).status_code == 303


async def test_health_needs_no_login(client):
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "online"


def test_missing_password_refuses_startup():
    with pytest.raises(ConfigError):
        check_startup_config(AppConfig(_env_file=None, web_secret_key="s"))


def test_missing_secret_refuses_startup():
    with pytest.raises(ConfigError):
        check_startup_config(AppConfig(_env_file=None, web_password="p"))


def test_session_expires(test_config):
    token = issue_session(test_config)
    assert session_is_valid(test_config, token)
    expired = test_config.model_copy(update={"session_max_age_seconds": -1})
    assert not session_is_valid(expired, token)


async def test_login_is_rate_limited(client):
    for _ in range(10):
        await client.post("/login", data={"password": "nope"})
    response = await client.post("/login", data={"password": PASSWORD})
    assert response.status_code == 429
    assert "Too many attempts" in response.text
