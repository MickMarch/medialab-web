"""The searching bar polls real progress for the search in flight."""

from unittest.mock import AsyncMock, patch

import pytest
from medialab_contracts import MediaType, TorrentSearchProgress

from medialab_web.client import OrchestratorClient
from medialab_web.constants import (
    SEARCH_PROGRESS_ATTR,
    SEARCH_PROGRESS_PARTIAL_PATH,
    SEARCHING_FALLBACK_TEXT,
)
from tests.test_client import API_KEY, BASE_URL, _mock_response

_PARAMS = {"title": "The Wire", "year": "2002", "media_type": "show", "season": "2", "query": ""}


def _progress(**kw) -> TorrentSearchProgress:
    base = {
        "state": "running",
        "patterns_total": 3,
        "patterns_done": 1,
        "results_so_far": 57,
        "elapsed_seconds": 5.0,
        "timeout_seconds": 15,
    }
    return TorrentSearchProgress(**{**base, **kw})


# --- client ---


@pytest.mark.asyncio
async def test_client_sends_the_search_parameters_and_parses_the_model():
    client = OrchestratorClient(base_url=BASE_URL, api_key=API_KEY)
    payload = _progress().model_dump(mode="json")
    mock_get = AsyncMock(return_value=_mock_response(200, payload))
    with patch.object(client._http, "get", new=mock_get):
        result = await client.search_progress(
            "The Wire", MediaType.SHOW, season=2, episode=None, alt_query="wire"
        )
    assert isinstance(result, TorrentSearchProgress)
    assert mock_get.call_args.args[0].endswith("/search/torrents/progress")
    params = mock_get.call_args.kwargs["params"]
    assert params == {"query": "The Wire", "media_type": "show", "season": 2, "alt_query": "wire"}


@pytest.mark.asyncio
async def test_client_returns_none_on_failure():
    client = OrchestratorClient(base_url=BASE_URL, api_key=API_KEY)
    with patch.object(client._http, "get", new=AsyncMock(return_value=_mock_response(503))):
        assert await client.search_progress("x", MediaType.MOVIE) is None


# --- the progress partial ---


async def test_progress_partial_renders_counts_and_a_live_width(logged_in, mock_client):
    mock_client.search_progress = AsyncMock(return_value=_progress())
    text = (await logged_in.get(SEARCH_PROGRESS_PARTIAL_PATH, params=_PARAMS)).text
    assert "1 of 3 patterns done" in text
    assert "57 results so far" in text
    # (1 + 5/15) / 3 = 44%
    assert 'style="width: 44%"' in text
    assert "live" in text


async def test_progress_partial_asks_for_the_same_search_as_the_torrents_step(
    logged_in, mock_client
):
    mock_client.search_progress = AsyncMock(return_value=_progress())
    await logged_in.get(SEARCH_PROGRESS_PARTIAL_PATH, params={**_PARAMS, "query": "the wire"})
    mock_client.search_progress.assert_awaited_once_with(
        "The Wire", MediaType.SHOW, season=2, episode=None, alt_query="the wire"
    )


async def test_idle_progress_keeps_the_fallback_text(logged_in, mock_client):
    mock_client.search_progress = AsyncMock(
        return_value=_progress(state="idle", patterns_done=0, results_so_far=0, elapsed_seconds=0)
    )
    text = (await logged_in.get(SEARCH_PROGRESS_PARTIAL_PATH, params=_PARAMS)).text
    assert SEARCHING_FALLBACK_TEXT in text
    assert "live" not in text


async def test_done_progress_fills_the_bar(logged_in, mock_client):
    mock_client.search_progress = AsyncMock(
        return_value=_progress(state="done", patterns_done=3, results_so_far=80)
    )
    text = (await logged_in.get(SEARCH_PROGRESS_PARTIAL_PATH, params=_PARAMS)).text
    assert 'style="width: 100%"' in text
    assert "80 results" in text


async def test_gateway_failure_keeps_the_fallback_text(logged_in, mock_client):
    mock_client.search_progress = AsyncMock(return_value=None)
    response = await logged_in.get(SEARCH_PROGRESS_PARTIAL_PATH, params=_PARAMS)
    assert response.status_code == 200
    assert SEARCHING_FALLBACK_TEXT in response.text


# --- the bar and the listener ---


async def test_searching_bar_polls_only_while_shown(logged_in):
    page = (await logged_in.get("/")).text
    assert f'hx-get="{SEARCH_PROGRESS_PARTIAL_PATH}"' in page
    assert "every 1s [" in page and "htmx-request" in page
    assert SEARCH_PROGRESS_ATTR in page


async def test_base_page_carries_the_search_parameter_listener(logged_in):
    page = (await logged_in.get("/")).text
    assert "htmx:configRequest" in page
    assert SEARCH_PROGRESS_ATTR in page
