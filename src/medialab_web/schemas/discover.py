"""A poster card's fields as they round-trip through hx-vals and forms."""

from medialab_contracts import DiscoverItem, WishlistAddRequest
from pydantic import field_validator


class CardItem(DiscoverItem):
    """``DiscoverItem`` read from a form or query string, where a missing
    year or poster arrives as an empty string."""

    @field_validator("year", "poster_path", mode="before")
    @classmethod
    def _blank_is_none(cls, value: object) -> object:
        return value or None

    def wishlist_request(self) -> WishlistAddRequest:
        return WishlistAddRequest(
            title=self.title, year=self.year, poster_path=self.poster_path, overview=self.overview
        )
