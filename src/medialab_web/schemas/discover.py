"""A poster card's fields as they round-trip through hx-vals and forms."""

from medialab_contracts import DiscoverItem, WatchlistAddRequest, WatchlistItem, WatchlistKind
from pydantic import field_validator

from medialab_web.media import from_tmdb_media_type
from medialab_web.schemas.tmdb import TmdbSearchResult


class CardItem(DiscoverItem):
    """``DiscoverItem`` read from a form or query string, where a missing
    year, poster or watchlist kind arrives as an empty string."""

    @field_validator("year", "poster_path", "watchlist_kind", mode="before")
    @classmethod
    def _blank_is_none(cls, value: object) -> object:
        return value or None

    @classmethod
    def from_watchlist(cls, item: WatchlistItem) -> "CardItem":
        return cls.model_validate(
            {
                **item.model_dump(exclude={"added_at", "kind", "follow"}),
                "on_watchlist": True,
                "watchlist_kind": item.kind,
            }
        )

    @classmethod
    def from_search(cls, result: TmdbSearchResult) -> "CardItem":
        """A title search result as a card; the caller has checked its media type."""
        return cls.model_validate(
            {
                **result.model_dump(exclude={"media_type"}),
                "media_type": from_tmdb_media_type(result.media_type),
            }
        )

    @property
    def following(self) -> bool:
        return self.watchlist_kind is WatchlistKind.FOLLOWING

    def with_kind(self, kind: WatchlistKind | None) -> "CardItem":
        return self.model_copy(update={"on_watchlist": kind is not None, "watchlist_kind": kind})

    def watchlist_request(self) -> WatchlistAddRequest:
        return WatchlistAddRequest(
            title=self.title, year=self.year, poster_path=self.poster_path, overview=self.overview
        )
