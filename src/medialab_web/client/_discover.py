from medialab_contracts import (
    API_PREFIX,
    DiscoverResponse,
    GenresResponse,
    MediaType,
    WishlistAddRequest,
    WishlistItem,
    WishlistResponse,
)

from medialab_web.client._base import _BaseClient
from medialab_web.constants import FIRST_PAGE


class _DiscoverMixin(_BaseClient):
    async def discover(
        self, media_type: MediaType, genre: int | None = None, page: int = FIRST_PAGE
    ) -> DiscoverResponse | None:
        # None covers TMDB_UNAVAILABLE (503) as well as a gateway that is down.
        params: dict[str, int] = {"page": page}
        if genre is not None:
            params["genre"] = genre
        data = await self._get(f"{API_PREFIX}/discover/{media_type.value}", params=params)
        return self._parse(DiscoverResponse, data)

    async def discover_genres(self, media_type: MediaType) -> GenresResponse | None:
        data = await self._get(f"{API_PREFIX}/discover/{media_type.value}/genres")
        return self._parse(GenresResponse, data)

    async def list_wishlist(self, media_type: MediaType | None = None) -> WishlistResponse | None:
        params = {"media_type": media_type.value} if media_type else {}
        data = await self._get(f"{API_PREFIX}/wishlist", params=params)
        return self._parse(WishlistResponse, data)

    async def add_to_wishlist(
        self, media_type: MediaType, tmdb_id: int, item: WishlistAddRequest
    ) -> WishlistItem | None:
        data = await self._put(
            f"{API_PREFIX}/wishlist/{media_type.value}/{tmdb_id}", json=item.model_dump(mode="json")
        )
        return self._parse(WishlistItem, data)

    async def remove_from_wishlist(self, media_type: MediaType, tmdb_id: int) -> bool:
        return await self._delete_no_content(f"{API_PREFIX}/wishlist/{media_type.value}/{tmdb_id}")
