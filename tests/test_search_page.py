from unittest.mock import AsyncMock

from medialab_contracts import MediaType, PosterSize, poster_url

from medialab_web.constants import (
    FOLLOW_LABEL,
    FOLLOWING_LABEL,
    IN_LIBRARY_LABEL,
    REDO_NOTICE,
    SAVE_LABEL,
    SAVED_LABEL,
)
from medialab_web.schemas.downloads import DownloadResponse
from medialab_web.schemas.errors import GatewayError
from medialab_web.schemas.tmdb import TmdbMediaDetailResponse, TmdbSearchResponse, TmdbSearchResult
from medialab_web.schemas.torrents import TorrentResult, TorrentSearchResponse
from tests.conftest import make_job

_DETAIL = {"tmdb_id": 1, "media_type": "movie", "title": "Dune", "year": "2021"}


def _tmdb(*results):
    return TmdbSearchResponse(status="success", message="", data=list(results))


def _result(**kw):
    base = {
        "tmdb_id": 1,
        "title": "Dune",
        "year": "2021",
        "media_type": "movie",
        "overview": "Sand.",
        "vote_average": 8.1,
        "poster_path": None,
    }
    return TmdbSearchResult(**{**base, **kw})


def _torrent(name="Dune.2021.1080p-GRP", seeders=10, langs=None, multi=False):
    return TorrentResult(
        fileName=name,
        fileUrl="magnet:?xt=urn:btih:abc",
        nbSeeders=seeders,
        nbLeechers=1,
        fileSize=2 * 1024**3,
        languages=langs or [],
        multiAudio=multi,
    )


async def test_search_page_renders(logged_in):
    response = await logged_in.get("/search")
    assert response.status_code == 200
    assert 'hx-get="/partials/search/tmdb"' in response.text


async def test_tmdb_results_are_cards_for_movies_and_shows_only(logged_in, mock_client):
    mock_client.search_tmdb = AsyncMock(
        return_value=_tmdb(
            _result(),
            _result(tmdb_id=2, title="Lost", media_type="tv"),
            _result(tmdb_id=3, title="Someone", media_type="person"),
        )
    )
    text = (await logged_in.get("/partials/search/tmdb", params={"query": "x"})).text
    assert text.count('hx-get="/partials/discover/detail"') == 2
    assert "Someone" not in text
    mock_client.search_tmdb.assert_awaited_once_with("x")


async def test_tmdb_results_badge_from_watchlist_kind_and_library(logged_in, mock_client):
    mock_client.search_tmdb = AsyncMock(return_value=_tmdb(_result()))
    text = (await logged_in.get("/partials/search/tmdb", params={"query": "x"})).text
    assert 'class="badge saved"' not in text and 'class="badge following"' not in text
    assert IN_LIBRARY_LABEL not in text
    mock_client.search_tmdb = AsyncMock(
        return_value=_tmdb(
            _result(on_watchlist=True, watchlist_kind="saved"),
            _result(
                tmdb_id=2,
                title="Lost",
                media_type="tv",
                in_library=True,
                on_watchlist=True,
                watchlist_kind="following",
            ),
        )
    )
    text = (await logged_in.get("/partials/search/tmdb", params={"query": "x"})).text
    assert text.count(f'class="badge saved">{SAVED_LABEL}<') == 1
    assert text.count(f'class="badge following">{FOLLOWING_LABEL}<') == 1
    assert text.count(IN_LIBRARY_LABEL) == 1


async def test_tmdb_results_carry_the_card_fields_and_a_browse_link(logged_in, mock_client):
    mock_client.search_tmdb = AsyncMock(
        return_value=_tmdb(_result(), _result(tmdb_id=2, title="Lost", media_type="tv"))
    )
    text = (await logged_in.get("/partials/search/tmdb", params={"query": "x"})).text
    assert '"media_type": "show"' in text and '"media_type": "movie"' in text
    assert text.count('class="browse"') == 1 and 'href="/shows/2"' in text
    assert SAVE_LABEL not in text and FOLLOW_LABEL not in text


async def test_tmdb_no_results(logged_in, mock_client):
    mock_client.search_tmdb = AsyncMock(return_value=_tmdb())
    text = (await logged_in.get("/partials/search/tmdb", params={"query": "zzz"})).text
    assert "No results" in text


async def test_scope_lists_seasons_without_specials(logged_in, mock_client):
    mock_client.search_tmdb_show = AsyncMock(
        return_value=TmdbMediaDetailResponse(
            status="success",
            message="",
            data={
                "seasons": [
                    {"season_number": 0, "episode_count": 3},
                    {"season_number": 1, "episode_count": 10},
                    {"season_number": 2, "episode_count": 8},
                ]
            },
        )
    )
    text = (
        await logged_in.get(
            "/partials/search/scope", params={"tmdb_id": 2, "title": "Lost", "year": "2004"}
        )
    ).text
    assert "Whole series" in text
    assert "Season 1 (10 episodes)" in text and "Season 2 (8 episodes)" in text
    assert "Season 0" not in text
    mock_client.search_tmdb_show.assert_awaited_once_with(2)


async def test_movie_torrents_query_carries_year_and_sorts_by_seeders(logged_in, mock_client):
    mock_client.search_torrents = AsyncMock(
        return_value=TorrentSearchResponse(
            status="success",
            message="",
            data={"1080p": [_torrent("low", 2), _torrent("high", 50, ["en"], True)], "720p": []},
        )
    )
    text = (
        await logged_in.get(
            "/partials/search/torrents",
            params={
                "tmdb_id": 1,
                "title": "Dune",
                "year": "2021",
                "media_type": "movie",
            },
        )
    ).text
    mock_client.search_torrents.assert_awaited_once_with(
        "Dune 2021", MediaType.MOVIE, season=None, episode=None, alt_query=None
    )
    assert text.index("high") < text.index("low")
    assert "EN" in text and "MULTi" in text
    assert text.count('hx-post="/downloads"') == 2


async def test_torrent_names_break_at_separators(logged_in, mock_client):
    mock_client.search_torrents = AsyncMock(
        return_value=TorrentSearchResponse(
            status="success", message="", data={"1080p": [_torrent()]}
        )
    )
    text = (
        await logged_in.get(
            "/partials/search/torrents",
            params={"tmdb_id": 1, "title": "Dune", "year": "2021", "media_type": "movie"},
        )
    ).text
    assert '<td class="release"><code>Dune.<wbr>2021.<wbr>1080p-<wbr>GRP</code></td>' in text


async def test_show_torrents_scope_is_forwarded(logged_in, mock_client):
    mock_client.search_torrents = AsyncMock(
        return_value=TorrentSearchResponse(status="success", message="", data={})
    )
    text = (
        await logged_in.get(
            "/partials/search/torrents",
            params={
                "tmdb_id": 2,
                "title": "Lost",
                "year": "2004",
                "media_type": "show",
                "season": "2",
                "episode": "5",
            },
        )
    ).text
    mock_client.search_torrents.assert_awaited_once_with(
        "Lost", MediaType.SHOW, season=2, episode=5, alt_query=None
    )
    assert "S02E05" in text
    assert "No torrents found" in text


async def test_whole_series_drops_season_and_episode(logged_in, mock_client):
    mock_client.search_torrents = AsyncMock(
        return_value=TorrentSearchResponse(status="success", message="", data={})
    )
    await logged_in.get(
        "/partials/search/torrents",
        params={
            "tmdb_id": 2,
            "title": "Lost",
            "year": "2004",
            "media_type": "show",
            "season": "all",
            "episode": "5",
        },
    )
    mock_client.search_torrents.assert_awaited_once_with(
        "Lost", MediaType.SHOW, season=None, episode=None, alt_query=None
    )


async def test_download_posts_the_three_fields(logged_in, mock_client):
    mock_client.download = AsyncMock(
        return_value=DownloadResponse(status="success", job=make_job("DOWNLOAD_SUBMITTED", "j9"))
    )
    response = await logged_in.post(
        "/downloads",
        data={
            "source_url": "magnet:?xt=urn:btih:abc",
            "media_type": "movie",
            "tmdb_id": "1",
            "file_name": "Dune.2021-GRP",
        },
    )
    assert response.status_code == 200
    assert "j9" in response.text and "Dune.2021-GRP" in response.text
    mock_client.download.assert_awaited_once_with(
        "magnet:?xt=urn:btih:abc", MediaType.MOVIE, 1, "Dune.2021-GRP", season=None, episode=None
    )


async def test_download_rejects_garbage_link(logged_in, mock_client):
    mock_client.download = AsyncMock()
    response = await logged_in.post(
        "/downloads",
        data={
            "source_url": "javascript:alert(1)",
            "media_type": "movie",
            "tmdb_id": "1",
            "file_name": "x",
        },
    )
    assert response.status_code == 422
    mock_client.download.assert_not_called()


async def test_download_failure_is_reported(logged_in, mock_client):
    mock_client.download = AsyncMock(return_value=None)
    response = await logged_in.post(
        "/downloads",
        data={
            "source_url": "http://x/t.torrent",
            "media_type": "show",
            "tmdb_id": "2",
            "file_name": "x",
        },
    )
    assert response.status_code == 502
    assert "nothing was submitted" in response.text


async def test_download_shows_the_detail_for_a_retryable_code(logged_in, mock_client):
    mock_client.download = AsyncMock(
        return_value=GatewayError(
            status_code=503,
            code="SOURCE_UNREACHABLE",
            detail="The source page could not be reached; the request can be retried.",
        )
    )
    response = await logged_in.post(
        "/downloads",
        data={
            "source_url": "magnet:?xt=urn:btih:abc",
            "media_type": "movie",
            "tmdb_id": "1",
            "file_name": "x",
        },
    )
    assert response.status_code == 502
    assert "could not be reached" in response.text
    assert "nothing was submitted" not in response.text


async def test_download_keeps_the_generic_message_for_an_unknown_code(logged_in, mock_client):
    mock_client.download = AsyncMock(
        return_value=GatewayError(status_code=500, code="INTERNAL_ERROR", detail="/srv/secret")
    )
    response = await logged_in.post(
        "/downloads",
        data={
            "source_url": "magnet:?xt=urn:btih:abc",
            "media_type": "movie",
            "tmdb_id": "1",
            "file_name": "x",
        },
    )
    assert response.status_code == 502
    assert "nothing was submitted" in response.text
    assert "/srv/secret" not in response.text


async def test_search_requires_login(client):
    assert (await client.get("/search")).status_code == 303
    assert (await client.post("/downloads", data={})).status_code == 303


async def test_results_land_in_the_stage_and_torrents_keep_the_query(logged_in, mock_client):
    mock_client.search_tmdb = AsyncMock(return_value=_tmdb(_result()))
    mock_client.search_torrents = AsyncMock(
        return_value=TorrentSearchResponse(status="success", message="", data={})
    )
    page = (await logged_in.get("/search")).text
    assert 'id="stage"' in page and page.count('hx-target="#stage"') == 1
    cards = (await logged_in.get("/partials/search/tmdb", params={"query": "dune"})).text
    assert "#stage" not in cards
    torrents = (
        await logged_in.get(
            "/partials/search/torrents",
            params={
                "tmdb_id": 1,
                "title": "Dune",
                "year": "2021",
                "media_type": "movie",
                "query": "dune",
            },
        )
    ).text
    assert "No torrents found" in torrents


async def test_clear_cache_button_and_action(logged_in, mock_client):
    from medialab_web.schemas.actions import CacheClearResponse

    page = (await logged_in.get("/search")).text
    assert 'hx-delete="/search/cache"' in page
    mock_client.clear_search_cache = AsyncMock(
        return_value=CacheClearResponse(status="success", cleared=True)
    )
    response = await logged_in.delete("/search/cache")
    assert response.status_code == 200
    assert "cleared" in response.text
    mock_client.clear_search_cache.assert_awaited_once()


async def test_clear_cache_failure(logged_in, mock_client):
    mock_client.clear_search_cache = AsyncMock(return_value=None)
    assert (await logged_in.delete("/search/cache")).status_code == 502


async def test_typed_query_becomes_alt_query(logged_in, mock_client):
    mock_client.search_torrents = AsyncMock(
        return_value=TorrentSearchResponse(status="success", message="", data={})
    )
    await logged_in.get(
        "/partials/search/torrents",
        params={
            "tmdb_id": 1,
            "title": "Lee Cronin's The Mummy",
            "year": "2026",
            "media_type": "movie",
            "query": "the mummy",
        },
    )
    mock_client.search_torrents.assert_awaited_once_with(
        "Lee Cronin's The Mummy 2026",
        MediaType.MOVIE,
        season=None,
        episode=None,
        alt_query="the mummy 2026",
    )


async def test_detail_card_carries_the_downloader_timeout_into_the_bar(logged_in, mock_client):
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
    page = (await logged_in.get("/partials/discover/detail", params=_DETAIL)).text
    assert "--search-seconds: 42s" in page and "Up to 42 s" in page


async def test_detail_card_falls_back_to_the_default_timeout(logged_in, mock_client):
    mock_client.get_settings = AsyncMock(return_value=None)
    page = (await logged_in.get("/partials/discover/detail", params=_DETAIL)).text
    assert "--search-seconds: 15s" in page


async def test_torrent_searches_use_the_searching_indicator(logged_in, mock_client):
    mock_client.search_tmdb = AsyncMock(
        return_value=_tmdb(_result(), _result(tmdb_id=2, title="Lost", media_type="tv"))
    )
    mock_client.search_tmdb_show = AsyncMock(
        return_value=TmdbMediaDetailResponse(status="success", message="", data={"seasons": []})
    )
    cards = (await logged_in.get("/partials/search/tmdb", params={"query": "x"})).text
    assert "#searching" not in cards
    scope = (
        await logged_in.get(
            "/partials/search/scope", params={"tmdb_id": 2, "title": "Lost", "year": "2004"}
        )
    ).text
    assert 'hx-indicator="previous .searching"' in scope


async def test_tmdb_results_render_poster_and_text_card(logged_in, mock_client):
    mock_client.search_tmdb = AsyncMock(
        return_value=_tmdb(
            _result(poster_path="/dune.jpg"),
            _result(tmdb_id=2, title="Lost", media_type="tv", poster_path=None),
        )
    )
    text = (await logged_in.get("/partials/search/tmdb", params={"query": "x"})).text
    assert f'src="{poster_url("/dune.jpg", PosterSize.GRID)}"' in text
    assert 'loading="lazy"' in text
    assert text.count("<img") == 1
    assert text.count('poster-card no-poster"') == 1
    assert text.count('class="poster"') == 2


async def test_search_torrents_are_not_in_redo_mode(logged_in, mock_client):
    mock_client.search_torrents = AsyncMock(
        return_value=TorrentSearchResponse(
            status="success", message="", data={"1080p": [_torrent()]}
        )
    )
    text = (
        await logged_in.get(
            "/partials/search/torrents",
            params={"tmdb_id": 1, "title": "Dune", "year": "2021", "media_type": "movie"},
        )
    ).text
    assert REDO_NOTICE not in text
    assert "/redo" not in text
    assert "Torrents for <strong>Dune (2021)</strong>" in text


def test_torrent_query_never_wraps_the_year_in_parentheses():
    # A parenthesised year poisons release-name matching; the pattern is "Title YYYY".
    from medialab_web.routes.search import _torrent_query

    assert _torrent_query("Dune", "2021", MediaType.MOVIE) == "Dune 2021"
    assert _torrent_query("Lost", "2004", MediaType.SHOW) == "Lost"
    assert "(" not in _torrent_query("Dune", "2021", MediaType.MOVIE)
