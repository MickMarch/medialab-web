"""The show page: one gateway call rendering seasons and episodes, each with a
Find torrents button that enters the torrent step with its scope preset."""

from collections import defaultdict

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from medialab_contracts import EpisodeState, Season, ShowBrowseResponse

from medialab_web.auth import require_session
from medialab_web.client import OrchestratorClient
from medialab_web.constants import SHOW_PATH
from medialab_web.deps import get_client
from medialab_web.rendering import render
from medialab_web.routes.search import search_timeout_seconds

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


@router.get(SHOW_PATH, response_class=HTMLResponse)
async def show_page(
    request: Request, tmdb_id: int, client: OrchestratorClient = _CLIENT
) -> HTMLResponse:
    show = await client.browse_show(tmdb_id)
    seasons = _seasons_with_episodes(show) if show else []
    # The latest season is the one being followed; it opens, the rest collapse.
    latest = max((season.season for season, _ in seasons), default=None)
    return render(
        request,
        "show.html",
        {
            "show": show,
            "seasons": seasons,
            "latest_season": latest,
            "search_timeout": await search_timeout_seconds(client),
        },
    )
