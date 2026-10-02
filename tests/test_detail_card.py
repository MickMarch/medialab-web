"""The one title card shared by Search and Discover: it opens in place in
the grid and hosts the download flow in its own slot, like the trailer."""

from unittest.mock import AsyncMock

from medialab_web.constants import DOWNLOAD_NOTICE_CLASS, DOWNLOAD_SLOT_CLASS, SEARCHING_CLASS
from medialab_web.schemas.tmdb import TmdbMediaDetailResponse
from medialab_web.schemas.torrents import TorrentSearchResponse
from tests.test_discover_page import _detail_params, _vals
from tests.test_search_page import _result, _tmdb, _torrent

STAGE_TARGET = 'hx-target="#stage"'
SLOT_TARGET = f'hx-target="closest .{DOWNLOAD_SLOT_CLASS}"'
NEXT_SLOT_TARGET = f'hx-target="next .{DOWNLOAD_SLOT_CLASS}"'
PREVIOUS_SEARCHING = f'hx-indicator="previous .{SEARCHING_CLASS}"'
NEXT_SEARCHING = f'hx-indicator="next .{SEARCHING_CLASS}"'
IN_PLACE = 'hx-target="closest .poster-card" hx-swap="afterend"'
MOVIE_SCOPE = {"tmdb_id": 1, "title": "Dune", "year": "2021", "media_type": "movie"}
SHOW_SCOPE = {"tmdb_id": 2, "title": "Lost", "year": "2004", "media_type": "show", "season": 1}


def _empty_torrents() -> AsyncMock:
    return AsyncMock(return_value=TorrentSearchResponse(status="success", message="", data={}))


# --- search results are posters that open the shared card ---


async def test_search_results_are_posters_opening_the_detail_card(logged_in, mock_client):
    mock_client.search_tmdb = AsyncMock(
        return_value=_tmdb(_result(), _result(tmdb_id=2, title="Lost", media_type="tv"))
    )
    text = (await logged_in.get("/partials/search/tmdb", params={"query": "dune"})).text
    assert text.count('hx-get="/partials/discover/detail"') == 2
    assert text.count(IN_PLACE) == 2
    assert "Find torrents" not in text and "Choose season" not in text
    assert "/partials/search/scope" not in text and "/partials/search/torrents" not in text
    assert '<ol class="steps">' not in text
    vals = _vals(text, 'hx-get="/partials/discover/detail"')
    assert vals["query"] == "dune" and vals["tmdb_id"] == 1


async def test_search_page_has_no_step_strip_or_page_level_searching_panel(logged_in):
    text = (await logged_in.get("/search")).text
    assert "Step 1 of 4" not in text
    assert 'id="searching"' not in text
    assert 'id="stage"' in text


async def test_discover_page_has_no_fixed_detail_or_stage(logged_in, mock_client):
    from tests.test_discover_page import _item, _page

    mock_client.discover = AsyncMock(return_value=_page(_item()))
    mock_client.discover_genres = AsyncMock(return_value=None)
    text = (await logged_in.get("/discover")).text
    assert 'id="detail"' not in text and 'id="stage"' not in text
    assert 'id="searching"' not in text
    assert IN_PLACE in text


# --- the detail card ---


async def test_detail_card_closes_other_open_cards_and_carries_the_slots(logged_in):
    text = (await logged_in.get("/partials/discover/detail", params=_detail_params())).text
    assert 'hx-on::load="' in text and "querySelectorAll('.detail')" in text
    assert f'class="{DOWNLOAD_SLOT_CLASS}"' in text
    assert f'class="htmx-indicator card {SEARCHING_CLASS}"' in text
    assert 'id="searching"' not in text


async def test_detail_download_button_targets_the_slot_without_scrolling(logged_in):
    movie = (await logged_in.get("/partials/discover/detail", params=_detail_params())).text
    assert NEXT_SLOT_TARGET in movie and "show:" not in movie
    assert NEXT_SEARCHING in movie
    show = (
        await logged_in.get(
            "/partials/discover/detail",
            params=_detail_params(media_type="show", tmdb_id=1396, title="Breaking Bad"),
        )
    ).text
    assert NEXT_SLOT_TARGET in show and "show:" not in show


async def test_detail_passes_the_typed_query_to_the_download_button(logged_in):
    params = {**_detail_params(), "query": "the mummy"}
    text = (await logged_in.get("/partials/discover/detail", params=params)).text
    assert _vals(text, 'hx-get="/partials/search/torrents"')["query"] == "the mummy"
    text = (await logged_in.get("/partials/discover/detail", params=_detail_params())).text
    assert _vals(text, 'hx-get="/partials/search/torrents"')["query"] == "Dune"


async def test_detail_card_carries_the_downloader_timeout(logged_in, mock_client):
    from medialab_contracts import SettingView, SuiteSettingsResponse

    mock_client.get_settings = AsyncMock(
        return_value=SuiteSettingsResponse(
            status="success",
            services={
                "torrent-downloader": [
                    SettingView(
                        key="search_timeout_seconds",
                        value=42,
                        default=15,
                        source="override",
                        type="int",
                        description="d",
                        applies="next search",
                        min=5,
                        max=120,
                    )
                ]
            },
        )
    )
    text = (await logged_in.get("/partials/discover/detail", params=_detail_params())).text
    assert "--search-seconds: 42s" in text and "Up to 42 s" in text


# --- the scope and torrent partials live wherever the slot is ---


async def test_scope_partial_targets_the_slot(logged_in, mock_client):
    mock_client.search_tmdb_show = AsyncMock(
        return_value=TmdbMediaDetailResponse(status="success", message="", data={"seasons": []})
    )
    text = (
        await logged_in.get(
            "/partials/search/scope", params={"tmdb_id": 2, "title": "Lost", "year": "2004"}
        )
    ).text
    assert "#stage" not in text
    assert SLOT_TARGET in text and PREVIOUS_SEARCHING in text
    assert "Back to titles" not in text and '<ol class="steps">' not in text


async def test_torrents_partial_targets_the_slot(logged_in, mock_client):
    mock_client.search_torrents = AsyncMock(
        return_value=TorrentSearchResponse(
            status="success", message="", data={"1080p": [_torrent()]}
        )
    )
    text = (await logged_in.get("/partials/search/torrents", params=SHOW_SCOPE)).text
    assert "#stage" not in text and "#download-notice" not in text
    assert "Change scope" in text and SLOT_TARGET in text and PREVIOUS_SEARCHING in text
    assert f'class="{DOWNLOAD_NOTICE_CLASS}"' in text
    assert f'hx-target="previous .{DOWNLOAD_NOTICE_CLASS}" hx-swap="innerHTML"' in text
    assert "show:" not in text
    assert '<ol class="steps">' not in text
    movie = (await logged_in.get("/partials/search/torrents", params=MOVIE_SCOPE)).text
    assert "Back to titles" not in movie and "Change scope" not in movie


async def test_redo_torrents_replace_within_the_slot(logged_in, mock_client):
    mock_client.search_torrents = AsyncMock(
        return_value=TorrentSearchResponse(
            status="success", message="", data={"1080p": [_torrent()]}
        )
    )
    text = (await logged_in.get("/partials/jobs/a/redo", params=MOVIE_SCOPE)).text
    assert "#stage" not in text and "getElementById('stage')" not in text
    assert f'hx-post="/partials/jobs/a/redo" {SLOT_TARGET}' in text
    assert f"this.closest('.{DOWNLOAD_SLOT_CLASS}').replaceChildren()" in text


async def test_pages_that_keep_a_stage_mark_it_as_the_slot(logged_in, mock_client):
    from tests.test_show_page import SHOW_PATH, _show

    mock_client.browse_show = AsyncMock(return_value=_show())
    mock_client.search_torrents = _empty_torrents()
    mock_client.list_watchlist = AsyncMock(return_value=None)
    for path in ("/", SHOW_PATH, "/watchlist"):
        text = (await logged_in.get(path)).text
        assert f'id="stage" class="{DOWNLOAD_SLOT_CLASS}"' in text, path
