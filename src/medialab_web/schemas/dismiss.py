from pydantic import BaseModel

from medialab_web.schemas.jobs import JobView


class JobDismissResult(BaseModel):
    """One entry of ``POST /jobs/dismiss``; ``error`` is the refusal or
    "no such job"."""

    job_id: str
    job: JobView | None
    error: str | None = None

    @property
    def dismissed(self) -> bool:
        return self.error is None


class BulkDismissResult(BaseModel):
    status: str
    results: list[JobDismissResult]
