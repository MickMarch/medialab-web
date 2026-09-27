"""Trailers for a title or a season: one gateway call on the button press, then
a player, a list of videos to pick from, or a notice. Nothing is fetched when
the button itself renders."""

from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import HTMLResponse
from medialab_contracts import MediaType

from medialab_web.auth import require_session
from medialab_web.client import OrchestratorClient
from medialab_web.constants import (
    NO_TRAILER_NOTICE,
    TRAILER_PLAY_PATH,
    TRAILERS_PARTIAL_PATH,
    TRAILERS_UNAVAILABLE_MESSAGE,
)
from medialab_web.deps import get_client
from medialab_web.rendering import render

router = APIRouter(dependencies=[Depends(require_session)])

_CLIENT = Depends(get_client)
_ERROR_FRAGMENT = "partials/error.html"
_NOTICE_FRAGMENT = "partials/trailer_notice.html"
_LIST_FRAGMENT = "partials/trailer_list.html"
_PLAYER_FRAGMENT = "partials/trailer_player.html"
_SINGLE_VIDEO = 1


def _player(request: Request, key: str, name: str) -> HTMLResponse:
    return render(request, _PLAYER_FRAGMENT, {"key": key, "name": name})


@router.get(TRAILERS_PARTIAL_PATH, response_class=HTMLResponse)
async def trailers(
    request: Request,
    media_type: MediaType,
    tmdb_id: int,
    season: int | None = None,
    client: OrchestratorClient = _CLIENT,
) -> HTMLResponse:
    response = await client.videos(media_type, tmdb_id, season=season)
    if response is None:
        return render(
            request,
            _ERROR_FRAGMENT,
            {"message": TRAILERS_UNAVAILABLE_MESSAGE},
            status_code=status.HTTP_502_BAD_GATEWAY,
        )
    videos = response.videos
    if not videos:
        return render(request, _NOTICE_FRAGMENT, {"notice": NO_TRAILER_NOTICE})
    if len(videos) == _SINGLE_VIDEO:
        only = videos[0]
        return _player(request, only.key, only.name)
    return render(request, _LIST_FRAGMENT, {"videos": videos})


@router.get(TRAILER_PLAY_PATH, response_class=HTMLResponse)
async def play(request: Request, key: str, name: str = "") -> HTMLResponse:
    return _player(request, key, name)
