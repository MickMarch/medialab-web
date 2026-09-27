from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from medialab_contracts import MediaType, ShowBrowseResponse

from medialab_web.client import OrchestratorClient
from medialab_web.schemas.actions import ActionResponse
from medialab_web.schemas.downloads import DownloadResponse
from medialab_web.schemas.jobs import JobsResponse, JobView
from medialab_web.schemas.system import DiskUsageResponse, HealthResponse
from medialab_web.schemas.tmdb import TmdbMediaDetailResponse, TmdbSearchResponse
from medialab_web.schemas.torrents import TorrentSearchResponse
from medialab_web.schemas.transfers import MergedTransfersResponse

BASE_URL = "http://localhost:8000"
API_KEY = "test-key"

_JOB = {
    "id": "job-abc",
    "torrent_hash": "abc123",
    "release_name": "Dune.2021.1080p",
    "media_type": "movie",
    "tmdb_id": 438631,
    "status": "DOWNLOAD_SUBMITTED",
    "created_at": "2026-06-26T00:00:00+00:00",
    "updated_at": "2026-06-26T00:00:00+00:00",
}


@pytest.fixture
def client():
    return OrchestratorClient(base_url=BASE_URL, api_key=API_KEY)


def _mock_response(status_code: int, payload: dict | None = None) -> MagicMock:
    r = MagicMock()
    r.status_code = status_code
    if payload is not None:
        r.json.return_value = payload
    return r


# --- infrastructure ---


@pytest.mark.asyncio
async def test_api_key_set_in_headers(client):
    assert client._http.headers.get("x-api-key") == API_KEY


@pytest.mark.asyncio
async def test_context_manager_closes_client():
    async with OrchestratorClient(base_url=BASE_URL, api_key=API_KEY) as c:
        assert c is not None
    assert c._http.is_closed


# --- health (aggregated) ---


@pytest.mark.asyncio
async def test_health_returns_aggregated_response_on_200(client):
    payload = {
        "status": "online",
        "uptime_seconds": 55.0,
        "downstream": {"torrent_downloader": True, "medialab_jellyfin": False},
    }
    with patch.object(
        client._http, "get", new=AsyncMock(return_value=_mock_response(200, payload))
    ):
        result = await client.health()
    assert isinstance(result, HealthResponse)
    assert result.downstream.torrent_downloader is True
    assert result.downstream.medialab_jellyfin is False


@pytest.mark.asyncio
async def test_health_returns_none_on_connect_error(client):
    with patch.object(
        client._http, "get", new=AsyncMock(side_effect=httpx.ConnectError("refused"))
    ):
        assert await client.health() is None


# --- search proxies ---


@pytest.mark.asyncio
async def test_search_tmdb_returns_response_on_200(client):
    payload = {
        "status": "success",
        "message": "",
        "data": [
            {
                "tmdb_id": 1,
                "title": "Dune",
                "year": "2021",
                "media_type": "movie",
                "overview": "Desert planet.",
                "vote_average": 7.9,
                "poster_path": None,
            }
        ],
    }
    with patch.object(
        client._http, "get", new=AsyncMock(return_value=_mock_response(200, payload))
    ):
        result = await client.search_tmdb("dune")
    assert isinstance(result, TmdbSearchResponse)
    assert result.data[0].title == "Dune"


@pytest.mark.asyncio
async def test_search_tmdb_movie_calls_correct_path(client):
    payload = {"status": "success", "message": "", "data": {}}
    mock_get = AsyncMock(return_value=_mock_response(200, payload))
    with patch.object(client._http, "get", new=mock_get):
        result = await client.search_tmdb_movie(438631)
    assert isinstance(result, TmdbMediaDetailResponse)
    assert "/api/v1/search/tmdb/movie/438631" in mock_get.call_args.args[0]


@pytest.mark.asyncio
async def test_search_tmdb_show_calls_correct_path(client):
    payload = {"status": "success", "message": "", "data": {}}
    mock_get = AsyncMock(return_value=_mock_response(200, payload))
    with patch.object(client._http, "get", new=mock_get):
        await client.search_tmdb_show(1396)
    assert "/api/v1/search/tmdb/show/1396" in mock_get.call_args.args[0]


@pytest.mark.asyncio
async def test_search_torrents_passes_query_and_media_type(client):
    payload = {"status": "success", "message": "", "data": {}}
    mock_get = AsyncMock(return_value=_mock_response(200, payload))
    with patch.object(client._http, "get", new=mock_get):
        result = await client.search_torrents("dune", MediaType.MOVIE)
    assert isinstance(result, TorrentSearchResponse)
    params = mock_get.call_args.kwargs.get("params", {})
    assert params.get("query") == "dune"
    assert params.get("media_type") == "movie"
    assert "season" not in params
    assert "episode" not in params


@pytest.mark.asyncio
async def test_search_torrents_passes_season_and_episode(client):
    payload = {"status": "success", "message": "", "data": {}}
    mock_get = AsyncMock(return_value=_mock_response(200, payload))
    with patch.object(client._http, "get", new=mock_get):
        await client.search_torrents("the wire", MediaType.SHOW, season=2, episode=5)
    params = mock_get.call_args.kwargs.get("params", {})
    assert params.get("media_type") == "show"
    assert params.get("season") == 2
    assert params.get("episode") == 5


# --- download (gateway body: media_type + tmdb_id, no save_path) ---


@pytest.mark.asyncio
async def test_download_returns_job_on_202(client):
    payload = {"status": "success", "job": _JOB}
    with patch.object(
        client._http, "post", new=AsyncMock(return_value=_mock_response(202, payload))
    ):
        result = await client.download("magnet:?xt=urn:btih:abc", MediaType.MOVIE, 438631)
    assert isinstance(result, DownloadResponse)
    assert result.job.torrent_hash == "abc123"


@pytest.mark.asyncio
async def test_download_sends_media_type_and_tmdb_id(client):
    payload = {"status": "success", "job": _JOB}
    mock_post = AsyncMock(return_value=_mock_response(202, payload))
    with patch.object(client._http, "post", new=mock_post):
        await client.download("magnet:?xt=urn:btih:abc", MediaType.SHOW, 1396)
    body = mock_post.call_args.kwargs.get("json", {})
    assert body == {
        "source_url": "magnet:?xt=urn:btih:abc",
        "media_type": "show",
        "tmdb_id": 1396,
        "release_name": "",
    }
    assert "save_path" not in body


@pytest.mark.asyncio
async def test_download_sends_torrent_file_url_as_source_url(client):
    payload = {"status": "success", "job": _JOB}
    mock_post = AsyncMock(return_value=_mock_response(202, payload))
    torrent_url = "https://www.torlock.com/tor/1924049.torrent"
    with patch.object(client._http, "post", new=mock_post):
        await client.download(torrent_url, MediaType.SHOW, 42)
    assert mock_post.call_args.kwargs["json"]["source_url"] == torrent_url


@pytest.mark.asyncio
async def test_download_returns_none_on_non_202(client):
    with patch.object(client._http, "post", new=AsyncMock(return_value=_mock_response(503))):
        assert await client.download("magnet:?xt=urn:btih:abc", MediaType.MOVIE, 1) is None


# --- redo (same body as download, posted to the finished job) ---


@pytest.mark.asyncio
async def test_redo_posts_the_download_body_to_the_job_and_returns_the_new_job(client):
    payload = {"status": "success", "job": _JOB}
    mock_post = AsyncMock(return_value=_mock_response(202, payload))
    with patch.object(client._http, "post", new=mock_post):
        result = await client.redo(
            "old",
            "magnet:?xt=urn:btih:abc",
            MediaType.SHOW,
            1396,
            "Lost.S02E05",
            season=2,
            episode=5,
        )
    assert isinstance(result, DownloadResponse)
    assert result.job.id == "job-abc"
    assert mock_post.call_args.args[0].endswith("/jobs/old/redo")
    assert mock_post.call_args.kwargs["json"] == {
        "source_url": "magnet:?xt=urn:btih:abc",
        "media_type": "show",
        "tmdb_id": 1396,
        "release_name": "Lost.S02E05",
        "season": 2,
        "episode": 5,
    }


@pytest.mark.asyncio
async def test_redo_returns_none_on_refusal(client):
    with patch.object(client._http, "post", new=AsyncMock(return_value=_mock_response(409))):
        assert await client.redo("old", "magnet:?xt=urn:btih:abc", MediaType.MOVIE, 1, "x") is None


# --- transfers (merged) ---


@pytest.mark.asyncio
async def test_get_transfers_returns_merged_response(client):
    payload = {
        "status": "success",
        "transfers": {"status": "success", "message": "", "data": []},
        "jobs": [_JOB],
    }
    with patch.object(
        client._http, "get", new=AsyncMock(return_value=_mock_response(200, payload))
    ):
        result = await client.get_transfers()
    assert isinstance(result, MergedTransfersResponse)
    assert len(result.jobs) == 1


# --- storage (no path param) ---


@pytest.mark.asyncio
async def test_get_storage_sends_no_path_param(client):
    payload = {
        "status": "success",
        "path": "/media",
        "total_gb": 2000.0,
        "used_gb": 800.0,
        "free_gb": 1200.0,
        "used_percent": 40.0,
    }
    mock_get = AsyncMock(return_value=_mock_response(200, payload))
    with patch.object(client._http, "get", new=mock_get):
        result = await client.get_storage()
    assert isinstance(result, DiskUsageResponse)
    # No path param: the gateway resolves storage itself (save-path config gone).
    assert "path" not in (mock_get.call_args.kwargs.get("params") or {})


# --- jobs ---


@pytest.mark.asyncio
async def test_list_jobs_returns_response(client):
    payload = {"status": "success", "jobs": [_JOB]}
    with patch.object(
        client._http, "get", new=AsyncMock(return_value=_mock_response(200, payload))
    ):
        result = await client.list_jobs()
    assert isinstance(result, JobsResponse)
    assert result.jobs[0].tmdb_id == 438631


@pytest.mark.asyncio
async def test_list_jobs_passes_status_filter(client):
    payload = {"status": "success", "jobs": []}
    mock_get = AsyncMock(return_value=_mock_response(200, payload))
    with patch.object(client._http, "get", new=mock_get):
        await client.list_jobs(status="FAILED")
    assert mock_get.call_args.kwargs.get("params", {}).get("status") == "FAILED"


@pytest.mark.asyncio
async def test_retry_job_calls_correct_path_and_returns_job(client):
    failed_then_retried = {**_JOB, "status": "STOP_SEEDING"}
    mock_post = AsyncMock(return_value=_mock_response(200, failed_then_retried))
    with patch.object(client._http, "post", new=mock_post):
        result = await client.retry_job("job-abc")
    assert isinstance(result, JobView)
    assert "/api/v1/jobs/job-abc/retry" in mock_post.call_args.args[0]
    assert result.status == "STOP_SEEDING"


@pytest.mark.asyncio
async def test_retry_job_returns_none_on_error(client):
    with patch.object(client._http, "post", new=AsyncMock(return_value=_mock_response(404))):
        assert await client.retry_job("nope") is None


# --- stop-seeding ---


@pytest.mark.asyncio
async def test_stop_seeding_posts_and_parses(client):
    payload = {"status": "success", "message": "All seeding transfers stopped."}
    with patch.object(
        client._http, "post", new=AsyncMock(return_value=_mock_response(202, payload))
    ) as mock_post:
        result = await client.stop_seeding()
    assert mock_post.call_args.args[0].endswith("/transfers/stop-seeding")
    assert isinstance(result, ActionResponse)
    assert result.message == "All seeding transfers stopped."


@pytest.mark.asyncio
async def test_stop_seeding_returns_none_on_error(client):
    with patch.object(client._http, "post", new=AsyncMock(return_value=_mock_response(502))):
        assert await client.stop_seeding() is None


# --- deletion ---


@pytest.mark.asyncio
async def test_deletion_plan_gets_and_parses(client):
    payload = {
        "status": "success",
        "job_id": "j1",
        "torrent": True,
        "download_folder": "/media/Movies/X",
        "placed_paths": [],
        "scan_path": None,
        "refused": None,
    }
    with patch.object(
        client._http, "get", new=AsyncMock(return_value=_mock_response(200, payload))
    ) as mock_get:
        plan = await client.deletion_plan("j1")
    assert mock_get.call_args.args[0].endswith("/jobs/j1/deletion-plan")
    assert plan is not None and plan.torrent is True


@pytest.mark.asyncio
async def test_delete_job_deletes_and_parses(client):
    with patch.object(
        client._http,
        "delete",
        new=AsyncMock(return_value=_mock_response(200, {**_JOB, "status": "DELETED"})),
    ) as mock_delete:
        job = await client.delete_job("job-abc")
    assert mock_delete.call_args.args[0].endswith("/jobs/job-abc")
    assert job is not None and job.status == "DELETED"


@pytest.mark.asyncio
async def test_delete_job_returns_none_on_409(client):
    with patch.object(client._http, "delete", new=AsyncMock(return_value=_mock_response(409))):
        assert await client.delete_job("job-abc") is None


@pytest.mark.asyncio
async def test_clear_search_cache_deletes_and_parses(client):
    from medialab_web.schemas.actions import CacheClearResponse

    payload = {"status": "success", "cleared": True}
    with patch.object(
        client._http, "delete", new=AsyncMock(return_value=_mock_response(200, payload))
    ) as mock_delete:
        result = await client.clear_search_cache()
    assert mock_delete.call_args.args[0].endswith("/search/cache")
    assert isinstance(result, CacheClearResponse)
    assert result.cleared is True


@pytest.mark.asyncio
async def test_search_torrents_passes_alt_query(client):
    payload = {"status": "success", "message": "", "data": {}}
    with patch.object(
        client._http, "get", new=AsyncMock(return_value=_mock_response(200, payload))
    ) as mock_get:
        await client.search_torrents("Dune 2021", MediaType.MOVIE, alt_query="dune 2021")
    assert mock_get.call_args.kwargs["params"]["alt_query"] == "dune 2021"


@pytest.mark.asyncio
async def test_download_sends_release_name(client):
    payload = {"status": "success", "job": _JOB}
    with patch.object(
        client._http, "post", new=AsyncMock(return_value=_mock_response(202, payload))
    ) as mock_post:
        await client.download("magnet:?xt=urn:btih:abc", MediaType.MOVIE, 1, "Dune.2021-GRP")
    assert mock_post.call_args.kwargs["json"]["release_name"] == "Dune.2021-GRP"


@pytest.mark.asyncio
async def test_download_sends_season_and_episode_only_when_given(client):
    payload = {"status": "success", "job": _JOB}
    mock_post = AsyncMock(return_value=_mock_response(202, payload))
    with patch.object(client._http, "post", new=mock_post):
        await client.download("magnet:?xt=urn:btih:abc", MediaType.SHOW, 1396, season=2, episode=5)
    body = mock_post.call_args.kwargs["json"]
    assert body["season"] == 2 and body["episode"] == 5
    with patch.object(client._http, "post", new=mock_post):
        await client.download("magnet:?xt=urn:btih:abc", MediaType.SHOW, 1396, season=2)
    body = mock_post.call_args.kwargs["json"]
    assert body["season"] == 2 and "episode" not in body


# --- browse show ---


@pytest.mark.asyncio
async def test_browse_show_parses_response(client):
    payload = {
        "tmdb_id": 1396,
        "title": "Breaking Bad",
        "year": "2008",
        "seasons": [{"season": 1, "name": "Season 1", "episode_count": 1}],
        "episodes": [{"season": 1, "episode": 1, "title": "Pilot", "aired": True}],
    }
    mock_get = AsyncMock(return_value=_mock_response(200, payload))
    with patch.object(client._http, "get", new=mock_get):
        result = await client.browse_show(1396)
    assert isinstance(result, ShowBrowseResponse)
    assert result.episodes[0].title == "Pilot"
    assert mock_get.call_args.args[0].endswith("/shows/1396")


@pytest.mark.asyncio
async def test_browse_show_returns_none_on_failure(client):
    with patch.object(client._http, "get", new=AsyncMock(return_value=_mock_response(503))):
        assert await client.browse_show(1396) is None


@pytest.mark.asyncio
async def test_settings_client_round_trip(client):
    from medialab_contracts import SettingView, SuiteSettingsResponse

    view = {
        "key": "minimum_seeders",
        "value": 3,
        "default": 10,
        "source": "override",
        "type": "int",
        "description": "d",
        "applies": "next search",
        "min": 0,
        "max": 1000,
    }
    with patch.object(
        client._http,
        "get",
        new=AsyncMock(
            return_value=_mock_response(
                200, {"status": "success", "services": {"torrent-downloader": [view]}}
            )
        ),
    ):
        suite = await client.get_settings()
    assert isinstance(suite, SuiteSettingsResponse)
    with patch.object(
        client._http, "put", new=AsyncMock(return_value=_mock_response(200, view))
    ) as mock_put:
        result = await client.set_setting("torrent-downloader", "minimum_seeders", "3")
    assert isinstance(result, SettingView)
    assert mock_put.call_args.args[0].endswith("/settings/torrent-downloader/minimum_seeders")
    assert mock_put.call_args.kwargs["json"] == {"value": "3"}
    with patch.object(client._http, "put", new=AsyncMock(return_value=_mock_response(422))):
        assert await client.set_setting("torrent-downloader", "minimum_seeders", "x") is None


# --- discover and wishlist ---

_DISCOVER = {
    "items": [{"tmdb_id": 1, "media_type": "movie", "title": "Dune", "poster_path": "/d.jpg"}],
    "page": 2,
    "total_pages": 5,
    "cached_at": "2026-09-27T00:00:00+00:00",
}
_WISH = {
    "tmdb_id": 1,
    "media_type": "movie",
    "title": "Dune",
    "added_at": "2026-09-27T00:00:00+00:00",
}


@pytest.mark.asyncio
async def test_discover_passes_genre_and_page(client):
    from medialab_contracts import DiscoverResponse

    mock_get = AsyncMock(return_value=_mock_response(200, _DISCOVER))
    with patch.object(client._http, "get", new=mock_get):
        result = await client.discover(MediaType.SHOW, genre=18, page=2)
    assert isinstance(result, DiscoverResponse)
    assert mock_get.call_args.args[0].endswith("/api/v1/discover/show")
    assert mock_get.call_args.kwargs["params"] == {"page": 2, "genre": 18}


@pytest.mark.asyncio
async def test_discover_omits_genre_and_returns_none_on_503(client):
    mock_get = AsyncMock(return_value=_mock_response(503, {"code": "TMDB_UNAVAILABLE"}))
    with patch.object(client._http, "get", new=mock_get):
        assert await client.discover(MediaType.MOVIE) is None
    assert mock_get.call_args.kwargs["params"] == {"page": 1}


@pytest.mark.asyncio
async def test_discover_genres_calls_path(client):
    from medialab_contracts import GenresResponse

    payload = {"genres": [{"id": 28, "name": "Action"}]}
    mock_get = AsyncMock(return_value=_mock_response(200, payload))
    with patch.object(client._http, "get", new=mock_get):
        result = await client.discover_genres(MediaType.MOVIE)
    assert isinstance(result, GenresResponse)
    assert mock_get.call_args.args[0].endswith("/api/v1/discover/movie/genres")


@pytest.mark.asyncio
async def test_list_wishlist_filters_by_media_type(client):
    from medialab_contracts import WishlistResponse

    mock_get = AsyncMock(return_value=_mock_response(200, {"items": [_WISH]}))
    with patch.object(client._http, "get", new=mock_get):
        result = await client.list_wishlist(MediaType.MOVIE)
        await client.list_wishlist()
    assert isinstance(result, WishlistResponse)
    assert mock_get.call_args_list[0].args[0].endswith("/api/v1/wishlist")
    assert mock_get.call_args_list[0].kwargs["params"] == {"media_type": "movie"}
    assert mock_get.call_args_list[1].kwargs["params"] == {}


@pytest.mark.asyncio
async def test_add_to_wishlist_puts_body(client):
    from medialab_contracts import WishlistAddRequest, WishlistItem

    body = WishlistAddRequest(title="Dune", year="2021", poster_path="/d.jpg", overview="o")
    mock_put = AsyncMock(return_value=_mock_response(200, _WISH))
    with patch.object(client._http, "put", new=mock_put):
        result = await client.add_to_wishlist(MediaType.MOVIE, 1, body)
    assert isinstance(result, WishlistItem)
    assert mock_put.call_args.args[0].endswith("/api/v1/wishlist/movie/1")
    assert mock_put.call_args.kwargs["json"] == body.model_dump(mode="json")


@pytest.mark.asyncio
async def test_remove_from_wishlist_true_on_204(client):
    mock_delete = AsyncMock(return_value=_mock_response(204))
    with patch.object(client._http, "delete", new=mock_delete):
        assert await client.remove_from_wishlist(MediaType.SHOW, 7) is True
    assert mock_delete.call_args.args[0].endswith("/api/v1/wishlist/show/7")
    with patch.object(client._http, "delete", new=AsyncMock(return_value=_mock_response(500))):
        assert await client.remove_from_wishlist(MediaType.SHOW, 7) is False
    with patch.object(
        client._http, "delete", new=AsyncMock(side_effect=httpx.ConnectError("refused"))
    ):
        assert await client.remove_from_wishlist(MediaType.SHOW, 7) is False
