from unittest.mock import AsyncMock

from medialab_contracts import SettingView, SuiteSettingsResponse


def _view(key="minimum_seeders", value=10, source="default", **kw) -> SettingView:
    base = {
        "key": key,
        "value": value,
        "default": 10,
        "source": source,
        "type": "int",
        "description": "Releases with fewer seeders are dropped.",
        "applies": "next search",
        "min": 0,
        "max": 1000,
    }
    return SettingView(**{**base, **kw})


def _suite() -> SuiteSettingsResponse:
    return SuiteSettingsResponse(
        status="success",
        services={
            "torrent-downloader": [
                _view(),
                _view(
                    key="audio_language_filter",
                    value="lenient",
                    type="choice",
                    choices=["lenient", "strict", "off"],
                    default="lenient",
                    min=None,
                    max=None,
                ),
            ],
            "medialab-orchestrator": [_view(key="auto_retry_max", value=4, source="override")],
        },
    )


async def test_settings_page_renders_a_row_per_setting_with_the_right_control(
    logged_in, mock_client
):
    mock_client.get_settings = AsyncMock(return_value=_suite())
    text = (await logged_in.get("/settings")).text
    assert 'id="setting-torrent-downloader-minimum_seeders"' in text
    assert 'type="number" name="value" value="10" min="0" max="1000"' in text
    assert '<select name="value">' in text and 'value="strict"' in text
    assert 'id="setting-medialab-orchestrator-auto_retry_max"' in text
    # only an override offers Reset
    assert text.count("Reset</button>") == 1
    assert 'hx-delete="/settings/medialab-orchestrator/auto_retry_max"' in text


async def test_settings_page_gateway_down(logged_in, mock_client):
    mock_client.get_settings = AsyncMock(return_value=None)
    text = (await logged_in.get("/settings")).text
    assert "Could not load settings" in text


async def test_save_swaps_the_row(logged_in, mock_client):
    mock_client.set_setting = AsyncMock(return_value=_view(value=3, source="override"))
    response = await logged_in.put(
        "/settings/torrent-downloader/minimum_seeders", data={"value": "3"}
    )
    assert response.status_code == 200
    assert 'value="3"' in response.text and "Saved." in response.text
    mock_client.set_setting.assert_awaited_once_with("torrent-downloader", "minimum_seeders", "3")


async def test_refused_value_shows_inline_error(logged_in, mock_client):
    mock_client.set_setting = AsyncMock(return_value=None)
    response = await logged_in.put(
        "/settings/torrent-downloader/minimum_seeders", data={"value": "5000"}
    )
    assert response.status_code == 422
    assert "value refused" in response.text


async def test_reset_calls_delete_and_swaps(logged_in, mock_client):
    mock_client.reset_setting = AsyncMock(return_value=_view(value=10, source="default"))
    response = await logged_in.delete("/settings/torrent-downloader/minimum_seeders")
    assert response.status_code == 200
    assert "Reset." in response.text and "Reset</button>" not in response.text
    mock_client.reset_setting.assert_awaited_once_with("torrent-downloader", "minimum_seeders")


async def test_settings_requires_login(client):
    assert (await client.get("/settings")).status_code == 303
