"""Jinja2 environment and the one render helper every route uses."""

from pathlib import Path
from typing import Any

from fastapi import Request, status
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from medialab_contracts import MediaType, still_url

from medialab_web import format as fmt
from medialab_web.constants import (
    BROWSE_LABEL,
    DISCOVER_PATH,
    FIND_TORRENTS_LABEL,
    IN_LIBRARY_LABEL,
    JOB_ROW_ID_PREFIX,
    JOBS_POLL_ELEMENT_ID,
    JOBS_REFRESH_SECONDS,
    MEDIA_TYPE_LABELS,
    NAV_LINKS,
    QUEUED_LABEL,
    REDO_LABEL,
    REDO_NOTICE,
    STATUS_DONE,
    TMDB_ATTRIBUTION,
    UNAIRED_LABEL,
    WHOLE_SERIES,
    WISHLISTED_LABEL,
)

TEMPLATES_DIR = Path(__file__).parent / "templates"
STATIC_DIR = Path(__file__).parent / "static"

templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
templates.env.filters["job_title"] = fmt.job_title
templates.env.filters["short_date"] = fmt.short_date
templates.env.filters["format_size"] = fmt.format_size
templates.env.filters["format_speed"] = fmt.format_speed
templates.env.filters["format_eta"] = fmt.format_eta
templates.env.filters["percent"] = fmt.format_percent
templates.env.filters["breakable"] = fmt.breakable
templates.env.filters["poster_url"] = fmt.poster_src
templates.env.filters["card_vals"] = fmt.card_vals
templates.env.filters["still_url"] = still_url
templates.env.filters["show_url"] = fmt.show_url
templates.env.filters["browse_url"] = fmt.browse_url
templates.env.filters["job_url"] = fmt.job_url
templates.env.filters["episode_code"] = fmt.episode_code
templates.env.filters["short_id"] = fmt.short_id
templates.env.filters["redo_vals"] = fmt.redo_vals
templates.env.globals["jobs_refresh_seconds"] = JOBS_REFRESH_SECONDS
templates.env.globals["jobs_poll_id"] = JOBS_POLL_ELEMENT_ID
templates.env.globals["job_row_id_prefix"] = JOB_ROW_ID_PREFIX
templates.env.globals["in_library_label"] = IN_LIBRARY_LABEL
templates.env.globals["wishlisted_label"] = WISHLISTED_LABEL
templates.env.globals["queued_label"] = QUEUED_LABEL
templates.env.globals["unaired_label"] = UNAIRED_LABEL
templates.env.globals["browse_label"] = BROWSE_LABEL
templates.env.globals["find_torrents_label"] = FIND_TORRENTS_LABEL
templates.env.globals["redo_label"] = REDO_LABEL
templates.env.globals["redo_notice"] = REDO_NOTICE
templates.env.globals["status_done"] = STATUS_DONE
templates.env.globals["media_type_show"] = MediaType.SHOW
templates.env.globals["discover_path"] = DISCOVER_PATH
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
