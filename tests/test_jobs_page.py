from unittest.mock import AsyncMock

from medialab_contracts import JobProgress

from medialab_web.constants import JOBS_ACTIVE_REFRESH_SECONDS, JOBS_REFRESH_SECONDS
from medialab_web.schemas.deletion import DeletionPlan
from medialab_web.schemas.jobs import JobsResponse
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
    assert "42% - 3 MB/s - ETA 12m" in text


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
