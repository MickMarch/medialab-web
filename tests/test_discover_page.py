import json
from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest
from medialab_contracts import (
    DiscoverItem,
    DiscoverResponse,
    Genre,
    GenresResponse,
    MediaType,
    PosterSize,
    WishlistAddRequest,
    WishlistItem,
    WishlistResponse,
    poster_url,
)

from medialab_web.constants import TMDB_ATTRIBUTION

NOW = datetime(2026, 9, 27, tzinfo=UTC)
DUNE_POSTER = "/dune.jpg"


def _item(**kw) -> DiscoverItem:
    base = {
        "tmdb_id": 438631,
        "media_type": MediaType.MOVIE,
        "title": "Dune",
        "year": "2021",
        "overview": "Desert planet.",
        "vote_average": 7.9,
        "poster_path": DUNE_POSTER,
    }
    return DiscoverItem(**{**base, **kw})


def _page(*items: DiscoverItem, page: int = 1, total_pages: int = 1) -> DiscoverResponse:
    return DiscoverResponse(items=list(items), page=page, total_pages=total_pages, cached_at=NOW)


def _wish(**kw) -> WishlistItem:
    base = {
        "tmdb_id": 1396,
        "media_type": MediaType.SHOW,
        "title": "Breaking Bad",
        "year": "2008",
        "poster_path": "/bb.jpg",
        "overview": "Chemistry.",
        "added_at": NOW,
    }
    return WishlistItem(**{**base, **kw})


def _vals(html: str, marker: str) -> dict:
    """The hx-vals JSON of the element whose tag contains ``marker``."""
    start = html.index(marker)
    tag = html[html.rfind("<", 0, start) : html.index(">", start)]
    raw = tag.split("hx-vals='", 1)[1].split("'", 1)[0]
    return json.loads(raw)


@pytest.fixture
def discover_client(mock_client):
    mock_client.discover = AsyncMock(
        return_value=_page(
            _item(),
            _item(tmdb_id=2, title="Posterless", poster_path=None),
            page=1,
            total_pages=3,
        )
    )
    mock_client.discover_genres = AsyncMock(
        return_value=GenresResponse(
            genres=[Genre(id=28, name="Action"), Genre(id=35, name="Comedy")]
        )
    )
    return mock_client


# --- discover page ---


async def test_discover_renders_posters_and_text_card(logged_in, discover_client):
    text = (await logged_in.get("/discover")).text
    assert f'src="{poster_url(DUNE_POSTER, PosterSize.GRID)}"' in text
    assert 'loading="lazy"' in text
    assert text.count('poster-card no-poster"') == 1
    assert "Posterless" in text
    assert text.count("<img") == 1
    discover_client.discover.assert_awaited_once_with(MediaType.MOVIE, genre=None, page=1)


async def test_discover_badge_only_when_in_library(logged_in, discover_client):
    discover_client.discover = AsyncMock(return_value=_page(_item()))
    assert "In Jellyfin" not in (await logged_in.get("/discover")).text
    discover_client.discover = AsyncMock(return_value=_page(_item(in_library=True)))
    assert "In Jellyfin" in (await logged_in.get("/discover")).text


async def test_discover_genre_select_lists_genres(logged_in, discover_client):
    text = (await logged_in.get("/discover", params={"media_type": "show"})).text
    assert '<option value="28"' in text and "Action" in text
    assert '<option value="35"' in text and "Comedy" in text
    discover_client.discover_genres.assert_awaited_once_with(MediaType.SHOW)


async def test_discover_more_link_only_before_last_page(logged_in, discover_client):
    text = (await logged_in.get("/discover")).text
    assert "More" in text and '"page": 2' in text
    discover_client.discover = AsyncMock(return_value=_page(_item(), page=3, total_pages=3))
    text = (
        await logged_in.get(
            "/partials/discover", params={"media_type": "movie", "genre": "28", "page": 3}
        )
    ).text
    assert "Dune" in text and "More" not in text
    discover_client.discover.assert_awaited_once_with(MediaType.MOVIE, genre=28, page=3)


async def test_discover_tmdb_unavailable_shows_friendly_message(logged_in, discover_client):
    discover_client.discover = AsyncMock(return_value=None)
    discover_client.discover_genres = AsyncMock(return_value=None)
    response = await logged_in.get("/discover")
    assert response.status_code == 200
    assert "TMDB is not reachable" in response.text


async def test_discover_footer_has_tmdb_attribution(logged_in, discover_client):
    assert TMDB_ATTRIBUTION in (await logged_in.get("/discover")).text


async def test_nav_has_discover_and_wishlist_on_every_page(logged_in, discover_client):
    discover_client.list_wishlist = AsyncMock(return_value=WishlistResponse(items=[]))
    for path in ("/", "/search", "/settings", "/discover", "/wishlist"):
        text = (await logged_in.get(path)).text
        assert 'href="/discover"' in text, path
        assert 'href="/wishlist"' in text, path


# --- detail card and actions ---


def _detail_params(**kw) -> dict:
    return {**_item(**kw).model_dump(mode="json"), **kw}


async def test_detail_movie_download_targets_torrents(logged_in):
    text = (await logged_in.get("/partials/discover/detail", params=_detail_params())).text
    assert "Desert planet." in text and "7.9" in text
    assert 'hx-get="/partials/search/torrents"' in text
    vals = _vals(text, 'hx-get="/partials/search/torrents"')
    assert vals["tmdb_id"] == 438631 and vals["media_type"] == "movie"
    assert "/partials/search/scope" not in text


async def test_detail_show_download_targets_scope(logged_in):
    params = _detail_params(media_type="show", tmdb_id=1396, title="Breaking Bad")
    text = (await logged_in.get("/partials/discover/detail", params=params)).text
    assert 'hx-get="/partials/search/scope"' in text
    assert _vals(text, 'hx-get="/partials/search/scope"')["tmdb_id"] == 1396
    assert "/partials/search/torrents" not in text


async def test_detail_wishlist_button_reflects_state(logged_in):
    text = (await logged_in.get("/partials/discover/detail", params=_detail_params())).text
    assert 'hx-put="/partials/wishlist"' in text and "Remove from wishlist" not in text
    params = _detail_params(on_wishlist=True)
    text = (await logged_in.get("/partials/discover/detail", params=params)).text
    assert 'hx-delete="/partials/wishlist"' in text and "Remove from wishlist" in text


async def test_wishlist_button_swaps_to_remove_and_back(logged_in, mock_client):
    mock_client.add_to_wishlist = AsyncMock(return_value=_wish())
    mock_client.remove_from_wishlist = AsyncMock(return_value=True)
    form = _item().model_dump(mode="json")
    text = (await logged_in.put("/partials/wishlist", data=form)).text
    assert "Remove from wishlist" in text and 'hx-delete="/partials/wishlist"' in text
    mock_client.add_to_wishlist.assert_awaited_once_with(
        MediaType.MOVIE,
        438631,
        WishlistAddRequest(
            title="Dune", year="2021", poster_path=DUNE_POSTER, overview="Desert planet."
        ),
    )
    text = (await logged_in.delete("/partials/wishlist", params=form)).text
    assert 'hx-put="/partials/wishlist"' in text and "Remove from wishlist" not in text
    mock_client.remove_from_wishlist.assert_awaited_once_with(MediaType.MOVIE, 438631)


async def test_wishlist_add_failure_renders_error(logged_in, mock_client):
    mock_client.add_to_wishlist = AsyncMock(return_value=None)
    response = await logged_in.put("/partials/wishlist", data=_item().model_dump(mode="json"))
    assert response.status_code == 502
    assert "wishlist" in response.text.lower()


# --- wishlist page ---


async def test_wishlist_page_lists_items_with_actions(logged_in, mock_client):
    mock_client.list_wishlist = AsyncMock(
        return_value=WishlistResponse(
            items=[
                _wish(in_library=True),
                _wish(tmdb_id=5, media_type=MediaType.MOVIE, title="Heat"),
            ]
        )
    )
    text = (await logged_in.get("/wishlist")).text
    assert "Breaking Bad" in text and "Heat" in text
    assert "In Jellyfin" in text
    assert 'hx-get="/partials/search/scope"' in text
    assert 'hx-get="/partials/search/torrents"' in text
    assert text.count('hx-delete="/partials/wishlist"') == 2
    assert TMDB_ATTRIBUTION in text
    mock_client.list_wishlist.assert_awaited_once_with(None)


async def test_wishlist_page_empty_and_unreachable(logged_in, mock_client):
    mock_client.list_wishlist = AsyncMock(return_value=WishlistResponse(items=[]))
    assert "wishlist is empty" in (await logged_in.get("/wishlist")).text
    mock_client.list_wishlist = AsyncMock(return_value=None)
    assert "Could not load the wishlist" in (await logged_in.get("/wishlist")).text


async def test_wishlist_page_remove_calls_delete(logged_in, mock_client):
    mock_client.remove_from_wishlist = AsyncMock(return_value=True)
    params = _item(media_type=MediaType.SHOW, tmdb_id=1396).model_dump(mode="json")
    response = await logged_in.delete("/partials/wishlist", params=params)
    assert response.status_code == 200
    mock_client.remove_from_wishlist.assert_awaited_once_with(MediaType.SHOW, 1396)


async def test_wishlist_remove_failure_renders_error(logged_in, mock_client):
    mock_client.remove_from_wishlist = AsyncMock(return_value=False)
    response = await logged_in.delete("/partials/wishlist", params=_item().model_dump(mode="json"))
    assert response.status_code == 502
