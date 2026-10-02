"""Discover grid and title detail. Each handler is at most one gateway call
per panel; every fragment carries the card's fields forward as hx-vals, so
the server keeps no state."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import HTMLResponse
from medialab_contracts import DiscoverResponse, MediaType
from pydantic import BeforeValidator

from medialab_web.auth import require_session
from medialab_web.client import OrchestratorClient
from medialab_web.constants import DISCOVER_PATH, FIRST_PAGE
from medialab_web.deps import get_client
from medialab_web.rendering import render
from medialab_web.routes.search import search_timeout_seconds
from medialab_web.schemas.discover import CardItem

router = APIRouter(dependencies=[Depends(require_session)])

_CLIENT = Depends(get_client)
_ITEMS_FRAGMENT = "partials/discover_items.html"

# An empty genre select ("Trending this week") submits "".
OptionalGenre = Annotated[int | None, BeforeValidator(lambda value: value or None)]
CardQuery = Annotated[CardItem, Query()]


class DetailRequest(CardItem):
    """A card's fields plus the text typed on the Search page, if any. The
    query rides along to the torrent search as the alternate query; Discover
    sends none and the title stands in."""

    query: str = ""

    def card(self) -> CardItem:
        return CardItem.model_validate(self.model_dump(exclude={"query"}))


DetailQuery = Annotated[DetailRequest, Query()]


def _items_context(
    response: DiscoverResponse | None, media_type: MediaType, genre: int | None
) -> dict[str, object]:
    return {"discover": response, "media_type": media_type, "genre": genre}


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
async def detail(
    request: Request, detail: DetailQuery, client: OrchestratorClient = _CLIENT
) -> HTMLResponse:
    return render(
        request,
        "partials/discover_detail.html",
        {
            "item": detail.card(),
            "query": detail.query,
            "search_timeout": await search_timeout_seconds(client),
        },
    )
