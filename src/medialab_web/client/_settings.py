from medialab_contracts import API_PREFIX, SettingView, SuiteSettingsResponse

from medialab_web.client._base import _BaseClient


class _SettingsMixin(_BaseClient):
    async def get_settings(self) -> SuiteSettingsResponse | None:
        data = await self._get(f"{API_PREFIX}/settings")
        return self._parse(SuiteSettingsResponse, data)

    async def set_setting(self, service: str, key: str, value: str) -> SettingView | None:
        # The gateway validates against the service's registry; a refused
        # value comes back as a non-200 and parses to None.
        data = await self._put(f"{API_PREFIX}/settings/{service}/{key}", json={"value": value})
        return self._parse(SettingView, data)

    async def reset_setting(self, service: str, key: str) -> SettingView | None:
        data = await self._delete(f"{API_PREFIX}/settings/{service}/{key}")
        return self._parse(SettingView, data)
