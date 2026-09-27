"""Search -> pick a title -> (show scope) -> torrent table -> Download.
Each step is one gateway call rendered as a fragment; no state on the server:
every fragment carries what the next one needs as query or form fields."""

from typing import Any

from fastapi import APIRouter, Depends, Form, Request, status
from fastapi.responses import HTMLResponse
from medialab_contracts import MediaType

from medialab_web.auth import require_session
from medialab_web.client import OrchestratorClient
from medialab_web.constants import (
    DEFAULT_SEARCH_TIMEOUT_SECONDS,
    DOWNLOADER_SERVICE_NAME,
    HTTP_PREFIX,
    MAGNET_PREFIX,
    MIN_TARGETABLE_SEASON,
    SEARCH_PATH,
    SEARCH_TIMEOUT_SETTING,
    TMDB_RESULTS_MAX,
    WHOLE_SERIES,
)
from medialab_web.deps import get_client
from medialab_web.media import from_tmdb_media_type
from medialab_web.rendering import render
from medialab_web.schemas.discover import CardItem
from medialab_web.schemas.torrents import TorrentResult

router = APIRouter(dependencies=[Depends(require_session)])

_CLIENT = Depends(get_client)
_SEASONS_KEY = "seasons"
_SEASON_NUMBER_KEY = "season_number"
_EPISODE_COUNT_KEY = "episode_count"
_ERROR_FRAGMENT = "partials/error.html"


def _error(request: Request, message: str) -> HTMLResponse:
    return render(
        request, _ERROR_FRAGMENT, {"message": message}, status_code=status.HTTP_502_BAD_GATEWAY
    )


async def search_timeout_seconds(client: OrchestratorClient) -> int:
    """The downloader's configured search timeout, so the searching bar runs
    for the real ceiling; the default when the gateway is unreachable."""
    suite = await client.get_settings()
    if suite is None:
        return DEFAULT_SEARCH_TIMEOUT_SECONDS
    for setting in suite.services.get(DOWNLOADER_SERVICE_NAME, []):
        if setting.key == SEARCH_TIMEOUT_SETTING and isinstance(setting.value, int):
            return setting.value
    return DEFAULT_SEARCH_TIMEOUT_SECONDS


@router.get(SEARCH_PATH, response_class=HTMLResponse)
async def search_page(
    request: Request, query: str | None = None, client: OrchestratorClient = _CLIENT
) -> HTMLResponse:
    return render(
        request,
        "search.html",
        {"query": query or "", "search_timeout": await search_timeout_seconds(client)},
    )


@router.get("/partials/search/tmdb", response_class=HTMLResponse)
async def tmdb_results(
    request: Request, query: str, client: OrchestratorClient = _CLIENT
) -> HTMLResponse:
    response = await client.search_tmdb(query)
    if response is None:
        return _error(request, "TMDB search failed at the gateway.")
    results = [CardItem.from_search(r) for r in response.data if from_tmdb_media_type(r.media_type)]
    return render(
        request,
        "partials/tmdb_results.html",
        {"results": results[:TMDB_RESULTS_MAX], "query": query},
    )


@router.get("/partials/search/scope", response_class=HTMLResponse)
async def show_scope(
    request: Request,
    tmdb_id: int,
    title: str,
    year: str,
    query: str = "",
    client: OrchestratorClient = _CLIENT,
) -> HTMLResponse:
    detail = await client.search_tmdb_show(tmdb_id)
    raw: list[dict[str, Any]] = (detail.data or {}).get(_SEASONS_KEY, []) if detail else []
    # Season 0 is Specials; not targetable by an S0N tag, so it is dropped.
    seasons = [
        {
            "number": int(s.get(_SEASON_NUMBER_KEY, 0)),
            "episodes": int(s.get(_EPISODE_COUNT_KEY, 0)),
        }
        for s in raw
        if int(s.get(_SEASON_NUMBER_KEY, 0)) >= MIN_TARGETABLE_SEASON
    ]
    return render(
        request,
        "partials/scope.html",
        {"tmdb_id": tmdb_id, "title": title, "year": year, "seasons": seasons, "query": query},
    )


def _top_per_resolution(
    groups: dict[str, list[TorrentResult]], per_resolution: int
) -> list[tuple[str, list[TorrentResult]]]:
    return [
        (resolution, sorted(results, key=lambda r: r.seeders, reverse=True)[:per_resolution])
        for resolution, results in groups.items()
        if results
    ]


@router.get("/partials/search/torrents", response_class=HTMLResponse)
async def torrents(
    request: Request,
    tmdb_id: int,
    title: str,
    year: str,
    media_type: MediaType,
    season: str | None = None,
    episode: str | None = None,
    query: str = "",
    client: OrchestratorClient = _CLIENT,
) -> HTMLResponse:
    return await render_torrents(
        request, client, tmdb_id, title, year, media_type, season, episode, query
    )


async def render_torrents(
    request: Request,
    client: OrchestratorClient,
    tmdb_id: int,
    title: str,
    year: str,
    media_type: MediaType,
    season: str | None = None,
    episode: str | None = None,
    query: str = "",
    redo_job_id: str | None = None,
) -> HTMLResponse:
    """The torrent step: one gateway search rendered as the grouped table.
    With ``redo_job_id`` every pick replaces that job instead of starting a
    fresh download."""
    # TMDB's canonical title and release names can differ ("Lee Cronin's The
    # Mummy" vs "The Mummy 2026"); the typed query is searched as well.
    search_query = _torrent_query(title, year, media_type)
    typed = query.strip()
    alt_query = _torrent_query(typed, year, media_type) if typed else None
    season_number, episode_number = scope_numbers(season, episode)
    response = await client.search_torrents(
        search_query,
        media_type,
        season=season_number,
        episode=episode_number,
        alt_query=alt_query,
    )
    if response is None:
        return _error(request, "Torrent search failed at the gateway.")
    cfg = request.app.state.config
    groups = _top_per_resolution(response.data, cfg.torrent_results_per_resolution)
    return render(
        request,
        "partials/torrents.html",
        {
            "groups": groups,
            "title": title,
            "year": year,
            "tmdb_id": tmdb_id,
            "media_type": media_type,
            "season": season_number,
            "episode": episode_number,
            "scope": _scope_label(season_number, episode_number),
            "query": query,
            "redo_job_id": redo_job_id,
        },
    )


def _torrent_query(title: str, year: str, media_type: MediaType) -> str:
    # Movie release names carry the year; show release names do not. A job
    # without a resolved year sends a blank one, so the query is trimmed.
    return title if media_type is MediaType.SHOW else f"{title} {year}".strip()


def scope_numbers(season: str | None, episode: str | None) -> tuple[int | None, int | None]:
    """Form values to a scope: the whole series and a blank are no season, and
    an episode only counts with a season."""
    season_number = int(season) if season and season != WHOLE_SERIES else None
    episode_number = int(episode) if episode and season_number is not None else None
    return season_number, episode_number


def _scope_label(season: int | None, episode: int | None) -> str:
    if season is None:
        return ""
    if episode is None:
        return f"Season {season}"
    return f"S{season:02d}E{episode:02d}"


_SOURCE_URL = Form(...)
_MEDIA_TYPE = Form(...)
_TMDB_ID = Form(...)
_FILE_NAME = Form(...)
_SEASON = Form(None)
_EPISODE = Form(None)


def is_torrent_link(source_url: str) -> bool:
    return source_url.startswith(MAGNET_PREFIX) or source_url.startswith(HTTP_PREFIX)


def invalid_link(request: Request) -> HTMLResponse:
    return render(
        request,
        _ERROR_FRAGMENT,
        {"message": "Invalid torrent link."},
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
    )


@router.post("/downloads", response_class=HTMLResponse)
async def start_download(
    request: Request,
    source_url: str = _SOURCE_URL,
    media_type: MediaType = _MEDIA_TYPE,
    tmdb_id: int = _TMDB_ID,
    file_name: str = _FILE_NAME,
    season: str | None = _SEASON,
    episode: str | None = _EPISODE,
    client: OrchestratorClient = _CLIENT,
) -> HTMLResponse:
    if not is_torrent_link(source_url):
        return invalid_link(request)
    season_number, episode_number = scope_numbers(season, episode)
    response = await client.download(
        source_url, media_type, tmdb_id, file_name, season=season_number, episode=episode_number
    )
    if response is None:
        return _error(request, "Download request failed; nothing was submitted.")
    return render(
        request, "partials/download_started.html", {"job": response.job, "file_name": file_name}
    )


@router.delete("/search/cache", response_class=HTMLResponse)
async def clear_cache(request: Request, client: OrchestratorClient = _CLIENT) -> HTMLResponse:
    result = await client.clear_search_cache()
    if result is None or not result.cleared:
        return _error(request, "Could not clear the search cache.")
    return render(
        request,
        "partials/notice.html",
        {"message": "Search cache cleared; the next search runs fresh."},
    )
