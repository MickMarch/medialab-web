"""HTMX fragments and actions for the jobs page. Every handler is one gateway
call and one re-rendered fragment."""

from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import HTMLResponse

from medialab_web.auth import require_session
from medialab_web.client import OrchestratorClient
from medialab_web.constants import (
    JOBS_ACTIVE_REFRESH_SECONDS,
    JOBS_REFRESH_SECONDS,
    RETRYABLE_STATUSES,
    TERMINAL_STATUS_DELETED,
)
from medialab_web.deps import get_client
from medialab_web.rendering import render
from medialab_web.schemas.jobs import JobView

router = APIRouter(dependencies=[Depends(require_session)])

_CLIENT = Depends(get_client)

_ERROR_FRAGMENT = "partials/error.html"


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


@router.get("/partials/jobs", response_class=HTMLResponse)
async def jobs_table(
    request: Request,
    status_filter: str | None = None,
    client: OrchestratorClient = _CLIENT,
) -> HTMLResponse:
    response = await client.list_jobs(status_filter or None)
    if response is None:
        return _error(request, "Could not reach the gateway for jobs.")
    jobs = [j for j in response.jobs if j.status != TERMINAL_STATUS_DELETED or status_filter]
    return render(
        request,
        "partials/jobs_table.html",
        {
            "jobs": jobs,
            "status_filter": status_filter or "",
            "retryable": RETRYABLE_STATUSES,
            "refresh_seconds": _refresh_seconds(jobs),
        },
    )


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


@router.post("/transfers/stop-seeding", response_class=HTMLResponse)
async def stop_seeding(request: Request, client: OrchestratorClient = _CLIENT) -> HTMLResponse:
    result = await client.stop_seeding()
    if result is None:
        return _error(request, "Stop seeding failed.")
    return render(request, "partials/notice.html", {"message": result.message})
