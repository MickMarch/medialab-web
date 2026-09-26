"""Full pages: login, logout, and the jobs page shell."""

from fastapi import APIRouter, Depends, Form, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse

from medialab_web.auth import issue_session, password_matches, require_session
from medialab_web.constants import HOME_PATH, LOGIN_PATH, SESSION_COOKIE_NAME
from medialab_web.limiter import LOGIN_RATE_LIMIT, limiter
from medialab_web.rendering import render

router = APIRouter()

_PASSWORD_FORM = Form(...)


@router.get(LOGIN_PATH, response_class=HTMLResponse)
async def login_form(request: Request) -> HTMLResponse:
    return render(request, "login.html", {"error": None})


@router.post(LOGIN_PATH, response_model=None)
@limiter.limit(LOGIN_RATE_LIMIT)
async def login(
    request: Request, password: str = _PASSWORD_FORM
) -> HTMLResponse | RedirectResponse:
    cfg = request.app.state.config
    if not password_matches(cfg, password):
        return render(
            request,
            "login.html",
            {"error": "Wrong password."},
            status_code=status.HTTP_401_UNAUTHORIZED,
        )
    response = RedirectResponse(HOME_PATH, status_code=status.HTTP_303_SEE_OTHER)
    response.set_cookie(
        SESSION_COOKIE_NAME,
        issue_session(cfg),
        max_age=cfg.session_max_age_seconds,
        httponly=True,
        samesite="lax",
    )
    return response


@router.post("/logout")
async def logout() -> RedirectResponse:
    response = RedirectResponse(LOGIN_PATH, status_code=status.HTTP_303_SEE_OTHER)
    response.delete_cookie(SESSION_COOKIE_NAME)
    return response


@router.get(HOME_PATH, response_class=HTMLResponse, dependencies=[Depends(require_session)])
async def index(request: Request, status_filter: str | None = None) -> HTMLResponse:
    # The shell only; the table and storage panel load themselves via HTMX so
    # a slow gateway never blocks the page.
    return render(request, "index.html", {"status_filter": status_filter or ""})
