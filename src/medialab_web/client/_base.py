import logging
from typing import Self, TypeVar

import httpx
from medialab_contracts import API_KEY_HEADER
from pydantic import BaseModel, ValidationError

logger = logging.getLogger(__name__)

ModelT = TypeVar("ModelT", bound=BaseModel)


class _BaseClient:
    def __init__(
        self,
        base_url: str,
        api_key: str,
        torrent_search_timeout: float = 30.0,
    ) -> None:
        self._http = httpx.AsyncClient(
            base_url=base_url,
            headers={API_KEY_HEADER: api_key},
        )
        self._torrent_search_timeout = torrent_search_timeout

    async def _get(
        self, path: str, params: dict | None = None, timeout: float | None = None
    ) -> dict | None:
        try:
            response = await self._http.get(path, params=params or {}, timeout=timeout)
            if response.status_code != httpx.codes.OK:
                logger.warning("GET %s returned %d", path, response.status_code)
                return None
            return response.json()
        except httpx.TimeoutException:
            logger.warning("GET %s timed out", path)
            return None
        except (httpx.ConnectError, httpx.HTTPError):
            logger.warning("GET %s failed with network error", path)
            return None
        except ValueError:
            logger.error("GET %s returned non-JSON response", path)
            return None

    async def _post(
        self,
        path: str,
        json: dict | None = None,
        expected_status: int = 200,
        timeout: float | None = None,
    ) -> dict | None:
        try:
            response = await self._http.post(path, json=json or {}, timeout=timeout)
            if response.status_code != expected_status:
                logger.warning("POST %s returned %d", path, response.status_code)
                return None
            return response.json()
        except httpx.TimeoutException:
            logger.warning("POST %s timed out", path)
            return None
        except (httpx.ConnectError, httpx.HTTPError):
            logger.warning("POST %s failed with network error", path)
            return None
        except ValueError:
            logger.error("POST %s returned non-JSON response", path)
            return None

    async def _delete(self, path: str, timeout: float | None = None) -> dict | None:
        try:
            response = await self._http.delete(path, timeout=timeout)
            if response.status_code != httpx.codes.OK:
                logger.warning("DELETE %s returned %d", path, response.status_code)
                return None
            return response.json()
        except httpx.TimeoutException:
            logger.warning("DELETE %s timed out", path)
            return None
        except (httpx.ConnectError, httpx.HTTPError):
            logger.warning("DELETE %s failed with network error", path)
            return None
        except ValueError:
            logger.error("DELETE %s returned non-JSON response", path)
            return None

    @staticmethod
    def _parse(model: type[ModelT], data: dict | None) -> ModelT | None:
        if data is None:
            return None
        try:
            return model.model_validate(data)
        except (ValidationError, TypeError) as exc:
            logger.error("Failed to parse %s: %s", model.__name__, exc)
            return None

    async def close(self) -> None:
        await self._http.aclose()

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, *_) -> None:
        await self.close()
