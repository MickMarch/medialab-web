from medialab_contracts import API_PREFIX, ShowBrowseResponse

from medialab_web.client._base import _BaseClient
from medialab_web.constants import SHOWS_PATH


class _ShowsMixin(_BaseClient):
    async def browse_show(self, tmdb_id: int) -> ShowBrowseResponse | None:
        # None covers TMDB_UNAVAILABLE (503), a downstream 502 and a gateway
        # that is down; the page renders a friendly message for all of them.
        data = await self._get(f"{API_PREFIX}{SHOWS_PATH}/{tmdb_id}")
        return self._parse(ShowBrowseResponse, data)
