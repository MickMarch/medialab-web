"""Attention rows offer the action that resolves them; Dismiss closes a job
without touching files, singly or in bulk. Spec: dismiss-attention-jobs."""

from unittest.mock import AsyncMock

from medialab_web.constants import (
    DISMISS_LABEL,
    DISMISS_SELECTED_LABEL,
    REDO_FAILED_NOTICE,
    REDO_NOTICE,
    STATUS_DISMISSED,
)
from medialab_web.schemas.dismiss import BulkDismissResult, JobDismissResult
from tests.conftest import make_job
from tests.test_jobs_page import _MOVIE_SCOPE, _jobs, _torrent, _torrents

TORRENT_GONE = "torrent no longer in qBittorrent"


def _bulk_result(*entries: JobDismissResult) -> AsyncMock:
    return AsyncMock(return_value=BulkDismissResult(status="success", results=list(entries)))


async def test_torrent_gone_row_offers_redo_and_dismiss_not_retry(logged_in, mock_client):
    mock_client.list_jobs = _jobs(
        make_job("NEEDS_ATTENTION", "g", last_error=TORRENT_GONE, attention_cause="TORRENT_GONE")
    )
    text = (await logged_in.get("/partials/jobs")).text
    assert 'hx-get="/partials/jobs/g/redo"' in text
    assert 'hx-post="/jobs/g/dismiss"' in text
    assert "/retry" not in text


async def test_other_attention_rows_offer_retry_and_dismiss_not_redo(logged_in, mock_client):
    mock_client.list_jobs = _jobs(
        make_job("NEEDS_ATTENTION", "r", last_error="RENAME: x", attention_cause="RENAME"),
        make_job("FAILED", "f", last_error="SCAN: y", attention_cause="SCAN"),
    )
    text = (await logged_in.get("/partials/jobs")).text
    assert 'hx-post="/jobs/r/retry"' in text and 'hx-post="/jobs/r/dismiss"' in text
    assert 'hx-post="/jobs/f/retry"' in text and 'hx-post="/jobs/f/dismiss"' in text
    assert "/redo" not in text


async def test_done_and_dismissed_rows_have_no_dismiss(logged_in, mock_client):
    mock_client.list_jobs = _jobs(make_job("DONE", "a"), make_job(STATUS_DISMISSED, "d"))
    text = (await logged_in.get("/partials/jobs")).text
    assert "/dismiss" not in text
    assert "/retry" not in text


async def test_dismissed_row_is_muted_and_keeps_delete(logged_in, mock_client):
    mock_client.list_jobs = _jobs(make_job(STATUS_DISMISSED, "d", last_error=TORRENT_GONE))
    text = (await logged_in.get("/partials/jobs")).text
    assert 'class="status-dismissed"' in text
    assert 'hx-get="/jobs/d/plan"' in text
    assert 'name="job_ids" value="d"' in text


async def test_dismissed_rows_show_by_default(logged_in, mock_client):
    mock_client.list_jobs = _jobs(make_job(STATUS_DISMISSED, "d"), make_job("DELETED", "c"))
    text = (await logged_in.get("/partials/jobs")).text
    assert 'id="job-d"' in text and 'id="job-c"' not in text


async def test_status_filter_offers_dismissed(logged_in):
    text = (await logged_in.get("/")).text
    assert f'<option value="{STATUS_DISMISSED}"' in text


async def test_dismiss_swaps_row_with_a_notice(logged_in, mock_client):
    mock_client.dismiss_job = AsyncMock(
        return_value=make_job(STATUS_DISMISSED, "g", dismissed_at="2026-10-04T00:00:00+00:00")
    )
    response = await logged_in.post("/jobs/g/dismiss")
    assert response.status_code == 200
    assert STATUS_DISMISSED in response.text and "Dismissed." in response.text
    mock_client.dismiss_job.assert_awaited_once_with("g")


async def test_dismiss_failure_changes_nothing(logged_in, mock_client):
    mock_client.dismiss_job = AsyncMock(return_value=None)
    response = await logged_in.post("/jobs/g/dismiss")
    assert response.status_code == 502 and "unchanged" in response.text


async def test_redo_from_an_attention_row_says_it_replaces_the_failed_download(
    logged_in, mock_client
):
    mock_client.search_torrents = _torrents(_torrent())
    response = await logged_in.get("/partials/jobs/g/redo", params={**_MOVIE_SCOPE, "failed": "1"})
    assert response.status_code == 200
    assert REDO_FAILED_NOTICE in response.text and REDO_NOTICE not in response.text


async def test_attention_redo_button_marks_the_download_as_failed(logged_in, mock_client):
    mock_client.list_jobs = _jobs(
        make_job("NEEDS_ATTENTION", "g", last_error=TORRENT_GONE, attention_cause="TORRENT_GONE")
    )
    text = (await logged_in.get("/partials/jobs")).text
    assert '"failed": 1' in text or "&#34;failed&#34;: 1" in text


async def test_bulk_bar_has_dismiss_selected(logged_in):
    text = (await logged_in.get("/")).text
    assert DISMISS_SELECTED_LABEL in text
    assert 'hx-post="/jobs/dismiss"' in text
    assert DISMISS_LABEL in text


async def test_bulk_dismiss_calls_gateway_and_rerenders_the_table_with_a_notice(
    logged_in, mock_client
):
    mock_client.bulk_dismiss = _bulk_result(
        JobDismissResult(job_id="g", job=make_job(STATUS_DISMISSED, "g")),
        JobDismissResult(
            job_id="a",
            job=make_job("DONE", "a", resolved_title="Lost", resolved_year=2004),
            error="only a flagged job can be dismissed",
        ),
        JobDismissResult(job_id="h", job=make_job(STATUS_DISMISSED, "h")),
    )
    mock_client.list_jobs = _jobs(make_job("DONE", "a"))
    response = await logged_in.post(
        "/jobs/dismiss", data={"job_ids": ["g", "a", "h"], "status_filter": ""}
    )
    text = response.text
    mock_client.bulk_dismiss.assert_awaited_once_with(["g", "a", "h"])
    assert "Dismissed 2 jobs" in text and "1 could not be dismissed" in text
    assert "Lost (2004)" in text and "only a flagged job" in text
    assert 'hx-swap-oob="true"' in text and 'id="jobs-poll"' in text
    mock_client.list_jobs.assert_awaited_once_with(None)


async def test_bulk_dismiss_all_good_has_no_refused_section(logged_in, mock_client):
    mock_client.bulk_dismiss = _bulk_result(
        JobDismissResult(job_id="g", job=make_job(STATUS_DISMISSED, "g"))
    )
    mock_client.list_jobs = _jobs()
    text = (await logged_in.post("/jobs/dismiss", data={"job_ids": "g"})).text
    assert "Dismissed 1 job" in text and "could not be dismissed" not in text


async def test_bulk_dismiss_gateway_down(logged_in, mock_client):
    mock_client.bulk_dismiss = AsyncMock(return_value=None)
    response = await logged_in.post("/jobs/dismiss", data={"job_ids": "g"})
    assert response.status_code == 502 and "nothing was changed" in response.text
