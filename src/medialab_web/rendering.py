"""Jinja2 environment and the one render helper every route uses."""

from pathlib import Path
from typing import Any

from fastapi import Request, status
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from medialab_web import format as fmt
from medialab_web.constants import (
    JOBS_REFRESH_SECONDS,
    MEDIA_TYPE_LABELS,
    NAV_LINKS,
    TMDB_ATTRIBUTION,
    WHOLE_SERIES,
)

TEMPLATES_DIR = Path(__file__).parent / "templates"
STATIC_DIR = Path(__file__).parent / "static"

templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
templates.env.filters["job_title"] = fmt.job_title
templates.env.filters["short_date"] = fmt.short_date
templates.env.filters["format_size"] = fmt.format_size
templates.env.filters["breakable"] = fmt.breakable
templates.env.filters["poster_url"] = fmt.poster_src
templates.env.filters["card_vals"] = fmt.card_vals
templates.env.globals["jobs_refresh_seconds"] = JOBS_REFRESH_SECONDS
templates.env.globals["whole_series"] = WHOLE_SERIES
templates.env.globals["nav_links"] = NAV_LINKS
templates.env.globals["media_type_labels"] = MEDIA_TYPE_LABELS
templates.env.globals["tmdb_attribution"] = TMDB_ATTRIBUTION


def render(
    request: Request,
    name: str,
    context: dict[str, Any],
    status_code: int = status.HTTP_200_OK,
) -> HTMLResponse:
    return templates.TemplateResponse(request, name, context, status_code=status_code)
