"""One shared password, one signed cookie."""

import secrets

from fastapi import HTTPException, Request, status
from itsdangerous import BadSignature, SignatureExpired, TimestampSigner

from medialab_web.config import AppConfig
from medialab_web.constants import LOGIN_PATH, SESSION_COOKIE_NAME, SESSION_VALUE


class ConfigError(RuntimeError):
    """Raised at startup when a required secret is missing."""


def check_startup_config(cfg: AppConfig) -> None:
    if not cfg.web_password:
        raise ConfigError("WEB_PASSWORD is not set; refusing to serve an unprotected page.")
    if not cfg.web_secret_key:
        raise ConfigError("WEB_SECRET_KEY is not set; sessions cannot be signed.")


def password_matches(cfg: AppConfig, candidate: str) -> bool:
    return bool(cfg.web_password) and secrets.compare_digest(
        candidate.encode(), (cfg.web_password or "").encode()
    )


def _signer(cfg: AppConfig) -> TimestampSigner:
    return TimestampSigner(cfg.web_secret_key or "")


def issue_session(cfg: AppConfig) -> str:
    return _signer(cfg).sign(SESSION_VALUE).decode()


def session_is_valid(cfg: AppConfig, token: str | None) -> bool:
    if not token or not cfg.web_secret_key:
        return False
    try:
        value = _signer(cfg).unsign(token, max_age=cfg.session_max_age_seconds)
    except (BadSignature, SignatureExpired):
        return False
    return value == SESSION_VALUE.encode()


class LoginRequired(HTTPException):
    """Turned into a redirect to the login page by the app's handler."""

    def __init__(self) -> None:
        super().__init__(status_code=status.HTTP_303_SEE_OTHER, headers={"Location": LOGIN_PATH})
        self.location = LOGIN_PATH


def require_session(request: Request) -> None:
    cfg: AppConfig = request.app.state.config
    if not session_is_valid(cfg, request.cookies.get(SESSION_COOKIE_NAME)):
        raise LoginRequired()
