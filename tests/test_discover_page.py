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
    WatchlistItem,
    WatchlistKind,
    WatchlistResponse,
    poster_url,
)

from medialab_web.constants import (
    FOLLOW_LABEL,
    FOLLOWING_LABEL,
    SAVE_LABEL,
    SAVED_LABEL,
    TMDB_ATTRIBUTION,
    UNSAVE_LABEL,
)

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


def _saved(**kw) -> WatchlistItem:
    base = {
        "tmdb_id": 1396,
        "media_type": MediaType.SHOW,
        "title": "Breaking Bad",
        "year": "2008",
        "poster_path": "/bb.jpg",
        "overview": "Chemistry.",
        "added_at": NOW,
    }
    return WatchlistItem(**{**base, **kw})


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
    assert text.count('hx-target="closest .poster-card" hx-swap="afterend"') == 2
    discover_client.discover.assert_awaited_once_with(MediaType.MOVIE, genre=None, page=1)


async def test_discover_badge_only_when_in_library(logged_in, discover_client):
    discover_client.discover = AsyncMock(return_value=_page(_item()))
    assert "In Jellyfin" not in (await logged_in.get("/discover")).text
    discover_client.discover = AsyncMock(return_value=_page(_item(in_library=True)))
    assert "In Jellyfin" in (await logged_in.get("/discover")).text


async def test_discover_badge_reads_saved_or_following(logged_in, discover_client):
    discover_client.discover = AsyncMock(return_value=_page(_item()))
    text = (await logged_in.get("/discover")).text
    assert SAVED_LABEL not in text and FOLLOWING_LABEL not in text
    discover_client.discover = AsyncMock(
        return_value=_page(_item(on_watchlist=True, watchlist_kind=WatchlistKind.SAVED))
    )
    text = (await logged_in.get("/discover")).text
    assert 'class="badge saved"' in text and SAVED_LABEL in text
    discover_client.discover = AsyncMock(
        return_value=_page(
            _item(
                media_type=MediaType.SHOW,
                on_watchlist=True,
                watchlist_kind=WatchlistKind.FOLLOWING,
            )
        )
    )
    text = (await logged_in.get("/discover")).text
    assert 'class="badge following"' in text and FOLLOWING_LABEL in text


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


async def test_nav_has_discover_and_watchlist_on_every_page(logged_in, discover_client):
    discover_client.list_watchlist = AsyncMock(return_value=WatchlistResponse(items=[]))
    for path in ("/", "/search", "/settings", "/discover", "/watchlist"):
        text = (await logged_in.get(path)).text
        assert 'href="/discover"' in text, path
        assert 'href="/watchlist"' in text and ">Watchlist</a>" in text, path
        assert "wishlist" not in text.lower(), path


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


async def test_detail_save_button_reflects_state(logged_in):
    text = (await logged_in.get("/partials/discover/detail", params=_detail_params())).text
    assert 'hx-put="/partials/watchlist"' in text and f">{SAVE_LABEL}<" in text
    assert UNSAVE_LABEL not in text
    params = _detail_params(on_watchlist=True, watchlist_kind="saved")
    text = (await logged_in.get("/partials/discover/detail", params=params)).text
    assert 'hx-delete="/partials/watchlist"' in text and f">{UNSAVE_LABEL}<" in text
    assert f">{SAVE_LABEL}<" not in text


async def test_detail_follow_button_on_shows_only(logged_in):
    text = (await logged_in.get("/partials/discover/detail", params=_detail_params())).text
    assert f">{FOLLOW_LABEL}<" not in text
    params = _detail_params(media_type="show", tmdb_id=1396, title="Breaking Bad")
    text = (await logged_in.get("/partials/discover/detail", params=params)).text
    assert 'hx-get="/partials/watchlist/follow"' in text and f">{FOLLOW_LABEL}<" in text
    vals = _vals(text, 'hx-get="/partials/watchlist/follow"')
    assert vals["tmdb_id"] == 1396 and vals["media_type"] == "show" and vals["view"] == "inline"


async def test_detail_following_show_offers_unfollow(logged_in):
    params = _detail_params(
        media_type="show", tmdb_id=1396, on_watchlist=True, watchlist_kind="following"
    )
    text = (await logged_in.get("/partials/discover/detail", params=params)).text
    assert 'hx-delete="/partials/watchlist/follow"' in text and "Unfollow" in text
    assert FOLLOWING_LABEL in text
    assert 'hx-get="/partials/watchlist/follow"' not in text
    assert UNSAVE_LABEL not in text
