import json
from datetime import date
from unittest.mock import AsyncMock

import pytest
from medialab_contracts import (
    DiscoverResponse,
    EpisodeState,
    MediaType,
    PosterSize,
    Season,
    ShowBrowseResponse,
    WatchlistKind,
    WatchlistResponse,
    poster_url,
    still_url,
)

from medialab_web.constants import (
    FOLLOW_LABEL,
    FOLLOWING_LABEL,
    IGNORED_LABEL,
    IN_LIBRARY_LABEL,
    QUEUED_LABEL,
    RETRY_LABEL,
    SAVED_LABEL,
    SUBMITTED_LABEL,
    UNAIRED_LABEL,
    WANTED_LABEL,
    WHOLE_SERIES,
)
from medialab_web.schemas.downloads import DownloadResponse
from tests.conftest import make_job
from tests.test_discover_page import NOW, _item, _saved

SHOW_ID = 1396
SHOW_PATH = f"/shows/{SHOW_ID}"
TORRENTS_PARTIAL = 'hx-get="/partials/search/torrents"'


def _episode(season: int, episode: int, **kw) -> EpisodeState:
    base = {
        "season": season,
        "episode": episode,
        "title": f"Episode {season}.{episode}",
        "air_date": date(2008, 1, 20),
        "overview": "Chemistry happens.",
        "still_path": f"/s{season}e{episode}.jpg",
        "aired": True,
    }
    return EpisodeState(**{**base, **kw})


def _show(**kw) -> ShowBrowseResponse:
    base = {
        "tmdb_id": SHOW_ID,
        "title": "Breaking Bad",
        "year": "2008",
        "poster_path": "/bb.jpg",
        "overview": "A chemistry teacher.",
        "status": "Ended",
        "seasons": [
            Season(season=1, name="Season 1", episode_count=2, air_date=date(2008, 1, 20)),
            Season(season=2, name="Season 2", episode_count=1, air_date=date(2009, 3, 8)),
        ],
        "episodes": [_episode(1, 1), _episode(1, 2), _episode(2, 1)],
    }
    return ShowBrowseResponse(**{**base, **kw})


def _buttons_vals(html: str) -> list[dict]:
    """The hx-vals of every Find torrents button, in document order."""
    vals = []
    position = 0
    while True:
        start = html.find(TORRENTS_PARTIAL, position)
        if start < 0:
            return vals
        end = html.index(">", start)
        tag = html[start:end]
        raw = tag.split("hx-vals='", 1)[1].split("'", 1)[0]
        vals.append(json.loads(raw))
        position = end


@pytest.fixture
def show_client(mock_client):
    mock_client.browse_show = AsyncMock(return_value=_show())
    return mock_client


# --- page ---


async def test_show_page_renders_header_and_seasons(logged_in, show_client):
    response = await logged_in.get(SHOW_PATH)
    assert response.status_code == 200
    text = response.text
    assert "Breaking Bad" in text and "2008" in text and "Ended" in text
    assert "A chemistry teacher." in text
    assert f'src="{poster_url("/bb.jpg", PosterSize.GRID)}"' in text
    assert "Season 1" in text and "Season 2" in text
    assert "S01E01" in text and "S01E02" in text and "S02E01" in text
    assert "Episode 1.1" in text
    assert 'id="stage"' in text and 'id="searching"' in text and 'id="busy"' in text
    show_client.browse_show.assert_awaited_once_with(SHOW_ID)


async def test_show_page_opens_only_the_latest_season(logged_in, show_client):
    text = (await logged_in.get(SHOW_PATH)).text
    assert text.count('class="season"') == 2
    assert text.count("<details open") == 1
    latest = text.index("<details open")
    assert "Season 2" in text[latest : text.index("</summary>", latest)]


async def test_show_page_find_torrents_scopes(logged_in, show_client):
    vals = _buttons_vals((await logged_in.get(SHOW_PATH)).text)
    # series, season 1, its two episodes, season 2, its episode
    assert len(vals) == 6
    series, season_one, ep_one, ep_two, season_two, ep_three = vals
    common = {"tmdb_id": SHOW_ID, "title": "Breaking Bad", "year": "2008", "media_type": "show"}
    for entry in vals:
        assert {k: entry[k] for k in common} == common
    assert series["season"] == WHOLE_SERIES and "episode" not in series
    assert season_one["season"] == 1 and "episode" not in season_one
    assert season_two["season"] == 2 and "episode" not in season_two
    assert (ep_one["season"], ep_one["episode"]) == (1, 1)
    assert (ep_two["season"], ep_two["episode"]) == (1, 2)
    assert (ep_three["season"], ep_three["episode"]) == (2, 1)


async def test_show_page_buttons_target_the_stage_with_the_searching_indicator(
    logged_in, show_client
):
    text = (await logged_in.get(SHOW_PATH)).text
    assert text.count(TORRENTS_PARTIAL) == 6
    assert text.count('hx-target="#stage"') == 6
    assert text.count('hx-indicator="#searching"') == 6


async def test_show_page_series_badges(logged_in, show_client):
    text = (await logged_in.get(SHOW_PATH)).text
    assert IN_LIBRARY_LABEL not in text and SAVED_LABEL not in text
    show_client.browse_show = AsyncMock(
        return_value=_show(in_library=True, on_watchlist=True, watchlist_kind=WatchlistKind.SAVED)
    )
    text = (await logged_in.get(SHOW_PATH)).text
    assert IN_LIBRARY_LABEL in text and 'class="badge saved"' in text


async def test_show_page_header_has_save_and_an_inline_follow_picker(logged_in, show_client):
    show_client.watchlist_episodes = AsyncMock()
    text = (await logged_in.get(SHOW_PATH)).text
    assert 'hx-put="/partials/watchlist"' in text
    assert '<details class="follow-inline">' in text and f">{FOLLOW_LABEL}</summary>" in text
    assert 'hx-put="/partials/watchlist/follow"' in text
    # seeded from the page data: no extra gateway call for the seasons
    assert '<option value="1" data-episodes="2">' in text
    assert '<option value="2" data-episodes="1">' in text
    assert 'hx-get="/partials/watchlist/follow"' not in text
    show_client.browse_show.assert_awaited_once_with(SHOW_ID)
    show_client.watchlist_episodes.assert_not_awaited()


async def test_show_page_following_reads_the_watchlist_episodes(logged_in, show_client):
    show_client.browse_show = AsyncMock(
        return_value=_show(on_watchlist=True, watchlist_kind=WatchlistKind.FOLLOWING)
    )
    show_client.watchlist_episodes = AsyncMock(
        return_value=_show(
            on_watchlist=True,
            watchlist_kind=WatchlistKind.FOLLOWING,
            episodes=[
                _episode(1, 1, submitted="submitted"),
                _episode(1, 2, submitted="ignored"),
                _episode(2, 1, wanted=True),
            ],
        )
    )
    text = (await logged_in.get(SHOW_PATH)).text
    show_client.watchlist_episodes.assert_awaited_once_with(SHOW_ID)
    assert 'class="badge following"' in text and FOLLOWING_LABEL in text
    assert text.count(SUBMITTED_LABEL) == 1 and text.count(IGNORED_LABEL) == 1
    assert text.count(WANTED_LABEL) == 1
    assert text.count(f">{RETRY_LABEL}<") == 2
    assert f'hx-delete="/partials/watchlist/{SHOW_ID}/episodes/1/1/submission"' in text
    assert 'hx-delete="/partials/watchlist/follow"' in text and "Unfollow" in text
    assert "follow-inline" not in text


async def test_show_page_not_following_hides_follow_badges(logged_in, show_client):
    show_client.browse_show = AsyncMock(
        return_value=_show(episodes=[_episode(1, 1, submitted="submitted", wanted=True)])
    )
    text = (await logged_in.get(SHOW_PATH)).text
    assert SUBMITTED_LABEL not in text and WANTED_LABEL not in text
    assert f">{RETRY_LABEL}<" not in text


async def test_show_page_episode_badges(logged_in, show_client):
    show_client.browse_show = AsyncMock(
        return_value=_show(
            episodes=[
                _episode(1, 1, in_library=True),
                _episode(1, 2, queued_job_id="job-7"),
                _episode(2, 1, aired=False, air_date=None),
            ]
        )
    )
    text = (await logged_in.get(SHOW_PATH)).text
    assert text.count(IN_LIBRARY_LABEL) == 1
    assert text.count(QUEUED_LABEL) == 1
    assert text.count(UNAIRED_LABEL) == 1
    assert 'href="/#job-job-7"' in text


async def test_show_page_episode_stills_are_lazy(logged_in, show_client):
    text = (await logged_in.get(SHOW_PATH)).text
    assert f'src="{still_url("/s1e1.jpg")}"' in text
    assert text.count('class="still"') == 3
    assert text.count('loading="lazy"') == 3


async def test_show_page_failure_is_friendly(logged_in, show_client):
    show_client.browse_show = AsyncMock(return_value=None)
    response = await logged_in.get(SHOW_PATH)
    assert response.status_code == 200
    assert "Could not load this show" in response.text
    assert 'href="/discover"' in response.text


async def test_show_page_requires_login(client):
    assert (await client.get(SHOW_PATH)).status_code == 303


# --- entry points ---


async def test_browse_link_on_show_cards_only(logged_in, mock_client):
    mock_client.discover = AsyncMock(
        return_value=DiscoverResponse(
            items=[_item(), _item(tmdb_id=SHOW_ID, media_type=MediaType.SHOW, title="BB")],
            page=1,
            total_pages=1,
            cached_at=NOW,
        )
    )
    mock_client.discover_genres = AsyncMock(return_value=None)
    text = (await logged_in.get("/discover")).text
    assert text.count("Browse") == 1
    assert f'href="{SHOW_PATH}"' in text
    assert 'href="/shows/438631"' not in text


async def test_browse_link_on_watchlist_show_cards(logged_in, mock_client):
    mock_client.list_watchlist = AsyncMock(
        return_value=WatchlistResponse(
            items=[_saved(), _saved(tmdb_id=5, media_type=MediaType.MOVIE, title="Heat")]
        )
    )
    text = (await logged_in.get("/watchlist")).text
    assert text.count("Browse") == 1
    assert f'href="{SHOW_PATH}"' in text


async def test_browse_link_on_search_result_show_cards(logged_in, mock_client):
    from tests.test_search_page import _result, _tmdb

    mock_client.search_tmdb = AsyncMock(
        return_value=_tmdb(_result(), _result(tmdb_id=SHOW_ID, title="BB", media_type="tv"))
    )
    text = (await logged_in.get("/partials/search/tmdb", params={"query": "x"})).text
    assert text.count("Browse") == 1
    assert f'href="{SHOW_PATH}"' in text


async def test_job_row_title_links_to_show_page_for_shows(logged_in, mock_client):
    from medialab_web.schemas.jobs import JobsResponse

    mock_client.list_jobs = AsyncMock(
        return_value=JobsResponse(
            status="success",
            jobs=[
                make_job("DONE", "a"),
                make_job(
                    "DONE",
                    "b",
                    media_type=MediaType.SHOW,
                    tmdb_id=SHOW_ID,
                    resolved_title="Breaking Bad",
                    resolved_year=2008,
                    season=2,
                    episode=5,
                ),
            ],
        )
    )
    text = (await logged_in.get("/partials/jobs")).text
    assert text.count(f'href="{SHOW_PATH}"') == 1
    assert 'href="/shows/1"' not in text


# --- download scope ---


def _download_form(**kw) -> dict:
    return {
        "source_url": "magnet:?xt=urn:btih:abc",
        "media_type": "show",
        "tmdb_id": str(SHOW_ID),
        "file_name": "BB.S02E05-GRP",
        **kw,
    }


async def test_download_forwards_season_and_episode(logged_in, mock_client):
    mock_client.download = AsyncMock(
        return_value=DownloadResponse(status="success", job=make_job("DOWNLOAD_SUBMITTED", "j9"))
    )
    response = await logged_in.post("/downloads", data=_download_form(season="2", episode="5"))
    assert response.status_code == 200
    mock_client.download.assert_awaited_once_with(
        "magnet:?xt=urn:btih:abc", MediaType.SHOW, SHOW_ID, "BB.S02E05-GRP", season=2, episode=5
    )


async def test_download_forwards_season_only(logged_in, mock_client):
    mock_client.download = AsyncMock(
        return_value=DownloadResponse(status="success", job=make_job("DOWNLOAD_SUBMITTED", "j9"))
    )
    await logged_in.post("/downloads", data=_download_form(season="2"))
    mock_client.download.assert_awaited_once_with(
        "magnet:?xt=urn:btih:abc", MediaType.SHOW, SHOW_ID, "BB.S02E05-GRP", season=2, episode=None
    )


async def test_download_omits_scope_for_whole_series(logged_in, mock_client):
    mock_client.download = AsyncMock(
        return_value=DownloadResponse(status="success", job=make_job("DOWNLOAD_SUBMITTED", "j9"))
    )
    await logged_in.post("/downloads", data=_download_form(season=WHOLE_SERIES, episode="5"))
    mock_client.download.assert_awaited_once_with(
        "magnet:?xt=urn:btih:abc",
        MediaType.SHOW,
        SHOW_ID,
        "BB.S02E05-GRP",
        season=None,
        episode=None,
    )


async def test_torrents_partial_carries_scope_into_the_download_form(logged_in, mock_client):
    from medialab_web.schemas.torrents import TorrentResult, TorrentSearchResponse

    mock_client.search_torrents = AsyncMock(
        return_value=TorrentSearchResponse(
            status="success",
            message="",
            data={
                "1080p": [
                    TorrentResult(
                        fileName="BB.S02E05",
                        fileUrl="magnet:?xt=urn:btih:abc",
                        nbSeeders=1,
                        nbLeechers=0,
                        fileSize=1,
                    )
                ]
            },
        )
    )
    params = {"tmdb_id": SHOW_ID, "title": "BB", "year": "2008", "media_type": "show"}
    text = (
        await logged_in.get(
            "/partials/search/torrents", params={**params, "season": "2", "episode": "5"}
        )
    ).text
    assert 'name="season" value="2"' in text and 'name="episode" value="5"' in text
    text = (await logged_in.get("/partials/search/torrents", params={**params, "season": "2"})).text
    assert 'name="season" value="2"' in text and 'name="episode"' not in text
    text = (
        await logged_in.get("/partials/search/torrents", params={**params, "season": WHOLE_SERIES})
    ).text
    assert 'name="season"' not in text and 'name="episode"' not in text
