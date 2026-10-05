"""HTMX fragments and actions for the jobs page. Every handler is one gateway
call and one re-rendered fragment."""

from fastapi import APIRouter, Depends, Form, Request, status
from fastapi.responses import HTMLResponse
from medialab_contracts import MediaType

from medialab_web.auth import require_session
from medialab_web.client import OrchestratorClient
from medialab_web.constants import (
    JOBS_ACTIVE_REFRESH_SECONDS,
    JOBS_REFRESH_SECONDS,
    REDO_FAILED_MESSAGE,
    REDO_FAILED_NOTICE,
    REDO_NOTICE,
    RETRYABLE_STATUSES,
    TERMINAL_STATUS_DELETED,
)
from medialab_web.deps import get_client
from medialab_web.rendering import render
from medialab_web.routes.search import (
    failure_message,
    invalid_link,
    is_torrent_link,
    render_torrents,
    scope_numbers,
)
from medialab_web.schemas.downloads import DownloadResponse
from medialab_web.schemas.jobs import JobView

router = APIRouter(dependencies=[Depends(require_session)])

_CLIENT = Depends(get_client)

_ERROR_FRAGMENT = "partials/error.html"
_JOBS_TABLE = "partials/jobs_table.html"

_SOURCE_URL = Form(...)
_MEDIA_TYPE = Form(...)
_TMDB_ID = Form(...)
_FILE_NAME = Form(...)
_SEASON = Form(None)
_EPISODE = Form(None)
_STATUS_FILTER = Form(None)
_JOB_IDS = Form(...)


def _row(request: Request, job: JobView, notice: str | None = None) -> HTMLResponse:
    return render(request, "partials/job_row.html", {"job": job, "notice": notice})


def _refresh_seconds(jobs: list[JobView]) -> int:
    """The jobs partial polls fast only while something is downloading."""
    if any(job.progress is not None for job in jobs):
        return JOBS_ACTIVE_REFRESH_SECONDS
    return JOBS_REFRESH_SECONDS


def _error(request: Request, message: str) -> HTMLResponse:
    return render(
        request, _ERROR_FRAGMENT, {"message": message}, status_code=status.HTTP_502_BAD_GATEWAY
    )


async def _table_context(
    client: OrchestratorClient, status_filter: str | None
) -> dict[str, object] | None:
    """The jobs table's context, or None when the gateway is unreachable."""
    response = await client.list_jobs(status_filter or None)
    if response is None:
        return None
    jobs = [j for j in response.jobs if j.status != TERMINAL_STATUS_DELETED or status_filter]
    return {
        "jobs": jobs,
        "status_filter": status_filter or "",
        "retryable": RETRYABLE_STATUSES,
        "refresh_seconds": _refresh_seconds(jobs),
    }


@router.get("/partials/jobs", response_class=HTMLResponse)
async def jobs_table(
    request: Request,
    status_filter: str | None = None,
    client: OrchestratorClient = _CLIENT,
) -> HTMLResponse:
    context = await _table_context(client, status_filter)
    if context is None:
        return _error(request, "Could not reach the gateway for jobs.")
    return render(request, _JOBS_TABLE, context)


@router.get("/partials/storage", response_class=HTMLResponse)
async def storage_panel(request: Request, client: OrchestratorClient = _CLIENT) -> HTMLResponse:
    usage = await client.get_storage()
    health = await client.health()
    return render(request, "partials/storage.html", {"usage": usage, "health": health})


@router.post("/jobs/{job_id}/retry", response_class=HTMLResponse)
async def retry(
    request: Request, job_id: str, client: OrchestratorClient = _CLIENT
) -> HTMLResponse:
    job = await client.retry_job(job_id)
    if job is None:
        return _error(request, "Retry failed; the job is unchanged.")
    return _row(request, job, notice="Retry queued.")


@router.post("/jobs/{job_id}/dismiss", response_class=HTMLResponse)
async def dismiss(
    request: Request, job_id: str, client: OrchestratorClient = _CLIENT
) -> HTMLResponse:
    job = await client.dismiss_job(job_id)
    if job is None:
        return _error(request, "Dismiss failed; the job is unchanged.")
    return _row(request, job, notice="Dismissed.")


@router.post("/jobs/dismiss", response_class=HTMLResponse)
async def bulk_dismiss(
    request: Request,
    job_ids: list[str] = _JOB_IDS,
    status_filter: str | None = _STATUS_FILTER,
    client: OrchestratorClient = _CLIENT,
) -> HTMLResponse:
    """Dismiss the checked jobs in one gateway call, then the whole table
    again with a notice; refused jobs are named with the reason. No plan step:
    dismiss touches no files."""
    result = await client.bulk_dismiss(job_ids)
    if result is None:
        return _error(request, "Bulk dismiss failed; nothing was changed.")
    dismissed = [entry for entry in result.results if entry.dismissed]
    failed = [entry for entry in result.results if not entry.dismissed]
    context = await _table_context(client, status_filter)
    return render(
        request,
        "partials/bulk_dismissed.html",
        {"dismissed": dismissed, "failed": failed, "table": context},
    )


@router.get("/jobs/{job_id}/plan", response_class=HTMLResponse)
async def deletion_plan(
    request: Request, job_id: str, client: OrchestratorClient = _CLIENT
) -> HTMLResponse:
    plan = await client.deletion_plan(job_id)
    if plan is None:
        return _error(request, "Could not fetch the deletion plan.")
    return render(request, "partials/plan.html", {"plan": plan, "job_id": job_id})


@router.delete("/jobs/{job_id}", response_class=HTMLResponse)
async def delete(
    request: Request, job_id: str, client: OrchestratorClient = _CLIENT
) -> HTMLResponse:
    job = await client.delete_job(job_id)
    if job is None:
        return _error(request, "Delete failed; nothing was changed.")
    return _row(request, job, notice="Deleted.")


@router.post("/partials/jobs/plan", response_class=HTMLResponse)
async def bulk_deletion_plan(
    request: Request, job_ids: list[str] = _JOB_IDS, client: OrchestratorClient = _CLIENT
) -> HTMLResponse:
    """One combined plan for the checked rows, deletable jobs first."""
    plans = await client.bulk_deletion_plan(job_ids)
    if plans is None:
        return _error(request, "Could not fetch the deletion plan.")
    deletable = [entry for entry in plans.plans if not entry.plan.refused]
    refused = [entry for entry in plans.plans if entry.plan.refused]
    return render(request, "partials/bulk_plan.html", {"deletable": deletable, "refused": refused})


@router.post("/jobs/delete", response_class=HTMLResponse)
async def bulk_delete(
    request: Request,
    job_ids: list[str] = _JOB_IDS,
    status_filter: str | None = _STATUS_FILTER,
    client: OrchestratorClient = _CLIENT,
) -> HTMLResponse:
    """Delete the confirmed jobs in one gateway call, then the whole table
    again with a notice; refused or failed jobs are named with the reason."""
    result = await client.bulk_delete(job_ids)
    if result is None:
        return _error(request, "Bulk delete failed; nothing was changed.")
    deleted = [entry for entry in result.results if entry.deleted]
    failed = [entry for entry in result.results if not entry.deleted]
    context = await _table_context(client, status_filter)
    return render(
        request,
        "partials/bulk_deleted.html",
        {"deleted": deleted, "failed": failed, "table": context},
    )


@router.get("/partials/jobs/{job_id}/redo", response_class=HTMLResponse)
async def redo_torrents(
    request: Request,
    job_id: str,
    tmdb_id: int,
    title: str,
    year: str,
    media_type: MediaType,
    season: str | None = None,
    episode: str | None = None,
    failed: bool = False,
    client: OrchestratorClient = _CLIENT,
) -> HTMLResponse:
    # The row sends the job's own scope (see ``redo_vals``); a job with neither
    # season nor episode searches the whole series. ``failed`` marks a redo of
    # a flagged job, which replaces nothing in the library.
    return await render_torrents(
        request,
        client,
        tmdb_id,
        title,
        year,
        media_type,
        season,
        episode,
        redo_job_id=job_id,
        redo_notice=REDO_FAILED_NOTICE if failed else REDO_NOTICE,
    )


@router.post("/partials/jobs/{job_id}/redo", response_class=HTMLResponse)
async def redo(
    request: Request,
    job_id: str,
    source_url: str = _SOURCE_URL,
    media_type: MediaType = _MEDIA_TYPE,
    tmdb_id: int = _TMDB_ID,
    file_name: str = _FILE_NAME,
    season: str | None = _SEASON,
    episode: str | None = _EPISODE,
    status_filter: str | None = _STATUS_FILTER,
    client: OrchestratorClient = _CLIENT,
) -> HTMLResponse:
    """Replace ``job_id`` with the picked torrent: one gateway call, then the
    whole table again so the replaced and the replacement rows both update."""
    if not is_torrent_link(source_url):
        return invalid_link(request)
    season_number, episode_number = scope_numbers(season, episode)
    response = await client.redo(
        job_id,
        source_url,
        media_type,
        tmdb_id,
        file_name,
        season=season_number,
        episode=episode_number,
    )
    if not isinstance(response, DownloadResponse):
        return _error(request, failure_message(response, REDO_FAILED_MESSAGE))
    context = await _table_context(client, status_filter)
    return render(
        request,
        "partials/redo_started.html",
        {
            "job": response.job,
            "replaced_id": job_id,
            "file_name": file_name,
            "table": context,
        },
    )


@router.post("/transfers/stop-seeding", response_class=HTMLResponse)
async def stop_seeding(request: Request, client: OrchestratorClient = _CLIENT) -> HTMLResponse:
    result = await client.stop_seeding()
    if result is None:
        return _error(request, "Stop seeding failed.")
    return render(request, "partials/notice.html", {"message": result.message})
