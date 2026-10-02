"""The show page: seasons and episodes, each with a Find torrents button that
enters the torrent step with its scope preset. A followed show reads its
episodes from the watchlist view, which adds what the follow submitted."""

from collections import defaultdict

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from medialab_contracts import EpisodeState, MediaType, Season, ShowBrowseResponse, WatchlistKind

from medialab_web.auth import require_session
from medialab_web.client import OrchestratorClient
from medialab_web.constants import MIN_TARGETABLE_SEASON, SHOW_PATH
from medialab_web.deps import get_client
from medialab_web.rendering import render
from medialab_web.routes.search import search_timeout_seconds
from medialab_web.schemas.discover import CardItem
from medialab_web.schemas.watchlist import FollowedShowView

router = APIRouter(dependencies=[Depends(require_session)])

_CLIENT = Depends(get_client)


def _seasons_with_episodes(
    show: ShowBrowseResponse,
) -> list[tuple[Season, list[EpisodeState]]]:
    """Seasons in number order, each paired with its episodes in episode order."""
    by_season: dict[int, list[EpisodeState]] = defaultdict(list)
    for episode in show.episodes:
        by_season[episode.season].append(episode)
    return [
        (season, sorted(by_season[season.season], key=lambda e: e.episode))
        for season in sorted(show.seasons, key=lambda s: s.season)
    ]


def picker_seasons(show: ShowBrowseResponse) -> list[dict[str, int]]:
    """Season numbers and episode counts for the follow picker; specials are
    never followed, so season 0 is dropped."""
    return [
        {"number": season.season, "episodes": season.episode_count}
        for season in sorted(show.seasons, key=lambda s: s.season)
        if season.season >= MIN_TARGETABLE_SEASON
    ]


def show_card(show: ShowBrowseResponse) -> CardItem:
    """The show as a poster card, so the page shares the watchlist actions."""
    return CardItem(
        tmdb_id=show.tmdb_id,
        media_type=MediaType.SHOW,
        title=show.title,
        year=show.year,
        overview=show.overview,
        poster_path=show.poster_path,
        on_watchlist=show.on_watchlist,
        watchlist_kind=show.watchlist_kind,
        in_library=show.in_library,
    )


def episode_list_context(show: ShowBrowseResponse) -> dict[str, object]:
    """What the episode list partial renders: seasons with episodes, the
    latest season open, and the Find torrents fields shared by every button."""
    seasons = _seasons_with_episodes(show)
    states = show.season_states() if isinstance(show, FollowedShowView) else {}
    return {
        "show": show,
        "item": show_card(show),
        "seasons": seasons,
        "latest_season": max((season.season for season, _ in seasons), default=None),
        "following": show.watchlist_kind is WatchlistKind.FOLLOWING,
        "season_states": states,
    }


async def load_show(client: OrchestratorClient, tmdb_id: int) -> ShowBrowseResponse | None:
    """The browse view, replaced by the watchlist view when the show is
    followed so each episode carries what the follow did with it."""
    show = await client.browse_show(tmdb_id)
    if show is not None and show.watchlist_kind is WatchlistKind.FOLLOWING:
        return await client.watchlist_episodes(tmdb_id) or show
    return show


@router.get(SHOW_PATH, response_class=HTMLResponse)
async def show_page(
    request: Request, tmdb_id: int, client: OrchestratorClient = _CLIENT
) -> HTMLResponse:
    show = await load_show(client, tmdb_id)
    context: dict[str, object] = (
        episode_list_context(show) if show else {"show": None, "seasons": []}
    )
    return render(
        request,
        "show.html",
        {
            **context,
            "picker_seasons": picker_seasons(show) if show else [],
            "search_timeout": await search_timeout_seconds(client),
        },
    )
