"""Presentation helpers used by the templates."""

from datetime import datetime
from typing import Protocol

from markupsafe import Markup, escape
from medialab_contracts import (
    DiscoverItem,
    Episode,
    FollowStart,
    FollowStartMode,
    MediaType,
    PosterSize,
    poster_url,
)

from medialab_web.constants import (
    DATE_LENGTH,
    DATETIME_FORMAT,
    ETA_UNDER_A_MINUTE_TEXT,
    ETA_UNKNOWN_TEXT,
    FROM_BEGINNING_TEXT,
    HOME_PATH,
    JOB_ROW_ID_PREFIX,
    NEVER_TEXT,
    NEW_EPISODES_TEXT,
    RELEASE_NAME_SEPARATORS,
    SECONDS_PER_DAY,
    SECONDS_PER_HOUR,
    SECONDS_PER_MINUTE,
    SHORT_ID_LENGTH,
    SHOWS_PATH,
    STATUS_DONE,
    YOUTUBE_THUMBNAIL_URL_TEMPLATE,
)
from medialab_web.media import from_tmdb_media_type
from medialab_web.schemas.jobs import JobView


class _Titled(Protocol):
    """Anything with a TMDB id and a media type: a card, a search result, a job."""

    tmdb_id: int
    media_type: str | MediaType


_GB = 1024**3
_MB = 1024**2
_KB = 1024


def job_title(job: JobView) -> str:
    """``Title (Year)`` when resolved, else the release name."""
    if job.resolved_title:
        return (
            f"{job.resolved_title} ({job.resolved_year})"
            if job.resolved_year
            else job.resolved_title
        )
    return job.release_name


def short_date(iso: str) -> str:
    return iso[:DATE_LENGTH]


def format_size(num_bytes: int) -> str:
    if num_bytes >= _GB:
        return f"{num_bytes / _GB:.2f} GB"
    return f"{num_bytes / _MB:.0f} MB"


def format_speed(bytes_per_second: int) -> str:
    """``1.2 MB/s`` at or above a megabyte per second, else whole ``KB/s``."""
    if bytes_per_second >= _MB:
        return f"{bytes_per_second / _MB:.1f} MB/s"
    return f"{bytes_per_second / _KB:.0f} KB/s"


def format_eta(seconds: int | None) -> str:
    """``12m`` under an hour, ``3h 05m`` under a day, else ``2d 4h``; ``-`` when unknown."""
    if seconds is None:
        return ETA_UNKNOWN_TEXT
    if seconds < SECONDS_PER_MINUTE:
        return ETA_UNDER_A_MINUTE_TEXT
    if seconds < SECONDS_PER_HOUR:
        return f"{seconds // SECONDS_PER_MINUTE}m"
    if seconds < SECONDS_PER_DAY:
        hours, rest = divmod(seconds, SECONDS_PER_HOUR)
        return f"{hours}h {rest // SECONDS_PER_MINUTE:02d}m"
    days, rest = divmod(seconds, SECONDS_PER_DAY)
    return f"{days}d {rest // SECONDS_PER_HOUR}h"


def format_percent(fraction: float) -> str:
    return f"{fraction:.0%}"


def breakable(name: str) -> Markup:
    """Escaped ``name`` with a ``<wbr>`` after each separator so it wraps between tokens."""
    return Markup("").join(
        escape(char) + Markup("<wbr>") if char in RELEASE_NAME_SEPARATORS else escape(char)
        for char in name
    )


def poster_src(poster_path: str | None, size: PosterSize = PosterSize.GRID) -> str | None:
    return poster_url(poster_path, size)


def show_url(tmdb_id: int) -> str:
    return f"{SHOWS_PATH}/{tmdb_id}"


def browse_url(item: _Titled) -> str | None:
    """The show page for a show; None for a movie, so cards render no Browse link."""
    raw = item.media_type.value if isinstance(item.media_type, MediaType) else item.media_type
    if from_tmdb_media_type(raw) is MediaType.SHOW:
        return show_url(item.tmdb_id)
    return None


def job_url(job_id: str) -> str:
    """The jobs page, anchored at the row the jobs table renders for ``job_id``."""
    return f"{HOME_PATH}#{JOB_ROW_ID_PREFIX}{job_id}"


def short_id(job_id: str) -> str:
    """The leading characters of a job id, enough to tell rows apart in a link."""
    return job_id[:SHORT_ID_LENGTH]


def redo_vals(job: JobView) -> dict[str, object]:
    """``job`` as the hx-vals of its Redo button: the torrent step's query
    fields, with season and episode present only when the job has them, and
    ``failed`` when the job is flagged rather than done."""
    vals: dict[str, object] = {
        "tmdb_id": job.tmdb_id,
        "title": job.resolved_title or job.release_name,
        "year": str(job.resolved_year) if job.resolved_year else "",
        "media_type": job.media_type.value,
    }
    if job.season is not None:
        vals["season"] = job.season
    if job.episode is not None:
        vals["episode"] = job.episode
    if job.status != STATUS_DONE:
        vals["failed"] = 1
    return vals


def episode_code(episode: Episode) -> str:
    return scope_code(episode.season, episode.episode)


def scope_code(season: int, episode: int) -> str:
    return f"S{season:02d}E{episode:02d}"


def follow_start_text(start: FollowStart) -> str:
    """The start point of a follow as a card reads it: ``New episodes``,
    ``From S02E03`` or ``From the beginning``."""
    if (
        start.mode is FollowStartMode.FROM
        and start.season is not None
        and start.episode is not None
    ):
        return f"From {scope_code(start.season, start.episode)}"
    if start.mode is FollowStartMode.BEGINNING:
        return FROM_BEGINNING_TEXT
    return NEW_EPISODES_TEXT


def when(moment: datetime | None) -> str:
    """A timestamp to the minute, or ``never``."""
    return moment.strftime(DATETIME_FORMAT) if moment else NEVER_TEXT


def card_vals(item: DiscoverItem) -> dict[str, object]:
    """``item`` as hx-vals: a missing value is sent as an empty string, since
    htmx would otherwise send the literal text ``null``."""
    return {k: "" if v is None else v for k, v in item.model_dump(mode="json").items()}


def youtube_thumbnail_url(key: str) -> str:
    """The medium thumbnail of a YouTube video, from the keyless image host."""
    return YOUTUBE_THUMBNAIL_URL_TEMPLATE.format(key=key)
