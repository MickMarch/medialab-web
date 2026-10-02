import json
from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest
from medialab_contracts import MediaType, Video, VideosResponse, VideoType, youtube_embed_url

from medialab_web.constants import (
    NO_TRAILER_NOTICE,
    OFFICIAL_LABEL,
    TRAILER_PLAY_PATH,
    TRAILER_SLOT_CLASS,
    TRAILERS_PARTIAL_PATH,
    WATCH_TRAILER_LABEL,
)
from medialab_web.format import youtube_thumbnail_url
from tests.test_discover_page import _detail_params, _vals
from tests.test_show_page import SHOW_ID, SHOW_PATH, _show

TRAILERS_BUTTON = f'hx-get="{TRAILERS_PARTIAL_PATH}"'
PLAY_BUTTON = f'hx-get="{TRAILER_PLAY_PATH}"'
NOCOOKIE_HOST = "https://www.youtube-nocookie.com/embed/"


def _video(key: str = "dQw4w9WgXcQ", **kw) -> Video:
    base = {
        "key": key,
        "name": "Official Trailer",
        "type": VideoType.TRAILER,
        "official": True,
        "published_at": datetime(2021, 7, 22, tzinfo=UTC),
        "language": "en",
    }
    return Video(**{**base, **kw})


def _all_vals(html: str, marker: str) -> list[dict]:
    vals = []
    position = 0
    while True:
        start = html.find(marker, position)
        if start < 0:
            return vals
        end = html.index(">", start)
        tag = html[html.rfind("<", 0, start) : end]
        vals.append(json.loads(tag.split("hx-vals='", 1)[1].split("'", 1)[0]))
        position = end


@pytest.fixture
def videos_client(mock_client):
    mock_client.videos = AsyncMock(return_value=VideosResponse(videos=[_video()]))
    return mock_client


# --- buttons: nothing fetched on render ---


async def test_detail_card_has_watch_trailer_button_without_fetching(logged_in, videos_client):
    text = (await logged_in.get("/partials/discover/detail", params=_detail_params())).text
    assert WATCH_TRAILER_LABEL in text
    vals = _vals(text, TRAILERS_BUTTON)
    assert vals == {"media_type": "movie", "tmdb_id": 438631}
    assert text.count(f'class="{TRAILER_SLOT_CLASS}"') == 1
    assert NOCOOKIE_HOST not in text
    videos_client.videos.assert_not_awaited()


async def test_detail_card_show_button_carries_no_season(logged_in, videos_client):
    params = _detail_params(media_type="show", tmdb_id=SHOW_ID, title="Breaking Bad")
    text = (await logged_in.get("/partials/discover/detail", params=params)).text
    assert _vals(text, TRAILERS_BUTTON) == {"media_type": "show", "tmdb_id": SHOW_ID}


async def test_show_page_season_rows_have_watch_trailer_buttons(logged_in, videos_client):
    videos_client.browse_show = AsyncMock(return_value=_show())
    text = (await logged_in.get(SHOW_PATH)).text
    vals = _all_vals(text, TRAILERS_BUTTON)
    assert vals == [
        {"media_type": "show", "tmdb_id": SHOW_ID, "season": 1},
        {"media_type": "show", "tmdb_id": SHOW_ID, "season": 2},
    ]
    assert text.count(f'class="{TRAILER_SLOT_CLASS}"') == 2
    # The button sits in the season body, before the episodes, not in the summary.
    first_button = text.index(TRAILERS_BUTTON)
    first_season = text.index('class="season"')
    assert text.index("</summary>", first_season) < first_button
    assert first_button < text.index('class="episodes plain"')
    videos_client.videos.assert_not_awaited()


# --- the trailers partial ---


async def test_single_video_plays_at_once(logged_in, videos_client):
    response = await logged_in.get(
        TRAILERS_PARTIAL_PATH, params={"media_type": "movie", "tmdb_id": 438631}
    )
    assert response.status_code == 200
    text = response.text
    assert f'src="{youtube_embed_url("dQw4w9WgXcQ")}"' in text
    assert NOCOOKIE_HOST in text
    assert 'title="Official Trailer"' in text
    assert 'allow="autoplay; encrypted-media; picture-in-picture"' in text
    assert "allowfullscreen" in text
    assert 'loading="lazy"' in text
    assert 'referrerpolicy="strict-origin-when-cross-origin"' in text
    assert "Close" in text
    assert PLAY_BUTTON not in text
    videos_client.videos.assert_awaited_once_with(MediaType.MOVIE, 438631, season=None)


async def test_season_is_forwarded_to_the_client(logged_in, videos_client):
    await logged_in.get(
        TRAILERS_PARTIAL_PATH, params={"media_type": "show", "tmdb_id": SHOW_ID, "season": 2}
    )
    videos_client.videos.assert_awaited_once_with(MediaType.SHOW, SHOW_ID, season=2)


async def test_several_videos_render_a_thumbnail_grid(logged_in, videos_client):
    videos_client.videos = AsyncMock(
        return_value=VideosResponse(
            videos=[
                _video("aaa", name="Main Trailer"),
                _video("bbb", name="Teaser", type=VideoType.TEASER, official=False),
            ]
        )
    )
    text = (
        await logged_in.get(TRAILERS_PARTIAL_PATH, params={"media_type": "movie", "tmdb_id": 1})
    ).text
    assert NOCOOKIE_HOST not in text
    assert "Main Trailer" in text and "Teaser" in text
    assert text.count(OFFICIAL_LABEL) == 1
    assert "trailer" in text and "teaser" in text
    vals = _all_vals(text, PLAY_BUTTON)
    assert vals == [{"key": "aaa", "name": "Main Trailer"}, {"key": "bbb", "name": "Teaser"}]
    assert text.count(f'hx-target="closest .{TRAILER_SLOT_CLASS}"') == 2
    # one lazy thumbnail per video, from YouTube's keyless image host
    assert f'src="{youtube_thumbnail_url("aaa")}"' in text
    assert f'src="{youtube_thumbnail_url("bbb")}"' in text
    assert text.count('loading="lazy"') == 2
    assert text.count('class="trailer-title"') == 2
    assert '<ul class="trailers' in text


async def test_untitled_video_falls_back_to_its_type(logged_in, videos_client):
    videos_client.videos = AsyncMock(
        return_value=VideosResponse(
            videos=[_video("aaa", name=""), _video("bbb", name="", type=VideoType.TEASER)]
        )
    )
    text = (
        await logged_in.get(TRAILERS_PARTIAL_PATH, params={"media_type": "movie", "tmdb_id": 1})
    ).text
    assert '<span class="trailer-title">trailer</span>' in text
    assert '<span class="trailer-title">teaser</span>' in text


async def test_no_videos_renders_the_notice(logged_in, videos_client):
    videos_client.videos = AsyncMock(return_value=VideosResponse(videos=[]))
    response = await logged_in.get(
        TRAILERS_PARTIAL_PATH, params={"media_type": "movie", "tmdb_id": 1}
    )
    assert response.status_code == 200
    assert NO_TRAILER_NOTICE in response.text
    assert NOCOOKIE_HOST not in response.text


async def test_client_failure_renders_the_error_fragment(logged_in, videos_client):
    videos_client.videos = AsyncMock(return_value=None)
    response = await logged_in.get(
        TRAILERS_PARTIAL_PATH, params={"media_type": "movie", "tmdb_id": 1}
    )
    assert response.status_code == 502
    assert 'class="error"' in response.text


async def test_play_route_renders_the_player(logged_in, videos_client):
    response = await logged_in.get(TRAILER_PLAY_PATH, params={"key": "zzz", "name": "Teaser 2"})
    assert response.status_code == 200
    assert f'src="{youtube_embed_url("zzz")}"' in response.text
    assert 'title="Teaser 2"' in response.text
    videos_client.videos.assert_not_awaited()


async def test_trailer_routes_require_login(client):
    params = {"media_type": "movie", "tmdb_id": 1}
    assert (await client.get(TRAILERS_PARTIAL_PATH, params=params)).status_code == 303
    assert (await client.get(TRAILER_PLAY_PATH, params={"key": "k"})).status_code == 303
