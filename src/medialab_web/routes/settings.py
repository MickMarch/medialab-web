"""Settings page: one row per setting, save and reset per row."""

from fastapi import APIRouter, Depends, Form, Request, status
from fastapi.responses import HTMLResponse

from medialab_web.auth import require_session
from medialab_web.client import OrchestratorClient
from medialab_web.constants import SETTINGS_PATH
from medialab_web.deps import get_client
from medialab_web.rendering import render

router = APIRouter(dependencies=[Depends(require_session)])

_CLIENT = Depends(get_client)
_VALUE_FORM = Form(...)
_ERROR_FRAGMENT = "partials/error.html"
_ROW_FRAGMENT = "partials/setting_row.html"


@router.get(SETTINGS_PATH, response_class=HTMLResponse)
async def settings_page(request: Request, client: OrchestratorClient = _CLIENT) -> HTMLResponse:
    suite = await client.get_settings()
    return render(request, "settings.html", {"services": suite.services if suite else None})


@router.put("/settings/{service}/{key}", response_class=HTMLResponse)
async def save_setting(
    request: Request,
    service: str,
    key: str,
    value: str = _VALUE_FORM,
    client: OrchestratorClient = _CLIENT,
) -> HTMLResponse:
    view = await client.set_setting(service, key, value)
    if view is None:
        return render(
            request,
            _ERROR_FRAGMENT,
            {"message": f"{key}: value refused (out of bounds, wrong type, or gateway down)."},
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        )
    return render(request, _ROW_FRAGMENT, {"service": service, "s": view, "notice": "Saved."})


@router.delete("/settings/{service}/{key}", response_class=HTMLResponse)
async def reset_setting(
    request: Request, service: str, key: str, client: OrchestratorClient = _CLIENT
) -> HTMLResponse:
    view = await client.reset_setting(service, key)
    if view is None:
        return render(
            request,
            _ERROR_FRAGMENT,
            {"message": f"{key}: reset failed."},
            status_code=status.HTTP_502_BAD_GATEWAY,
        )
    return render(request, _ROW_FRAGMENT, {"service": service, "s": view, "notice": "Reset."})
