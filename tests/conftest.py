from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest
from medialab_contracts import MediaType

from medialab_web.config import AppConfig
from medialab_web.constants import SESSION_COOKIE_NAME
from medialab_web.limiter import limiter
from medialab_web.main import create_app
from medialab_web.schemas.jobs import JobsResponse, JobView
from medialab_web.schemas.system import DiskUsageResponse, DownstreamHealth, HealthResponse

PASSWORD = "correct horse"
SECRET = "unit-test-secret"


def make_job(status: str = "DONE", job_id: str = "job-1", **overrides) -> JobView:
    base = {
        "id": job_id,
        "torrent_hash": "abc",
        "release_name": "Dune.2021.1080p.PORTUGUESE.DUAL-GRP",
        "media_type": MediaType.MOVIE,
        "tmdb_id": 1,
        "resolved_title": "Dune",
        "resolved_year": 2021,
        "status": status,
        "created_at": "2026-06-26T00:00:00+00:00",
        "updated_at": "2026-06-26T00:00:00+00:00",
    }
    return JobView(**{**base, **overrides})


@pytest.fixture
def mock_client():
    client = MagicMock()
    client.health = AsyncMock(
        return_value=HealthResponse(
            status="online",
            uptime_seconds=42.0,
            downstream=DownstreamHealth(torrent_downloader=True, medialab_jellyfin=True),
            vpn_interface_bound=True,
        )
    )
    client.get_storage = AsyncMock(
        return_value=DiskUsageResponse(
            status="success",
            path="/media",
            total_gb=1000.0,
            used_gb=400.0,
            free_gb=600.0,
            used_percent=40.0,
        )
    )
    client.list_jobs = AsyncMock(
        return_value=JobsResponse(
            status="success",
            jobs=[make_job("DONE", "a"), make_job("FAILED", "b"), make_job("DELETED", "c")],
        )
    )
    client.get_settings = AsyncMock(return_value=None)
    client.close = AsyncMock()
    return client


@pytest.fixture(autouse=True)
def _reset_rate_limits():
    limiter.reset()


@pytest.fixture
def test_config() -> AppConfig:
    return AppConfig(
        _env_file=None,
        web_password=PASSWORD,
        web_secret_key=SECRET,
        orchestrator_url="http://gateway",
        orchestrator_api_key="k",
    )


@pytest.fixture
def app(test_config, mock_client, mocker):
    mocker.patch("medialab_web.main.OrchestratorClient", return_value=mock_client)
    return create_app(test_config)


@pytest.fixture
async def client(app):
    async with (
        app.router.lifespan_context(app),
        httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test", follow_redirects=False
        ) as c,
    ):
        yield c


@pytest.fixture
async def logged_in(client):
    response = await client.post("/login", data={"password": PASSWORD})
    assert response.status_code == 303
    assert SESSION_COOKIE_NAME in response.cookies
    client.cookies.set(SESSION_COOKIE_NAME, response.cookies[SESSION_COOKIE_NAME])
    return client
