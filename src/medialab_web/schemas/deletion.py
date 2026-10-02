from pydantic import BaseModel

from medialab_web.schemas.jobs import JobView


class DeletionPlan(BaseModel):
    """What ``DELETE /jobs/{id}`` would remove, as the gateway computes it.
    Shown verbatim to the user before the confirm button."""

    status: str
    job_id: str
    torrent: bool
    download_folder: str | None = None
    placed_paths: list[str] = []
    scan_path: str | None = None
    refused: str | None = None


class JobDeletionPlan(BaseModel):
    """One entry of ``POST /jobs/deletion-plan``; ``job`` is None for an unknown id."""

    job: JobView | None
    plan: DeletionPlan


class BulkDeletionPlan(BaseModel):
    status: str
    plans: list[JobDeletionPlan]


class JobDeleteResult(BaseModel):
    """One entry of ``POST /jobs/delete``; ``error`` is the refusal or failure."""

    job_id: str
    job: JobView | None
    error: str | None = None

    @property
    def deleted(self) -> bool:
        return self.error is None


class BulkDeleteResult(BaseModel):
    status: str
    results: list[JobDeleteResult]
