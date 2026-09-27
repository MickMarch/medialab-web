"""Jinja2 environment and the one render helper every route uses."""

from pathlib import Path
from typing import Any

from fastapi import Request, status
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from medialab_contracts import (
    FollowStartMode,
    MediaType,
    SubmissionState,
    WatchlistKind,
    still_url,
    youtube_embed_url,
)

from medialab_web import format as fmt
from medialab_web.constants import (
    BROWSE_LABEL,
    CANCEL_LABEL,
    CHECK_NOW_LABEL,
    DEFAULT_RESOLUTION,
    DISCOVER_PATH,
    EPISODES_LABEL,
    EPISODES_SLOT_CLASS,
    FIND_TORRENTS_LABEL,
    FOLLOW_BUTTON_PARTIAL_PATH,
    FOLLOW_LABEL,
    FOLLOW_NOTICE_CLASS,
    FOLLOW_PARTIAL_PATH,
    FOLLOW_RESOLUTIONS,
    FOLLOW_START_LABELS,
    FOLLOWING_LABEL,
    IGNORED_LABEL,
    IN_LIBRARY_LABEL,
    JOB_ROW_ID_PREFIX,
    JOBS_POLL_ELEMENT_ID,
    JOBS_REFRESH_SECONDS,
    MEDIA_TYPE_LABELS,
    NAV_LINKS,
    NEVER_TEXT,
    OFFICIAL_LABEL,
    PAUSE_LABEL,
    PAUSED_LABEL,
    QUEUED_LABEL,
    REDO_LABEL,
    REDO_NOTICE,
    RESUME_LABEL,
    RETRY_LABEL,
    SAVE_LABEL,
    SAVED_LABEL,
    STATUS_DONE,
    SUBMITTED_LABEL,
    TMDB_ATTRIBUTION,
    TRAILER_CLOSE_LABEL,
    TRAILER_PLAY_PATH,
    TRAILER_SLOT_CLASS,
    TRAILERS_PARTIAL_PATH,
    UNAIRED_LABEL,
    UNFOLLOW_LABEL,
    UNSAVE_LABEL,
    WANTED_LABEL,
    WATCH_TRAILER_LABEL,
    WATCHLIST_ACTIONS_CLASS,
    WATCHLIST_KIND_LABELS,
    WATCHLIST_PARTIAL_PATH,
    WATCHLIST_PATH,
    WHOLE_SERIES,
)
from medialab_web.schemas.discover import CardItem
from medialab_web.schemas.watchlist import FollowView

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
templates.env.filters["follow_start"] = fmt.follow_start_text
templates.env.filters["when"] = fmt.when
templates.env.filters["watchlist_card"] = CardItem.from_watchlist
templates.env.globals["jobs_refresh_seconds"] = JOBS_REFRESH_SECONDS
templates.env.globals["jobs_poll_id"] = JOBS_POLL_ELEMENT_ID
templates.env.globals["job_row_id_prefix"] = JOB_ROW_ID_PREFIX
templates.env.globals["in_library_label"] = IN_LIBRARY_LABEL
templates.env.globals["watchlist_kind_labels"] = WATCHLIST_KIND_LABELS
templates.env.globals["saved_label"] = SAVED_LABEL
templates.env.globals["following_label"] = FOLLOWING_LABEL
templates.env.globals["never_text"] = NEVER_TEXT
templates.env.globals["watchlist_kinds"] = list(WatchlistKind)
templates.env.globals["kind_following"] = WatchlistKind.FOLLOWING
templates.env.globals["view_inline"] = FollowView.INLINE.value
templates.env.globals["view_page"] = FollowView.PAGE.value
templates.env.globals["submission_submitted"] = SubmissionState.SUBMITTED
templates.env.globals["submission_ignored"] = SubmissionState.IGNORED
templates.env.globals["watchlist_path"] = WATCHLIST_PATH
templates.env.globals["watchlist_partial_path"] = WATCHLIST_PARTIAL_PATH
templates.env.globals["follow_partial_path"] = FOLLOW_PARTIAL_PATH
templates.env.globals["follow_button_partial_path"] = FOLLOW_BUTTON_PARTIAL_PATH
templates.env.globals["watchlist_actions_class"] = WATCHLIST_ACTIONS_CLASS
templates.env.globals["episodes_slot_class"] = EPISODES_SLOT_CLASS
templates.env.globals["follow_notice_class"] = FOLLOW_NOTICE_CLASS
templates.env.globals["save_label"] = SAVE_LABEL
templates.env.globals["unsave_label"] = UNSAVE_LABEL
templates.env.globals["follow_label"] = FOLLOW_LABEL
templates.env.globals["unfollow_label"] = UNFOLLOW_LABEL
templates.env.globals["pause_label"] = PAUSE_LABEL
templates.env.globals["resume_label"] = RESUME_LABEL
templates.env.globals["paused_label"] = PAUSED_LABEL
templates.env.globals["check_now_label"] = CHECK_NOW_LABEL
templates.env.globals["episodes_label"] = EPISODES_LABEL
templates.env.globals["retry_label"] = RETRY_LABEL
templates.env.globals["cancel_label"] = CANCEL_LABEL
templates.env.globals["submitted_label"] = SUBMITTED_LABEL
templates.env.globals["ignored_label"] = IGNORED_LABEL
templates.env.globals["wanted_label"] = WANTED_LABEL
templates.env.globals["follow_start_labels"] = FOLLOW_START_LABELS
templates.env.globals["follow_start_modes"] = list(FollowStartMode)
templates.env.globals["start_mode_from"] = FollowStartMode.FROM
templates.env.globals["follow_resolutions"] = FOLLOW_RESOLUTIONS
templates.env.globals["default_resolution"] = DEFAULT_RESOLUTION
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
templates.env.globals["youtube_embed_url"] = youtube_embed_url
templates.env.globals["trailers_path"] = TRAILERS_PARTIAL_PATH
templates.env.globals["trailer_play_path"] = TRAILER_PLAY_PATH
templates.env.globals["trailer_slot_class"] = TRAILER_SLOT_CLASS
templates.env.globals["watch_trailer_label"] = WATCH_TRAILER_LABEL
templates.env.globals["trailer_close_label"] = TRAILER_CLOSE_LABEL
templates.env.globals["official_label"] = OFFICIAL_LABEL


def render(
    request: Request,
    name: str,
    context: dict[str, Any],
    status_code: int = status.HTTP_200_OK,
) -> HTMLResponse:
    return templates.TemplateResponse(request, name, context, status_code=status_code)
