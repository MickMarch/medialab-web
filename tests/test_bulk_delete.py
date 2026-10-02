"""Select mode on the Jobs page: checkboxes, the sticky bar, one combined
plan, one confirmation, one result notice."""

from unittest.mock import AsyncMock

from medialab_web.constants import (
    BULK_BAR_ID,
    BULK_PLAN_ID,
    DELETE_SELECTED_LABEL,
    JOBS_SELECTED_TEXT,
    SELECT_LABEL,
    SELECT_MODE_CLASS,
)
from medialab_web.schemas.deletion import (
    BulkDeleteResult,
    BulkDeletionPlan,
    JobDeleteResult,
    JobDeletionPlan,
)
from tests.conftest import make_job
from tests.test_jobs_page import _jobs, _plan

DELETE_FORM = 'hx-post="/jobs/delete"'


def _bulk_plan(*entries: JobDeletionPlan) -> AsyncMock:
    return AsyncMock(return_value=BulkDeletionPlan(status="success", plans=list(entries)))


def _bulk_result(*entries: JobDeleteResult) -> AsyncMock:
    return AsyncMock(return_value=BulkDeleteResult(status="success", results=list(entries)))


async def test_index_has_the_select_toggle_bar_and_plan_slot(logged_in):
    text = (await logged_in.get("/")).text
    assert f">{SELECT_LABEL}<" in text
    assert f'id="{BULK_BAR_ID}"' in text and f'id="{BULK_PLAN_ID}"' in text
    assert JOBS_SELECTED_TEXT in text and DELETE_SELECTED_LABEL in text
    assert 'hx-post="/partials/jobs/plan"' in text
    assert "input[name='job_ids']:checked" in text
    assert SELECT_MODE_CLASS in text


async def test_rows_carry_a_checkbox_except_deleted(logged_in, mock_client):
    mock_client.list_jobs = _jobs(make_job("DONE", "a"), make_job("DELETED", "gone"))
    text = (await logged_in.get("/partials/jobs", params={"status_filter": "DELETED"})).text
    assert 'name="job_ids" value="a"' in text
    assert 'name="job_ids" value="gone"' not in text
    assert text.count('<td class="select">') == 2


async def test_poll_pauses_in_select_mode(logged_in):
    text = (await logged_in.get("/partials/jobs")).text
    assert f"!document.querySelector('.{SELECT_MODE_CLASS}')" in text
    assert "!document.querySelector('.plan-slot:not(:empty)')" in text


async def test_combined_plan_lists_jobs_and_refusals_and_counts_deletable(logged_in, mock_client):
    mock_client.bulk_deletion_plan = _bulk_plan(
        JobDeletionPlan(job=make_job("DONE", "a"), plan=_plan(job_id="a")),
        JobDeletionPlan(
            job=make_job("DONE", "b", resolved_title="Lost", resolved_year=2004),
            plan=_plan(job_id="b", refused="predates tracking", placed_paths=[]),
        ),
        JobDeletionPlan(job=None, plan=_plan(job_id="nope", refused="no such job")),
    )
    response = await logged_in.post("/partials/jobs/plan", data={"job_ids": ["a", "b", "nope"]})
    text = response.text
    mock_client.bulk_deletion_plan.assert_awaited_once_with(["a", "b", "nope"])
    assert "Nothing has happened yet" in text
    assert "Dune (2021).mkv" in text
    assert "Lost (2004)" in text and "predates tracking" in text
    assert text.count('<code class="release">') == 2  # release names tell episodes apart
    assert "nope" in text and "no such job" in text
    assert DELETE_FORM in text
    assert text.count('name="job_ids"') == 1 and 'name="job_ids" value="a"' in text
    assert ">Delete 1 job<" in text
    mock_client.bulk_delete.assert_not_called()


async def test_combined_plan_with_nothing_deletable_has_no_delete_button(logged_in, mock_client):
    mock_client.bulk_deletion_plan = _bulk_plan(
        JobDeletionPlan(job=None, plan=_plan(job_id="nope", refused="no such job"))
    )
    text = (await logged_in.post("/partials/jobs/plan", data={"job_ids": "nope"})).text
    assert DELETE_FORM not in text and "Cannot delete automatically" in text


async def test_combined_plan_gateway_down(logged_in, mock_client):
    mock_client.bulk_deletion_plan = AsyncMock(return_value=None)
    response = await logged_in.post("/partials/jobs/plan", data={"job_ids": "a"})
    assert response.status_code == 502


async def test_bulk_delete_calls_gateway_and_rerenders_the_table_with_a_notice(
    logged_in, mock_client
):
    mock_client.bulk_delete = _bulk_result(
        JobDeleteResult(job_id="a", job=make_job("DELETED", "a")),
        JobDeleteResult(
            job_id="b",
            job=make_job("DONE", "b", resolved_title="Lost", resolved_year=2004),
            error="predates tracking",
        ),
        JobDeleteResult(job_id="c", job=make_job("DELETED", "c")),
    )
    mock_client.list_jobs = _jobs(make_job("DONE", "b"))
    response = await logged_in.post(
        "/jobs/delete",
        data={"job_ids": ["a", "b", "c"], "status_filter": ""},
    )
    text = response.text
    mock_client.bulk_delete.assert_awaited_once_with(["a", "b", "c"])
    assert "Deleted 2 jobs" in text and "1 could not be deleted" in text
    assert "Lost (2004)" in text and "predates tracking" in text
    assert 'hx-swap-oob="true"' in text and 'id="jobs-poll"' in text
    mock_client.list_jobs.assert_awaited_once_with(None)


async def test_bulk_delete_all_good_has_no_refused_section(logged_in, mock_client):
    mock_client.bulk_delete = _bulk_result(
        JobDeleteResult(job_id="a", job=make_job("DELETED", "a"))
    )
    mock_client.list_jobs = _jobs()
    text = (await logged_in.post("/jobs/delete", data={"job_ids": "a"})).text
    assert "Deleted 1 job" in text and "could not be deleted" not in text


async def test_bulk_delete_gateway_down(logged_in, mock_client):
    mock_client.bulk_delete = AsyncMock(return_value=None)
    response = await logged_in.post("/jobs/delete", data={"job_ids": "a"})
    assert response.status_code == 502 and "nothing was changed" in response.text
