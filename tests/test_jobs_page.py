from unittest.mock import AsyncMock

from medialab_contracts import JobProgress, MediaType

from medialab_web.constants import (
    JOBS_ACTIVE_REFRESH_SECONDS,
    JOBS_REFRESH_SECONDS,
    REDO_NOTICE,
    SHORT_ID_LENGTH,
)
from medialab_web.schemas.deletion import DeletionPlan
from medialab_web.schemas.downloads import DownloadResponse
from medialab_web.schemas.errors import GatewayError
from medialab_web.schemas.jobs import JobsResponse
from medialab_web.schemas.torrents import TorrentResult, TorrentSearchResponse
from tests.conftest import make_job

_SPEED_3_MB = 3 * 1024**2


def _progress(**kw) -> JobProgress:
    base = {
        "progress": 0.42,
        "download_speed": _SPEED_3_MB,
        "eta_seconds": 720,
        "state": "downloading",
    }
    return JobProgress(**{**base, **kw})


def _jobs(*jobs) -> AsyncMock:
    return AsyncMock(return_value=JobsResponse(status="success", jobs=list(jobs)))


def _plan(**kw) -> DeletionPlan:
    base = {
        "status": "success",
        "job_id": "a",
        "torrent": True,
        "download_folder": "/media/_incoming/Movies/Dune.2021",
        "placed_paths": ["/media/Movies/Dune (2021)/Dune (2021).mkv"],
        "scan_path": "/media/Movies",
    }
    return DeletionPlan(**{**base, **kw})


async def test_index_renders_shell(logged_in):
    response = await logged_in.get("/")
    assert response.status_code == 200
    assert 'hx-get="/partials/jobs"' in response.text
    assert 'hx-get="/partials/storage"' in response.text


async def test_jobs_table_hides_deleted_by_default(logged_in, mock_client):
    response = await logged_in.get("/partials/jobs")
    assert response.status_code == 200
    assert 'id="job-a"' in response.text
    assert 'id="job-b"' in response.text
    assert 'id="job-c"' not in response.text
    mock_client.list_jobs.assert_awaited_once_with(None)


async def test_jobs_table_shows_title_year_release_and_status(logged_in):
    text = (await logged_in.get("/partials/jobs")).text
    assert "Dune (2021)" in text
    assert "Dune.<wbr>2021.<wbr>1080p.<wbr>PORTUGUESE.<wbr>DUAL-<wbr>GRP" in text
    assert "FAILED" in text


async def test_retry_button_only_on_retryable_rows(logged_in):
    text = (await logged_in.get("/partials/jobs")).text
    assert text.count("/retry") == 1
    assert 'hx-post="/jobs/b/retry"' in text


async def test_status_filter_is_forwarded(logged_in, mock_client):
    await logged_in.get("/partials/jobs", params={"status_filter": "DELETED"})
    mock_client.list_jobs.assert_awaited_once_with("DELETED")


async def test_jobs_table_gateway_down(logged_in, mock_client):
    mock_client.list_jobs = AsyncMock(return_value=None)
    response = await logged_in.get("/partials/jobs")
    assert response.status_code == 502
    assert "Could not reach the gateway" in response.text


async def test_storage_panel(logged_in):
    text = (await logged_in.get("/partials/storage")).text
    assert "600 GB free" in text
    assert "medialab-jellyfin" in text


async def test_retry_swaps_row(logged_in, mock_client):
    mock_client.retry_job = AsyncMock(return_value=make_job("DOWNLOADING", "b"))
    response = await logged_in.post("/jobs/b/retry")
    assert response.status_code == 200
    assert "DOWNLOADING" in response.text
    assert "Retry queued" in response.text
    mock_client.retry_job.assert_awaited_once_with("b")


async def test_plan_renders_with_delete_button(logged_in, mock_client):
    mock_client.deletion_plan = AsyncMock(return_value=_plan())
    text = (await logged_in.get("/jobs/a/plan")).text
    assert "Nothing has happened yet" in text
    assert "Dune (2021).mkv" in text
    assert 'hx-delete="/jobs/a"' in text
    mock_client.delete_job.assert_not_called()


async def test_refused_plan_has_no_delete_button(logged_in, mock_client):
    mock_client.deletion_plan = AsyncMock(return_value=_plan(refused="predates tracking"))
    text = (await logged_in.get("/jobs/a/plan")).text
    assert "Cannot delete automatically" in text
    assert "hx-delete" not in text


async def test_delete_calls_gateway_once_and_swaps_row(logged_in, mock_client):
    mock_client.delete_job = AsyncMock(return_value=make_job("DELETED", "a"))
    response = await logged_in.delete("/jobs/a")
    assert response.status_code == 200
    assert "DELETED" in response.text
    mock_client.delete_job.assert_awaited_once_with("a")


async def test_delete_failure_changes_nothing(logged_in, mock_client):
    mock_client.delete_job = AsyncMock(return_value=None)
    response = await logged_in.delete("/jobs/a")
    assert response.status_code == 502
    assert "nothing was changed" in response.text


async def test_stop_seeding_reports_message(logged_in, mock_client):
    from medialab_web.schemas.actions import ActionResponse

    mock_client.stop_seeding = AsyncMock(
        return_value=ActionResponse(status="success", message="3 stopped")
    )
    response = await logged_in.post("/transfers/stop-seeding")
    assert response.status_code == 200
    assert "3 stopped" in response.text


async def test_active_row_renders_progress_bar_percent_speed_and_eta(logged_in, mock_client):
    mock_client.list_jobs = _jobs(make_job("DOWNLOADING", "a", progress=_progress()))
    text = (await logged_in.get("/partials/jobs")).text
    assert '<progress max="1" value="0.42"' in text
    assert "42% - 3.0 MB/s - ETA 12m" in text


async def test_unknown_eta_renders_dash(logged_in, mock_client):
    mock_client.list_jobs = _jobs(
        make_job("DOWNLOAD_SUBMITTED", "a", progress=_progress(eta_seconds=None))
    )
    assert "ETA -" in (await logged_in.get("/partials/jobs")).text


async def test_row_without_progress_has_no_bar(logged_in, mock_client):
    mock_client.list_jobs = _jobs(make_job("DOWNLOADING", "a"))
    text = (await logged_in.get("/partials/jobs")).text
    assert "<progress" not in text
    assert "ETA" not in text


async def test_partial_polls_fast_while_any_job_has_progress(logged_in, mock_client):
    mock_client.list_jobs = _jobs(
        make_job("DONE", "a"), make_job("DOWNLOADING", "b", progress=_progress())
    )
    text = (await logged_in.get("/partials/jobs")).text
    assert f'hx-trigger="every {JOBS_ACTIVE_REFRESH_SECONDS}s' in text
    assert f"every {JOBS_REFRESH_SECONDS}s" not in text


async def test_partial_polls_slow_when_nothing_is_downloading(logged_in):
    text = (await logged_in.get("/partials/jobs")).text
    assert f'hx-trigger="every {JOBS_REFRESH_SECONDS}s' in text
    assert f"every {JOBS_ACTIVE_REFRESH_SECONDS}s" not in text


async def test_partial_poll_keeps_the_status_filter(logged_in, mock_client):
    text = (await logged_in.get("/partials/jobs", params={"status_filter": "DELETED"})).text
    assert 'hx-get="/partials/jobs?status_filter=DELETED"' in text
    assert 'hx-swap="outerHTML"' in text


async def test_empty_partial_still_polls(logged_in, mock_client):
    mock_client.list_jobs = _jobs()
    text = (await logged_in.get("/partials/jobs")).text
    assert "No jobs" in text
    assert f'hx-trigger="every {JOBS_REFRESH_SECONDS}s' in text


# --- redo ---

_MOVIE_SCOPE = {"tmdb_id": 1, "title": "Dune", "year": "2021", "media_type": "movie"}
_SHOW_SCOPE = {"tmdb_id": 2, "title": "Lost", "year": "2004", "media_type": "show"}
_MAGNET = "magnet:?xt=urn:btih:def"


def _torrents(*results) -> AsyncMock:
    return AsyncMock(
        return_value=TorrentSearchResponse(
            status="success", message="", data={"1080p": list(results)}
        )
    )


def _torrent(name="Dune.2021.2160p-GRP") -> TorrentResult:
    return TorrentResult(
        fileName=name,
        fileUrl=_MAGNET,
        nbSeeders=5,
        nbLeechers=1,
        fileSize=2 * 1024**3,
        languages=[],
        multiAudio=False,
    )


def _pick(**fields) -> dict[str, str]:
    base = {"source_url": _MAGNET, "media_type": "movie", "tmdb_id": "1", "file_name": "x"}
    return {**base, **fields}


async def test_index_has_a_stage_and_the_searching_panel(logged_in):
    text = (await logged_in.get("/")).text
    assert 'id="stage" class="download-slot"' in text
    assert 'id="searching"' in text


async def test_redo_button_only_on_done_rows(logged_in):
    text = (await logged_in.get("/partials/jobs")).text
    assert text.count("/redo") == 1
    assert 'hx-get="/partials/jobs/a/redo"' in text
    assert 'hx-target="#stage"' in text


async def test_redo_partial_searches_the_movie_scope(logged_in, mock_client):
    mock_client.search_torrents = _torrents(_torrent())
    response = await logged_in.get("/partials/jobs/a/redo", params=_MOVIE_SCOPE)
    assert response.status_code == 200
    text = response.text
    mock_client.search_torrents.assert_awaited_once_with(
        "Dune 2021", MediaType.MOVIE, season=None, episode=None, alt_query=None
    )
    assert REDO_NOTICE in text
    assert 'hx-post="/partials/jobs/a/redo"' in text
    assert 'hx-post="/downloads"' not in text
    assert "Replace the original download with Dune.2021.2160p-GRP?" in text
    assert f'name="source_url" value="{_MAGNET}"' in text
    assert 'name="file_name" value="Dune.2021.2160p-GRP"' in text
    assert "Back to titles" not in text and "Change scope" not in text


async def test_redo_partial_searches_the_episode_scope(logged_in, mock_client):
    mock_client.search_torrents = _torrents(_torrent("Lost.S02E05-GRP"))
    text = (
        await logged_in.get(
            "/partials/jobs/a/redo", params={**_SHOW_SCOPE, "season": 2, "episode": 5}
        )
    ).text
    mock_client.search_torrents.assert_awaited_once_with(
        "Lost", MediaType.SHOW, season=2, episode=5, alt_query=None
    )
    assert "S02E05" in text
    assert 'name="season" value="2"' in text and 'name="episode" value="5"' in text


async def test_redo_partial_searches_the_season_scope(logged_in, mock_client):
    mock_client.search_torrents = _torrents()
    text = (await logged_in.get("/partials/jobs/a/redo", params={**_SHOW_SCOPE, "season": 2})).text
    mock_client.search_torrents.assert_awaited_once_with(
        "Lost", MediaType.SHOW, season=2, episode=None, alt_query=None
    )
    assert "Season 2" in text


async def test_redo_partial_searches_the_whole_series(logged_in, mock_client):
    mock_client.search_torrents = _torrents()
    await logged_in.get("/partials/jobs/a/redo", params=_SHOW_SCOPE)
    mock_client.search_torrents.assert_awaited_once_with(
        "Lost", MediaType.SHOW, season=None, episode=None, alt_query=None
    )


async def test_redo_partial_gateway_down(logged_in, mock_client):
    mock_client.search_torrents = AsyncMock(return_value=None)
    response = await logged_in.get("/partials/jobs/a/redo", params=_MOVIE_SCOPE)
    assert response.status_code == 502


async def test_done_row_carries_its_scope_into_the_redo_request(logged_in, mock_client):
    mock_client.list_jobs = _jobs(
        make_job("DONE", "a", media_type=MediaType.SHOW, tmdb_id=2, season=2, episode=5)
    )
    text = (await logged_in.get("/partials/jobs")).text
    assert '"season": 2' in text and '"episode": 5' in text
    assert '"media_type": "show"' in text


async def test_redo_calls_the_gateway_and_rerenders_the_table(logged_in, mock_client):
    new_job = make_job("DOWNLOAD_SUBMITTED", "n1", redo_of="a")
    mock_client.redo = AsyncMock(return_value=DownloadResponse(status="success", job=new_job))
    mock_client.list_jobs = _jobs(make_job("DELETED", "a", redone_by="n1"), new_job)
    response = await logged_in.post(
        "/partials/jobs/a/redo",
        data=_pick(
            media_type="show",
            tmdb_id="2",
            file_name="Lost.S02E05-GRP",
            season="2",
            episode="5",
            status_filter="DONE",
        ),
    )
    assert response.status_code == 200
    mock_client.redo.assert_awaited_once_with(
        "a", _MAGNET, MediaType.SHOW, 2, "Lost.S02E05-GRP", season=2, episode=5
    )
    mock_client.list_jobs.assert_awaited_once_with("DONE")
    text = response.text
    assert 'id="job-a"' in text and 'id="job-n1"' in text
    assert 'hx-swap-oob="true"' in text
    assert "Lost.S02E05-GRP" in text and "n1" in text


async def test_redo_whole_series_sends_no_scope(logged_in, mock_client):
    mock_client.redo = AsyncMock(
        return_value=DownloadResponse(status="success", job=make_job("DOWNLOAD_SUBMITTED", "n1"))
    )
    await logged_in.post(
        "/partials/jobs/a/redo",
        data=_pick(source_url="http://x/t.torrent", media_type="show", tmdb_id="2"),
    )
    mock_client.redo.assert_awaited_once_with(
        "a", "http://x/t.torrent", MediaType.SHOW, 2, "x", season=None, episode=None
    )


async def test_redo_shows_the_detail_for_a_retryable_code(logged_in, mock_client):
    mock_client.redo = AsyncMock(
        return_value=GatewayError(
            status_code=503, code="SOURCE_UNREACHABLE", detail="Source page unreachable; retry."
        )
    )
    response = await logged_in.post("/partials/jobs/a/redo", data=_pick())
    assert response.status_code == 502
    assert "unreachable" in response.text
    assert "Redo failed" not in response.text


async def test_redo_keeps_the_generic_message_for_an_unknown_code(logged_in, mock_client):
    mock_client.redo = AsyncMock(
        return_value=GatewayError(status_code=409, code="JOB_NOT_DONE", detail="not done")
    )
    response = await logged_in.post("/partials/jobs/a/redo", data=_pick())
    assert response.status_code == 502
    assert "Redo failed" in response.text


async def test_redo_rejects_garbage_link(logged_in, mock_client):
    mock_client.redo = AsyncMock()
    response = await logged_in.post(
        "/partials/jobs/a/redo", data=_pick(source_url="javascript:alert(1)")
    )
    assert response.status_code == 422
    mock_client.redo.assert_not_called()


async def test_redo_failure_shows_a_notice_and_changes_nothing(logged_in, mock_client):
    mock_client.redo = AsyncMock(return_value=None)
    response = await logged_in.post("/partials/jobs/a/redo", data=_pick())
    assert response.status_code == 502
    assert "Redo failed" in response.text
    assert "the original download is untouched" in response.text
    mock_client.list_jobs.assert_not_called()


async def test_rows_link_the_replaced_and_replacement_jobs(logged_in, mock_client):
    old_id = "0123456789abcdef"
    new_id = "fedcba9876543210"
    mock_client.list_jobs = _jobs(
        make_job("DELETED", old_id, redone_by=new_id),
        make_job("DOWNLOAD_SUBMITTED", new_id, redo_of=old_id),
    )
    text = (await logged_in.get("/partials/jobs", params={"status_filter": "DELETED"})).text
    assert f'href="/#job-{new_id}">Replaced by {new_id[:SHORT_ID_LENGTH]}</a>' in text
    assert f'href="/#job-{old_id}">Redo of {old_id[:SHORT_ID_LENGTH]}</a>' in text


async def test_rows_without_redo_links_render_none(logged_in):
    text = (await logged_in.get("/partials/jobs")).text
    assert "Replaced by" not in text and "Redo of" not in text


async def test_pages_tell_htmx_to_swap_error_responses(logged_in, mock_client):
    mock_client.list_jobs = AsyncMock(return_value=JobsResponse(status="success", jobs=[]))
    text = (await logged_in.get("/")).text
    assert 'name="htmx-config"' in text
    assert '"code": "[45]..", "swap": true' in text


async def test_storage_panel_shows_vpn_bound(logged_in, mock_client):
    text = (await logged_in.get("/partials/storage")).text
    assert "VPN" in text
    assert 'class="badge ok">bound<' in text


async def test_storage_panel_flags_vpn_not_bound(logged_in, mock_client):
    health = mock_client.health.return_value
    mock_client.health = AsyncMock(
        return_value=health.model_copy(update={"vpn_interface_bound": False})
    )
    text = (await logged_in.get("/partials/storage")).text
    assert 'class="badge bad">not bound<' in text


async def test_credentials_banner_is_empty_when_everything_is_ok(logged_in):
    text = (await logged_in.get("/partials/credentials")).text
    assert "Credential problem" not in text


async def test_credentials_banner_lists_invalid_keys_with_the_fix(logged_in, mock_client):
    from medialab_contracts import CREDENTIAL_TMDB_API_KEY, CredentialState, CredentialStatus

    health = mock_client.health.return_value
    mock_client.health = AsyncMock(
        return_value=health.model_copy(
            update={
                "credentials": {
                    CREDENTIAL_TMDB_API_KEY: CredentialState(
                        status=CredentialStatus.INVALID, detail="HTTP 401"
                    )
                }
            }
        )
    )
    text = (await logged_in.get("/partials/credentials")).text
    assert "Credential problem" in text
    assert "TMDB API key" in text and "HTTP 401" in text
    assert f"setup.cmd --fix {CREDENTIAL_TMDB_API_KEY}" in text


async def test_pages_poll_the_banner_but_login_does_not(client, logged_in):
    home = (await logged_in.get("/")).text
    assert 'hx-get="/partials/credentials"' in home
    login = (await client.get("/login")).text
    assert 'hx-get="/partials/credentials"' not in login


async def test_storage_panel_lists_credential_states(logged_in, mock_client):
    from medialab_contracts import CREDENTIAL_JELLYFIN_API_KEY, CredentialState, CredentialStatus

    health = mock_client.health.return_value
    mock_client.health = AsyncMock(
        return_value=health.model_copy(
            update={
                "credentials": {
                    CREDENTIAL_JELLYFIN_API_KEY: CredentialState(status=CredentialStatus.OK)
                }
            }
        )
    )
    text = (await logged_in.get("/partials/storage")).text
    assert "Jellyfin API key" in text
    assert 'class="badge ok">ok<' in text
