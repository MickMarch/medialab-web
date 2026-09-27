"""The watchlist: Saved and Following tabs, save and unsave toggles, the
follow picker, the follow controls of a Following card, and the episode
view with Retry. Each action is one gateway call (two for a follow of a
title not yet saved) rendered as a fragment."""

from typing import Annotated

from fastapi import APIRouter, Depends, Form, Query, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from medialab_contracts import WatchlistItem, WatchlistKind
from pydantic import ValidationError

from medialab_web.auth import require_session
from medialab_web.client import OrchestratorClient
from medialab_web.constants import (
    FOLLOW_BUTTON_PARTIAL_PATH,
    FOLLOW_PARTIAL_PATH,
    LEGACY_WISHLIST_PATH,
    NOTHING_SUBMITTED_NOTICE,
    WATCHLIST_PARTIAL_PATH,
    WATCHLIST_PATH,
    WATCHLIST_SHOW_PARTIAL_PATH,
)
from medialab_web.deps import get_client
from medialab_web.rendering import render
from medialab_web.routes.search import search_timeout_seconds
from medialab_web.routes.shows import episode_list_context, picker_seasons
from medialab_web.schemas.discover import CardItem
from medialab_web.schemas.watchlist import FollowCard, FollowForm, FollowView

router = APIRouter(dependencies=[Depends(require_session)])

_CLIENT = Depends(get_client)
_ERROR_FRAGMENT = "partials/error.html"
_NOTICE_FRAGMENT = "partials/notice.html"
_ACTIONS_FRAGMENT = "partials/watchlist_actions.html"
_PICKER_FRAGMENT = "partials/follow_picker.html"
_FOLLOW_CARD_FRAGMENT = "partials/follow_card.html"
_EPISODE_LIST_FRAGMENT = "partials/episode_list.html"
_HX_REDIRECT_HEADER = "HX-Redirect"
_FOLLOW_ROUTE = WATCHLIST_SHOW_PARTIAL_PATH + "/follow"
_EPISODES_ROUTE = WATCHLIST_SHOW_PARTIAL_PATH + "/episodes"
_SUBMISSION_ROUTE = _EPISODES_ROUTE + "/{season}/{episode}/submission"

CardQuery = Annotated[CardItem, Query()]
CardForm = Annotated[CardItem, Form()]
FollowCardQuery = Annotated[FollowCard, Query()]
FollowFormBody = Annotated[FollowForm, Form()]


def _error(
    request: Request, message: str, status_code: int = status.HTTP_502_BAD_GATEWAY
) -> HTMLResponse:
    return render(request, _ERROR_FRAGMENT, {"message": message}, status_code=status_code)


def _actions(
    request: Request, item: CardItem, view: FollowView = FollowView.INLINE
) -> HTMLResponse:
    return render(request, _ACTIONS_FRAGMENT, {"item": item, "view": view.value})


def _follow_card(request: Request, item: WatchlistItem) -> HTMLResponse:
    return render(request, _FOLLOW_CARD_FRAGMENT, {"item": item})


def following_tab_url() -> str:
    return f"{WATCHLIST_PATH}?kind={WatchlistKind.FOLLOWING.value}"


# --- page ---


@router.get(LEGACY_WISHLIST_PATH, include_in_schema=False)
async def wishlist_redirect() -> RedirectResponse:
    return RedirectResponse(WATCHLIST_PATH, status_code=status.HTTP_308_PERMANENT_REDIRECT)


@router.get(WATCHLIST_PATH, response_class=HTMLResponse)
async def watchlist_page(
    request: Request,
    kind: WatchlistKind = WatchlistKind.SAVED,
    client: OrchestratorClient = _CLIENT,
) -> HTMLResponse:
    response = await client.list_watchlist(kind=kind)
    return render(
        request,
        "watchlist.html",
        {
            "kind": kind,
            "items": response.items if response else None,
            "cards": [CardItem.from_watchlist(i) for i in response.items] if response else None,
            "search_timeout": await search_timeout_seconds(client),
        },
    )


# --- save and unsave ---


@router.put(WATCHLIST_PARTIAL_PATH, response_class=HTMLResponse)
async def save(
    request: Request, item: CardForm, client: OrchestratorClient = _CLIENT
) -> HTMLResponse:
    saved = await client.add_to_watchlist(item.media_type, item.tmdb_id, item.watchlist_request())
    if saved is None:
        return _error(request, "Could not save to the watchlist.")
    return _actions(request, item.with_kind(saved.kind))


@router.delete(WATCHLIST_PARTIAL_PATH, response_class=HTMLResponse)
async def unsave(
    request: Request, item: CardQuery, client: OrchestratorClient = _CLIENT
) -> HTMLResponse:
    if not await client.remove_from_watchlist(item.media_type, item.tmdb_id):
        return _error(request, "Could not remove from the watchlist.")
    return _actions(request, item.with_kind(None))


# --- follow ---


@router.get(FOLLOW_PARTIAL_PATH, response_class=HTMLResponse)
async def follow_picker(
    request: Request, item: FollowCardQuery, client: OrchestratorClient = _CLIENT
) -> HTMLResponse:
    show = await client.browse_show(item.tmdb_id)
    if show is None:
        return _error(request, "Could not load the seasons. TMDB or the gateway is not reachable.")
    return render(
        request,
        _PICKER_FRAGMENT,
        {"item": item.card, "seasons": picker_seasons(show), "view": item.view.value},
    )


@router.get(FOLLOW_BUTTON_PARTIAL_PATH, response_class=HTMLResponse)
async def follow_cancel(request: Request, item: FollowCardQuery) -> HTMLResponse:
    return _actions(request, item.card, item.view)


@router.put(FOLLOW_PARTIAL_PATH, response_class=HTMLResponse)
async def follow(
    request: Request, form: FollowFormBody, client: OrchestratorClient = _CLIENT
) -> Response:
    try:
        body = form.follow_request()
    except ValidationError:
        return _error(
            request, "Pick a season and an episode.", status.HTTP_422_UNPROCESSABLE_CONTENT
        )
    item = form.card
    if not item.on_watchlist:
        saved = await client.add_to_watchlist(
            item.media_type, item.tmdb_id, item.watchlist_request()
        )
        if saved is None:
            return _error(request, "Could not save to the watchlist.")
    followed = await client.follow_show(item.tmdb_id, body)
    if followed is None:
        return _error(request, "Could not follow this show.")
    if form.view is FollowView.PAGE:
        return Response(
            status_code=status.HTTP_200_OK, headers={_HX_REDIRECT_HEADER: following_tab_url()}
        )
    return _actions(request, item.with_kind(followed.kind))


@router.delete(FOLLOW_PARTIAL_PATH, response_class=HTMLResponse)
async def unfollow(
    request: Request, item: CardQuery, client: OrchestratorClient = _CLIENT
) -> HTMLResponse:
    if not await client.unfollow_show(item.tmdb_id):
        return _error(request, "Could not unfollow this show.")
    return _actions(request, item.with_kind(WatchlistKind.SAVED))


@router.post(_FOLLOW_ROUTE + "/pause", response_class=HTMLResponse)
async def pause(
    request: Request, tmdb_id: int, client: OrchestratorClient = _CLIENT
) -> HTMLResponse:
    item = await client.pause_follow(tmdb_id)
    if item is None:
        return _error(request, "Could not pause this follow.")
    return _follow_card(request, item)


@router.post(_FOLLOW_ROUTE + "/resume", response_class=HTMLResponse)
async def resume(
    request: Request, tmdb_id: int, client: OrchestratorClient = _CLIENT
) -> HTMLResponse:
    item = await client.resume_follow(tmdb_id)
    if item is None:
        return _error(request, "Could not resume this follow.")
    return _follow_card(request, item)


@router.post(_FOLLOW_ROUTE + "/check", response_class=HTMLResponse)
async def check(
    request: Request, tmdb_id: int, client: OrchestratorClient = _CLIENT
) -> HTMLResponse:
    result = await client.check_follow(tmdb_id)
    if result is None:
        return _error(request, "The check failed at the gateway.")
    message = (
        f"Submitted {', '.join(result.submitted)}."
        if result.submitted
        else NOTHING_SUBMITTED_NOTICE
    )
    return render(request, _NOTICE_FRAGMENT, {"message": message})


# --- episodes ---


async def _episode_list(request: Request, client: OrchestratorClient, tmdb_id: int) -> HTMLResponse:
    show = await client.watchlist_episodes(tmdb_id)
    if show is None:
        return _error(request, "Could not load the episodes. TMDB or the gateway is not reachable.")
    return render(request, _EPISODE_LIST_FRAGMENT, episode_list_context(show))


@router.get(_EPISODES_ROUTE, response_class=HTMLResponse)
async def episodes(
    request: Request, tmdb_id: int, client: OrchestratorClient = _CLIENT
) -> HTMLResponse:
    return await _episode_list(request, client, tmdb_id)


@router.delete(_SUBMISSION_ROUTE, response_class=HTMLResponse)
async def retry(
    request: Request,
    tmdb_id: int,
    season: int,
    episode: int,
    client: OrchestratorClient = _CLIENT,
) -> HTMLResponse:
    if not await client.retry_episode(tmdb_id, season, episode):
        return _error(request, "Could not clear the submission.")
    return await _episode_list(request, client, tmdb_id)
