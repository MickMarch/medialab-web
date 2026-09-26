from medialab_contracts import API_PREFIX

from medialab_web.client._base import _BaseClient
from medialab_web.schemas.deletion import DeletionPlan
from medialab_web.schemas.jobs import JobsResponse, JobView


class _JobsMixin(_BaseClient):
    async def list_jobs(self, status: str | None = None) -> JobsResponse | None:
        params = {"status": status} if status else None
        data = await self._get(f"{API_PREFIX}/jobs", params=params)
        return self._parse(JobsResponse, data)

    async def retry_job(self, job_id: str) -> JobView | None:
        # The gateway re-enters the worker from the last good state and returns
        # the updated job (not wrapped in a status envelope).
        data = await self._post(f"{API_PREFIX}/jobs/{job_id}/retry")
        return self._parse(JobView, data)

    async def deletion_plan(self, job_id: str) -> DeletionPlan | None:
        # Read-only: what a delete would remove, shown before confirming.
        data = await self._get(f"{API_PREFIX}/jobs/{job_id}/deletion-plan")
        return self._parse(DeletionPlan, data)

    async def delete_job(self, job_id: str) -> JobView | None:
        # Deletes may take a while (file removal + Jellyfin); use the search timeout.
        data = await self._delete(
            f"{API_PREFIX}/jobs/{job_id}", timeout=self._torrent_search_timeout
        )
        return self._parse(JobView, data)
