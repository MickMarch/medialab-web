from medialab_contracts import API_PREFIX, MediaType

from medialab_web.client._base import _BaseClient
from medialab_web.schemas.tmdb import TmdbMediaDetailResponse, TmdbSearchResponse


class _TmdbMixin(_BaseClient):
    async def search_tmdb(self, query: str) -> TmdbSearchResponse | None:
        data = await self._get(f"{API_PREFIX}/search/tmdb", params={"query": query})
        return self._parse(TmdbSearchResponse, data)

    async def _tmdb_detail(
        self, media_type: MediaType, tmdb_id: int
    ) -> TmdbMediaDetailResponse | None:
        data = await self._get(f"{API_PREFIX}/search/tmdb/{media_type.value}/{tmdb_id}")
        return self._parse(TmdbMediaDetailResponse, data)

    async def search_tmdb_movie(self, tmdb_id: int) -> TmdbMediaDetailResponse | None:
        return await self._tmdb_detail(MediaType.MOVIE, tmdb_id)

    async def search_tmdb_show(self, tmdb_id: int) -> TmdbMediaDetailResponse | None:
        return await self._tmdb_detail(MediaType.SHOW, tmdb_id)
