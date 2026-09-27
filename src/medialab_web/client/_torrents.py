from medialab_contracts import API_PREFIX, MediaType

from medialab_web.client._base import _BaseClient
from medialab_web.schemas.downloads import DownloadResponse
from medialab_web.schemas.torrents import TorrentSearchResponse

_DOWNLOAD_ACCEPTED = 202


class _TorrentsMixin(_BaseClient):
    async def search_torrents(
        self,
        query: str,
        media_type: MediaType,
        season: int | None = None,
        episode: int | None = None,
        alt_query: str | None = None,
    ) -> TorrentSearchResponse | None:
        params: dict[str, str | int] = {"query": query, "media_type": media_type.value}
        if alt_query:
            params["alt_query"] = alt_query
        if season is not None:
            params["season"] = season
        if episode is not None:
            params["episode"] = episode
        data = await self._get(
            f"{API_PREFIX}/search/torrents",
            params=params,
            timeout=self._torrent_search_timeout,
        )
        return self._parse(TorrentSearchResponse, data)

    async def download(
        self,
        source_url: str,
        media_type: MediaType,
        tmdb_id: int,
        release_name: str = "",
    ) -> DownloadResponse | None:
        # source_url is whatever the picked result carried - a magnet or an http
        # .torrent URL. The gateway resolves placement and fans out; it requires
        # media_type + tmdb_id (no title guessing).
        data = await self._post(
            f"{API_PREFIX}/download",
            json={
                "source_url": source_url,
                "media_type": media_type.value,
                "tmdb_id": tmdb_id,
                "release_name": release_name,
            },
            expected_status=_DOWNLOAD_ACCEPTED,
        )
        return self._parse(DownloadResponse, data)
