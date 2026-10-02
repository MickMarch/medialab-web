from medialab_contracts import (
    API_PREFIX,
    FollowRequest,
    MediaType,
    SeasonFollowMode,
    SeasonFollowState,
    WatchlistAddRequest,
    WatchlistItem,
    WatchlistKind,
    WatchlistResponse,
)

from medialab_web.client._base import _BaseClient
from medialab_web.constants import CHECK_TIMEOUT_SECONDS
from medialab_web.schemas.watchlist import FollowCheckResponse, FollowedShowView

_WATCHLIST = f"{API_PREFIX}/watchlist"


def _show_path(tmdb_id: int) -> str:
    return f"{_WATCHLIST}/{MediaType.SHOW.value}/{tmdb_id}"


class _WatchlistMixin(_BaseClient):
    async def list_watchlist(
        self, media_type: MediaType | None = None, kind: WatchlistKind | None = None
    ) -> WatchlistResponse | None:
        params: dict[str, str] = {}
        if media_type is not None:
            params["media_type"] = media_type.value
        if kind is not None:
            params["kind"] = kind.value
        data = await self._get(_WATCHLIST, params=params)
        return self._parse(WatchlistResponse, data)

    async def add_to_watchlist(
        self, media_type: MediaType, tmdb_id: int, item: WatchlistAddRequest
    ) -> WatchlistItem | None:
        data = await self._put(
            f"{_WATCHLIST}/{media_type.value}/{tmdb_id}", json=item.model_dump(mode="json")
        )
        return self._parse(WatchlistItem, data)

    async def remove_from_watchlist(self, media_type: MediaType, tmdb_id: int) -> bool:
        return await self._delete_no_content(f"{_WATCHLIST}/{media_type.value}/{tmdb_id}")

    async def follow_show(self, tmdb_id: int, request: FollowRequest) -> WatchlistItem | None:
        """Follow a saved show; the gateway answers 404 for a show not saved first."""
        data = await self._put(
            f"{_show_path(tmdb_id)}/follow", json=request.model_dump(mode="json")
        )
        return self._parse(WatchlistItem, data)

    async def unfollow_show(self, tmdb_id: int) -> bool:
        return await self._delete_no_content(f"{_show_path(tmdb_id)}/follow")

    async def pause_follow(self, tmdb_id: int) -> WatchlistItem | None:
        data = await self._post(f"{_show_path(tmdb_id)}/follow/pause")
        return self._parse(WatchlistItem, data)

    async def resume_follow(self, tmdb_id: int) -> WatchlistItem | None:
        data = await self._post(f"{_show_path(tmdb_id)}/follow/resume")
        return self._parse(WatchlistItem, data)

    async def check_follow(self, tmdb_id: int) -> FollowCheckResponse | None:
        """Run one follow check now; the gateway searches and submits before answering."""
        data = await self._post(
            f"{_show_path(tmdb_id)}/follow/check", timeout=CHECK_TIMEOUT_SECONDS
        )
        return self._parse(FollowCheckResponse, data)

    async def watchlist_episodes(self, tmdb_id: int) -> FollowedShowView | None:
        """The show view with what the follow submitted and still wants per
        episode, and the pack state per season."""
        data = await self._get(f"{_show_path(tmdb_id)}/episodes")
        return self._parse(FollowedShowView, data)

    async def decide_season(
        self, tmdb_id: int, season: int, mode: SeasonFollowMode
    ) -> SeasonFollowState | None:
        """How a season whose pack was not found continues."""
        data = await self._post(
            f"{_show_path(tmdb_id)}/seasons/{season}/decision", json={"mode": mode.value}
        )
        return self._parse(SeasonFollowState, data)

    async def retry_episode(self, tmdb_id: int, season: int, episode: int) -> bool:
        """Clear a submission so the next follow tick may fetch the episode again."""
        return await self._delete_no_content(
            f"{_show_path(tmdb_id)}/episodes/{season}/{episode}/submission"
        )
