"""Watchlist forms and the gateway responses medialab-contracts does not model."""

from enum import Enum

from medialab_contracts import (
    DEFAULT_FOLLOW_RESOLUTION,
    FollowRequest,
    FollowStart,
    FollowStartMode,
    SeasonFollowState,
    ShowBrowseResponse,
)
from pydantic import BaseModel, field_validator

from medialab_web.schemas.discover import CardItem


class FollowCheckResponse(BaseModel):
    """Answer of ``POST /watchlist/show/{tmdb_id}/follow/check``: the episode codes submitted."""

    submitted: list[str] = []


class FollowedShowView(ShowBrowseResponse):
    """Answer of ``GET /watchlist/show/{tmdb_id}/episodes``: the show view
    plus the per-season pack state of every season that has one."""

    seasons_follow: list[SeasonFollowState] = []

    def season_states(self) -> dict[int, SeasonFollowState]:
        return {state.season: state for state in self.seasons_follow}


class FollowView(str, Enum):
    """Where the follow picker was opened: inline in a card's actions, which
    re-render, or on the watchlist page, which moves to the Following tab."""

    INLINE = "inline"
    PAGE = "page"


class FollowCard(CardItem):
    """A card plus where its follow picker lives; the picker and its Cancel
    carry both."""

    view: FollowView = FollowView.INLINE

    @property
    def card(self) -> CardItem:
        return CardItem.model_validate(self.model_dump(exclude={"view"}))


class FollowForm(FollowCard):
    """The follow picker as submitted: the card, the view, the start point
    and the resolution."""

    mode: FollowStartMode
    season: int | None = None
    episode: int | None = None
    resolution: str = DEFAULT_FOLLOW_RESOLUTION

    @field_validator("season", "episode", mode="before")
    @classmethod
    def _blank_scope_is_none(cls, value: object) -> object:
        return value or None

    def follow_request(self) -> FollowRequest:
        """The gateway body; season and episode only count for a ``from`` start."""
        scoped = self.mode is FollowStartMode.FROM
        return FollowRequest(
            start=FollowStart(
                mode=self.mode,
                season=self.season if scoped else None,
                episode=self.episode if scoped else None,
            ),
            resolution=self.resolution,
        )
