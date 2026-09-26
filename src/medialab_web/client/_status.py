from medialab_contracts import API_PREFIX

from medialab_web.client._base import _BaseClient
from medialab_web.schemas.actions import ActionResponse, CacheClearResponse
from medialab_web.schemas.system import DiskUsageResponse, HealthResponse
from medialab_web.schemas.transfers import MergedTransfersResponse

_ACCEPTED = 202


class _StatusMixin(_BaseClient):
    async def health(self) -> HealthResponse | None:
        data = await self._get(f"{API_PREFIX}/health")
        return self._parse(HealthResponse, data)

    async def get_transfers(self) -> MergedTransfersResponse | None:
        data = await self._get(f"{API_PREFIX}/transfers")
        return self._parse(MergedTransfersResponse, data)

    async def get_storage(self) -> DiskUsageResponse | None:
        # The gateway resolves the storage path itself; no path arg from the web UI.
        data = await self._get(f"{API_PREFIX}/storage")
        return self._parse(DiskUsageResponse, data)

    async def stop_seeding(self) -> ActionResponse | None:
        # Pauses every seeding (completed) torrent; never touches an in-progress
        # download. The gateway answers 202 with the downloader's envelope.
        data = await self._post(f"{API_PREFIX}/transfers/stop-seeding", expected_status=_ACCEPTED)
        return self._parse(ActionResponse, data)

    async def clear_search_cache(self) -> CacheClearResponse | None:
        data = await self._delete(f"{API_PREFIX}/search/cache")
        return self._parse(CacheClearResponse, data)
