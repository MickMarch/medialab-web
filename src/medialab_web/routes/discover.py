"""Discover grid, title detail, wishlist page and wishlist toggles. Each handler
is at most one gateway call per panel; every fragment carries the card's
fields forward as hx-vals, so the server keeps no state."""

from typing import Annotated

from fastapi import APIRouter, Depends, Form, Query, Request, status
from fastapi.responses import HTMLResponse
from medialab_contracts import DiscoverResponse, MediaType, WishlistItem
from pydantic import BeforeValidator

from medialab_web.auth import require_session
from medialab_web.client import OrchestratorClient
from medialab_web.constants import DISCOVER_PATH, FIRST_PAGE, WISHLIST_PATH
from medialab_web.deps import get_client
from medialab_web.rendering import render
from medialab_web.routes.search import search_timeout_seconds
from medialab_web.schemas.discover import CardItem

router = APIRouter(dependencies=[Depends(require_session)])

_CLIENT = Depends(get_client)
_ERROR_FRAGMENT = "partials/error.html"
_ITEMS_FRAGMENT = "partials/discover_items.html"
_WISHLIST_BUTTON = "partials/wishlist_button.html"

# An empty genre select ("Trending this week") submits "".
OptionalGenre = Annotated[int | None, BeforeValidator(lambda value: value or None)]
CardQuery = Annotated[CardItem, Query()]
CardForm = Annotated[CardItem, Form()]


def _error(request: Request, message: str) -> HTMLResponse:
    return render(
        request, _ERROR_FRAGMENT, {"message": message}, status_code=status.HTTP_502_BAD_GATEWAY
    )


def _items_context(
    response: DiscoverResponse | None, media_type: MediaType, genre: int | None
) -> dict[str, object]:
    return {"discover": response, "media_type": media_type, "genre": genre}


def _as_card(item: WishlistItem) -> CardItem:
    return CardItem.model_validate({**item.model_dump(exclude={"added_at"}), "on_wishlist": True})


@router.get(DISCOVER_PATH, response_class=HTMLResponse)
async def discover_page(
    request: Request,
    media_type: MediaType = MediaType.MOVIE,
    genre: OptionalGenre = None,
    client: OrchestratorClient = _CLIENT,
) -> HTMLResponse:
    genres = await client.discover_genres(media_type)
    response = await client.discover(media_type, genre=genre, page=FIRST_PAGE)
    return render(
        request,
        "discover.html",
        {
            **_items_context(response, media_type, genre),
            "genres": genres.genres if genres else [],
            "media_types": list(MediaType),
            "search_timeout": await search_timeout_seconds(client),
        },
    )


@router.get("/partials/discover", response_class=HTMLResponse)
async def discover_items(
    request: Request,
    media_type: MediaType,
    genre: OptionalGenre = None,
    page: int = FIRST_PAGE,
    client: OrchestratorClient = _CLIENT,
) -> HTMLResponse:
    # A friendly message rather than an error status so HTMX swaps it in.
    response = await client.discover(media_type, genre=genre, page=page)
    return render(request, _ITEMS_FRAGMENT, _items_context(response, media_type, genre))


@router.get("/partials/discover/detail", response_class=HTMLResponse)
async def detail(request: Request, item: CardQuery) -> HTMLResponse:
    return render(request, "partials/discover_detail.html", {"item": item})


@router.put("/partials/wishlist", response_class=HTMLResponse)
async def add_to_wishlist(
    request: Request, item: CardForm, client: OrchestratorClient = _CLIENT
) -> HTMLResponse:
    added = await client.add_to_wishlist(item.media_type, item.tmdb_id, item.wishlist_request())
    if added is None:
        return _error(request, "Could not add to the wishlist.")
    return render(
        request, _WISHLIST_BUTTON, {"item": item.model_copy(update={"on_wishlist": True})}
    )


@router.delete("/partials/wishlist", response_class=HTMLResponse)
async def remove_from_wishlist(
    request: Request, item: CardQuery, client: OrchestratorClient = _CLIENT
) -> HTMLResponse:
    if not await client.remove_from_wishlist(item.media_type, item.tmdb_id):
        return _error(request, "Could not remove from the wishlist.")
    return render(
        request, _WISHLIST_BUTTON, {"item": item.model_copy(update={"on_wishlist": False})}
    )


@router.get(WISHLIST_PATH, response_class=HTMLResponse)
async def wishlist_page(
    request: Request,
    media_type: MediaType | None = None,
    client: OrchestratorClient = _CLIENT,
) -> HTMLResponse:
    response = await client.list_wishlist(media_type)
    return render(
        request,
        "wishlist.html",
        {
            "items": [_as_card(i) for i in response.items] if response else None,
            "media_type": media_type,
            "media_types": list(MediaType),
            "search_timeout": await search_timeout_seconds(client),
        },
    )
