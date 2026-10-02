from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest
from medialab_contracts import (
    FollowRequest,
    FollowStart,
    FollowStartMode,
    FollowState,
    MediaType,
    WatchlistAddRequest,
    WatchlistKind,
    WatchlistResponse,
)

from medialab_web.constants import (
    CHECK_NOW_LABEL,
    EPISODES_LABEL,
    FOLLOW_LABEL,
    FOLLOWING_LABEL,
    IGNORED_LABEL,
    NOTHING_SUBMITTED_NOTICE,
    PAUSE_LABEL,
    PAUSED_LABEL,
    RESUME_LABEL,
    RETRY_LABEL,
    SAVED_LABEL,
    SUBMITTED_LABEL,
    UNFOLLOW_LABEL,
    WANTED_LABEL,
)
from medialab_web.schemas.watchlist import FollowCheckResponse
from tests.test_discover_page import _item, _saved, _vals
from tests.test_show_page import SHOW_ID, _episode, _show

CHECKED = datetime(2026, 9, 27, 14, 3, tzinfo=UTC)
FOLLOW_PATH = "/partials/watchlist/follow"
SHOW_FORM = {
    **_item(media_type=MediaType.SHOW, tmdb_id=SHOW_ID, title="Breaking Bad").model_dump(
        mode="json"
    ),
    "year": "2008",
}


def _follow(**kw) -> FollowState:
    base = {
        "start": FollowStart(mode=FollowStartMode.FROM, season=2, episode=3),
        "resolution": "1080p",
        "followed_at": CHECKED,
        "last_checked_at": CHECKED,
        "last_submitted": "S02E05",
    }
    return FollowState(**{**base, **kw})


def _following(**kw):
    return _saved(**{"kind": WatchlistKind.FOLLOWING, "follow": _follow(), **kw})


@pytest.fixture
def watchlist_client(mock_client):
    mock_client.list_watchlist = AsyncMock(return_value=WatchlistResponse(items=[]))
    mock_client.add_to_watchlist = AsyncMock(return_value=_saved())
    mock_client.remove_from_watchlist = AsyncMock(return_value=True)
    mock_client.follow_show = AsyncMock(return_value=_following())
    mock_client.unfollow_show = AsyncMock(return_value=True)
    mock_client.pause_follow = AsyncMock(return_value=_following(follow=_follow(paused=True)))
    mock_client.resume_follow = AsyncMock(return_value=_following())
    mock_client.check_follow = AsyncMock(return_value=FollowCheckResponse(submitted=["S02E06"]))
    mock_client.browse_show = AsyncMock(return_value=_show())
    mock_client.watchlist_episodes = AsyncMock(
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
    mock_client.retry_episode = AsyncMock(return_value=True)
    return mock_client


# --- page and tabs ---


async def test_old_wishlist_path_redirects_permanently(logged_in):
    response = await logged_in.get("/wishlist")
    assert response.status_code == 308
    assert response.headers["location"] == "/watchlist"


async def test_watchlist_defaults_to_the_saved_tab(logged_in, watchlist_client):
    text = (await logged_in.get("/watchlist")).text
    watchlist_client.list_watchlist.assert_awaited_once_with(kind=WatchlistKind.SAVED)
    assert 'href="/watchlist?kind=saved"' in text and 'href="/watchlist?kind=following"' in text
    assert f'aria-selected="true" aria-current="page">{SAVED_LABEL}</a>' in text
    assert "Nothing saved yet" in text


async def test_following_tab_filters_by_kind(logged_in, watchlist_client):
    text = (await logged_in.get("/watchlist", params={"kind": "following"})).text
    watchlist_client.list_watchlist.assert_awaited_once_with(kind=WatchlistKind.FOLLOWING)
    assert f'aria-selected="true" aria-current="page">{FOLLOWING_LABEL}</a>' in text
    assert "You follow no shows yet" in text


async def test_watchlist_unreachable(logged_in, watchlist_client):
    watchlist_client.list_watchlist = AsyncMock(return_value=None)
    assert "Could not load the watchlist" in (await logged_in.get("/watchlist")).text


async def test_saved_tab_cards_have_download_follow_remove(logged_in, watchlist_client):
    watchlist_client.list_watchlist = AsyncMock(
        return_value=WatchlistResponse(
            items=[
                _saved(in_library=True),
                _saved(tmdb_id=5, media_type=MediaType.MOVIE, title="Heat"),
            ]
        )
    )
    text = (await logged_in.get("/watchlist")).text
    assert "Breaking Bad" in text and "Heat" in text and "In Jellyfin" in text
    assert SAVED_LABEL not in text.split("</nav>", 1)[1].split('id="stage"')[1]
    assert 'hx-get="/partials/search/scope"' in text
    assert 'hx-get="/partials/search/torrents"' in text
    assert text.count('hx-delete="/partials/watchlist"') == 2
    # Follow only on the show, opening the picker in the stage
    assert text.count(f'hx-get="{FOLLOW_PATH}"') == 1
    vals = _vals(text, f'hx-get="{FOLLOW_PATH}"')
    assert vals["tmdb_id"] == SHOW_ID and vals["view"] == "page"
    assert 'hx-target="#stage"' in text[text.index(f'hx-get="{FOLLOW_PATH}"') :]


async def test_saved_tab_remove_calls_delete(logged_in, watchlist_client):
    params = _item(media_type=MediaType.SHOW, tmdb_id=SHOW_ID).model_dump(mode="json")
    response = await logged_in.delete("/partials/watchlist", params=params)
    assert response.status_code == 200
    watchlist_client.remove_from_watchlist.assert_awaited_once_with(MediaType.SHOW, SHOW_ID)


# --- Following card ---


async def test_following_card_shows_state_and_the_four_actions(logged_in, watchlist_client):
    watchlist_client.list_watchlist = AsyncMock(
        return_value=WatchlistResponse(items=[_following()])
    )
    text = (await logged_in.get("/watchlist", params={"kind": "following"})).text
    assert 'follow-card"' in text and "Breaking Bad" in text
    assert "From S02E03" in text and "1080p" in text
    assert "2026-09-27 14:03" in text and "S02E05" in text
    assert PAUSED_LABEL not in text
    follow = f"/partials/watchlist/{SHOW_ID}/follow"
    assert f'hx-post="{follow}/pause"' in text and f">{PAUSE_LABEL}<" in text
    assert RESUME_LABEL + "<" not in text
    assert f'hx-post="{follow}/check"' in text and f">{CHECK_NOW_LABEL}<" in text
    assert f'hx-delete="{FOLLOW_PATH}"' in text and f">{UNFOLLOW_LABEL}<" in text
    assert _vals(text, f'hx-delete="{FOLLOW_PATH}"')["tmdb_id"] == SHOW_ID
    assert f"<summary>{EPISODES_LABEL}</summary>" in text
    assert f'hx-get="/partials/watchlist/{SHOW_ID}/episodes"' in text
    assert f'href="/shows/{SHOW_ID}"' in text


async def test_following_card_start_texts(logged_in, watchlist_client):
    def card(mode: FollowStartMode, **scope) -> str:
        return "\n".join([])  # placeholder to keep the helper local

    for mode, expected in (
        (FollowStartMode.NEW_ONLY, "New episodes"),
        (FollowStartMode.BEGINNING, "From the beginning"),
    ):
        watchlist_client.list_watchlist = AsyncMock(
            return_value=WatchlistResponse(
                items=[
                    _saved(
                        kind=WatchlistKind.FOLLOWING,
                        follow=_follow(
                            start=FollowStart(mode=mode),
                            last_checked_at=None,
                            last_submitted=None,
                        ),
                    )
                ]
            )
        )
        text = (await logged_in.get("/watchlist", params={"kind": "following"})).text
        assert expected in text
        assert text.count("never") == 2


async def test_paused_card_offers_resume(logged_in, watchlist_client):
    watchlist_client.list_watchlist = AsyncMock(
        return_value=WatchlistResponse(items=[_following(follow=_follow(paused=True))])
    )
    text = (await logged_in.get("/watchlist", params={"kind": "following"})).text
    assert PAUSED_LABEL in text
    assert f">{RESUME_LABEL}<" in text and f">{PAUSE_LABEL}<" not in text


async def test_pause_and_resume_re_render_the_card(logged_in, watchlist_client):
    text = (await logged_in.post(f"/partials/watchlist/{SHOW_ID}/follow/pause")).text
    watchlist_client.pause_follow.assert_awaited_once_with(SHOW_ID)
    assert 'follow-card"' in text and f">{RESUME_LABEL}<" in text
    text = (await logged_in.post(f"/partials/watchlist/{SHOW_ID}/follow/resume")).text
    watchlist_client.resume_follow.assert_awaited_once_with(SHOW_ID)
    assert f">{PAUSE_LABEL}<" in text


async def test_pause_failure_renders_error(logged_in, watchlist_client):
    watchlist_client.pause_follow = AsyncMock(return_value=None)
    response = await logged_in.post(f"/partials/watchlist/{SHOW_ID}/follow/pause")
    assert response.status_code == 502


async def test_check_now_reports_what_was_submitted(logged_in, watchlist_client):
    text = (await logged_in.post(f"/partials/watchlist/{SHOW_ID}/follow/check")).text
    watchlist_client.check_follow.assert_awaited_once_with(SHOW_ID)
    assert "Submitted S02E06." in text
    watchlist_client.check_follow = AsyncMock(return_value=FollowCheckResponse(submitted=[]))
    text = (await logged_in.post(f"/partials/watchlist/{SHOW_ID}/follow/check")).text
    assert NOTHING_SUBMITTED_NOTICE in text
    watchlist_client.check_follow = AsyncMock(return_value=None)
    assert (await logged_in.post(f"/partials/watchlist/{SHOW_ID}/follow/check")).status_code == 502


async def test_unfollow_calls_the_client_and_renders_saved_actions(logged_in, watchlist_client):
    params = {**SHOW_FORM, "on_watchlist": "true", "watchlist_kind": "following"}
    text = (await logged_in.delete(FOLLOW_PATH, params=params)).text
    watchlist_client.unfollow_show.assert_awaited_once_with(SHOW_ID)
    assert f">{FOLLOW_LABEL}<" in text and "Unsave" in text
    assert UNFOLLOW_LABEL not in text
    watchlist_client.unfollow_show = AsyncMock(return_value=False)
    assert (await logged_in.delete(FOLLOW_PATH, params=params)).status_code == 502


# --- episodes and Retry ---


async def test_episodes_partial_carries_follow_badges_and_retry(logged_in, watchlist_client):
    text = (await logged_in.get(f"/partials/watchlist/{SHOW_ID}/episodes")).text
    watchlist_client.watchlist_episodes.assert_awaited_once_with(SHOW_ID)
    assert "S01E01" in text and "S02E01" in text
    assert text.count(SUBMITTED_LABEL) == 1
    assert text.count(IGNORED_LABEL) == 1
    assert text.count(WANTED_LABEL) == 1
    assert text.count(f">{RETRY_LABEL}<") == 2
    retry = f'hx-delete="/partials/watchlist/{SHOW_ID}/episodes/1/2/submission"'
    assert retry in text
    assert 'hx-target="closest .episodes-slot"' in text[text.index(retry) :]
    assert text.count('hx-get="/partials/search/torrents"') == 5


async def test_episodes_partial_failure(logged_in, watchlist_client):
    watchlist_client.watchlist_episodes = AsyncMock(return_value=None)
    response = await logged_in.get(f"/partials/watchlist/{SHOW_ID}/episodes")
    assert response.status_code == 502


async def test_retry_clears_the_submission_and_re_renders(logged_in, watchlist_client):
    response = await logged_in.delete(f"/partials/watchlist/{SHOW_ID}/episodes/1/2/submission")
    assert response.status_code == 200
    watchlist_client.retry_episode.assert_awaited_once_with(SHOW_ID, 1, 2)
    watchlist_client.watchlist_episodes.assert_awaited_once_with(SHOW_ID)
    assert "S01E02" in response.text
    watchlist_client.retry_episode = AsyncMock(return_value=False)
    response = await logged_in.delete(f"/partials/watchlist/{SHOW_ID}/episodes/1/2/submission")
    assert response.status_code == 502


# --- save and unsave ---


async def test_save_swaps_to_unsave_and_back(logged_in, watchlist_client):
    form = _item().model_dump(mode="json")
    text = (await logged_in.put("/partials/watchlist", data=form)).text
    assert "Unsave" in text and 'hx-delete="/partials/watchlist"' in text
    watchlist_client.add_to_watchlist.assert_awaited_once_with(
        MediaType.MOVIE,
        438631,
        WatchlistAddRequest(
            title="Dune", year="2021", poster_path="/dune.jpg", overview="Desert planet."
        ),
    )
    text = (await logged_in.delete("/partials/watchlist", params=form)).text
    assert 'hx-put="/partials/watchlist"' in text and "Unsave" not in text
    watchlist_client.remove_from_watchlist.assert_awaited_once_with(MediaType.MOVIE, 438631)


async def test_save_and_unsave_failures_render_errors(logged_in, watchlist_client):
    watchlist_client.add_to_watchlist = AsyncMock(return_value=None)
    response = await logged_in.put("/partials/watchlist", data=_item().model_dump(mode="json"))
    assert response.status_code == 502 and "watchlist" in response.text.lower()
    watchlist_client.remove_from_watchlist = AsyncMock(return_value=False)
    response = await logged_in.delete("/partials/watchlist", params=_item().model_dump(mode="json"))
    assert response.status_code == 502


# --- follow picker ---


async def test_follow_picker_renders_start_scope_and_resolution(logged_in, watchlist_client):
    text = (await logged_in.get(FOLLOW_PATH, params=SHOW_FORM)).text
    watchlist_client.browse_show.assert_awaited_once_with(SHOW_ID)
    assert f'hx-put="{FOLLOW_PATH}"' in text
    for mode in ("new_only", "from", "beginning"):
        assert f'name="mode" value="{mode}"' in text
    assert 'name="mode" value="new_only" checked' in text
    assert '<option value="1" data-episodes="2">Season 1</option>' in text
    assert '<option value="2" data-episodes="1">Season 2</option>' in text
    # episode options up to the longest season; season 1 has two, so none is hidden
    assert 'name="episode"' in text and '<option value="2">2</option>' in text
    assert " hidden>" not in text and '<option value="3">3</option>' not in text
    assert '<option value="1080p" selected>1080p</option>' in text
    assert '<option value="4K">4K</option>' in text and '<option value="720p">720p</option>' in text
    assert 'name="view" value="inline"' in text
    assert 'name="tmdb_id" value="1396"' in text


async def test_follow_picker_page_view_targets_the_stage(logged_in, watchlist_client):
    text = (await logged_in.get(FOLLOW_PATH, params={**SHOW_FORM, "view": "page"})).text
    assert 'hx-target="#stage"' in text and 'name="view" value="page"' in text
    assert "replaceChildren()" in text


async def test_follow_picker_unreachable(logged_in, watchlist_client):
    watchlist_client.browse_show = AsyncMock(return_value=None)
    assert (await logged_in.get(FOLLOW_PATH, params=SHOW_FORM)).status_code == 502


async def test_follow_cancel_restores_the_actions(logged_in, watchlist_client):
    text = (await logged_in.get(f"{FOLLOW_PATH}/button", params=SHOW_FORM)).text
    assert f'hx-get="{FOLLOW_PATH}"' in text and 'hx-put="/partials/watchlist"' in text


async def test_follow_from_saves_first_then_posts_season_and_episode(logged_in, watchlist_client):
    form = {**SHOW_FORM, "mode": "from", "season": "2", "episode": "3", "resolution": "720p"}
    response = await logged_in.put(FOLLOW_PATH, data=form)
    assert response.status_code == 200
    watchlist_client.add_to_watchlist.assert_awaited_once_with(
        MediaType.SHOW,
        SHOW_ID,
        WatchlistAddRequest(
            title="Breaking Bad", year="2008", poster_path="/dune.jpg", overview="Desert planet."
        ),
    )
    watchlist_client.follow_show.assert_awaited_once_with(
        SHOW_ID,
        FollowRequest(
            start=FollowStart(mode=FollowStartMode.FROM, season=2, episode=3), resolution="720p"
        ),
    )
    assert FOLLOWING_LABEL in response.text and f">{UNFOLLOW_LABEL}<" in response.text
    assert f">{FOLLOW_LABEL}<" not in response.text


async def test_follow_new_only_posts_no_scope_and_skips_the_save_when_saved(
    logged_in, watchlist_client
):
    form = {
        **SHOW_FORM,
        "on_watchlist": "true",
        "watchlist_kind": "saved",
        "mode": "new_only",
        "season": "2",
        "episode": "3",
    }
    response = await logged_in.put(FOLLOW_PATH, data=form)
    assert response.status_code == 200
    watchlist_client.add_to_watchlist.assert_not_awaited()
    watchlist_client.follow_show.assert_awaited_once_with(
        SHOW_ID, FollowRequest(start=FollowStart(mode=FollowStartMode.NEW_ONLY), resolution="1080p")
    )


async def test_follow_beginning_posts_no_scope(logged_in, watchlist_client):
    form = {**SHOW_FORM, "mode": "beginning", "season": "1", "episode": "1"}
    await logged_in.put(FOLLOW_PATH, data=form)
    watchlist_client.follow_show.assert_awaited_once_with(
        SHOW_ID, FollowRequest(start=FollowStart(mode=FollowStartMode.BEGINNING))
    )


async def test_follow_from_without_a_scope_is_rejected(logged_in, watchlist_client):
    response = await logged_in.put(FOLLOW_PATH, data={**SHOW_FORM, "mode": "from"})
    assert response.status_code == 422
    watchlist_client.follow_show.assert_not_awaited()


async def test_follow_from_the_page_redirects_to_the_following_tab(logged_in, watchlist_client):
    form = {**SHOW_FORM, "mode": "new_only", "view": "page"}
    response = await logged_in.put(FOLLOW_PATH, data=form)
    assert response.status_code == 200
    assert response.headers["HX-Redirect"] == "/watchlist?kind=following"


async def test_follow_failures_render_errors(logged_in, watchlist_client):
    form = {**SHOW_FORM, "mode": "new_only"}
    watchlist_client.add_to_watchlist = AsyncMock(return_value=None)
    assert (await logged_in.put(FOLLOW_PATH, data=form)).status_code == 502
    watchlist_client.follow_show.assert_not_awaited()
    watchlist_client.add_to_watchlist = AsyncMock(return_value=_saved())
    watchlist_client.follow_show = AsyncMock(return_value=None)
    response = await logged_in.put(FOLLOW_PATH, data=form)
    assert response.status_code == 502 and "follow" in response.text.lower()


async def test_watchlist_requires_login(client):
    assert (await client.get("/watchlist")).status_code == 303
    assert (await client.put(FOLLOW_PATH, data={})).status_code == 303


# --- season packs ---

from medialab_contracts import SeasonFollowMode, SeasonFollowState  # noqa: E402

from medialab_web.constants import (  # noqa: E402
    EPISODE_BY_EPISODE_LABEL,
    PACK_NOT_FOUND_TEXT,
    RETRY_LONGER_LABEL,
    RETRY_SEEDERS_LABEL,
    RETRYING_PACK_LABEL,
    SEASON_PACK_LABEL,
)
from medialab_web.schemas.watchlist import FollowedShowView  # noqa: E402

DECISION_PATH = f"/partials/watchlist/{SHOW_ID}/seasons/1/decision"


def _followed_view(*states: SeasonFollowState) -> FollowedShowView:
    show = _show(
        on_watchlist=True,
        watchlist_kind=WatchlistKind.FOLLOWING,
        episodes=[_episode(1, 1, wanted=True), _episode(1, 2, wanted=True), _episode(2, 1)],
    )
    return FollowedShowView(**show.model_dump(), seasons_follow=list(states))


async def test_season_without_a_state_renders_no_pack_controls(logged_in, watchlist_client):
    watchlist_client.watchlist_episodes = AsyncMock(return_value=_followed_view())
    text = (await logged_in.get(f"/partials/watchlist/{SHOW_ID}/episodes")).text
    assert PACK_NOT_FOUND_TEXT not in text and SEASON_PACK_LABEL not in text
    assert "seasons/1/decision" not in text


async def test_not_found_season_offers_the_three_choices(logged_in, watchlist_client):
    watchlist_client.watchlist_episodes = AsyncMock(
        return_value=_followed_view(
            SeasonFollowState(season=1, mode=SeasonFollowMode.PACK_NOT_FOUND, attempts=1)
        )
    )
    text = (await logged_in.get(f"/partials/watchlist/{SHOW_ID}/episodes")).text
    assert PACK_NOT_FOUND_TEXT in text
    for label, mode in (
        (RETRY_LONGER_LABEL, "pack_retry_timeout"),
        (RETRY_SEEDERS_LABEL, "pack_retry_seeders"),
        (EPISODE_BY_EPISODE_LABEL, "episodes"),
    ):
        assert f">{label}<" in text, label
        assert f'hx-post="{DECISION_PATH}" hx-vals=\'{{"mode": "{mode}"}}\'' in text, mode
    assert text.count('hx-target="closest .episodes-slot"') >= 3
    assert "seasons/2/decision" not in text


async def test_pack_states_render_as_badges(logged_in, watchlist_client):
    watchlist_client.watchlist_episodes = AsyncMock(
        return_value=_followed_view(
            SeasonFollowState(season=1, mode=SeasonFollowMode.PACK, attempts=1, job_id="job-9"),
            SeasonFollowState(season=2, mode=SeasonFollowMode.PACK_RETRY_SEEDERS, attempts=1),
        )
    )
    text = (await logged_in.get(f"/partials/watchlist/{SHOW_ID}/episodes")).text
    assert f'href="/#job-job-9">{SEASON_PACK_LABEL}<' in text
    assert f">{RETRYING_PACK_LABEL}<" in text
    assert PACK_NOT_FOUND_TEXT not in text
    watchlist_client.watchlist_episodes = AsyncMock(
        return_value=_followed_view(
            SeasonFollowState(season=1, mode=SeasonFollowMode.EPISODES, attempts=2)
        )
    )
    text = (await logged_in.get(f"/partials/watchlist/{SHOW_ID}/episodes")).text
    assert f'class="badge pack">{EPISODE_BY_EPISODE_LABEL}<' in text


async def test_decision_posts_the_mode_and_re_renders_the_episodes(logged_in, watchlist_client):
    watchlist_client.decide_season = AsyncMock(
        return_value=SeasonFollowState(season=1, mode=SeasonFollowMode.EPISODES, attempts=1)
    )
    watchlist_client.watchlist_episodes = AsyncMock(
        return_value=_followed_view(
            SeasonFollowState(season=1, mode=SeasonFollowMode.EPISODES, attempts=1)
        )
    )
    response = await logged_in.post(DECISION_PATH, data={"mode": "episodes"})
    assert response.status_code == 200
    watchlist_client.decide_season.assert_awaited_once_with(SHOW_ID, 1, SeasonFollowMode.EPISODES)
    assert f">{EPISODE_BY_EPISODE_LABEL}<" in response.text
    watchlist_client.decide_season = AsyncMock(return_value=None)
    assert (await logged_in.post(DECISION_PATH, data={"mode": "episodes"})).status_code == 502
