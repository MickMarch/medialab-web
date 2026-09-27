"""Presentation helpers used by the templates."""

from typing import Protocol

from markupsafe import Markup, escape
from medialab_contracts import DiscoverItem, Episode, MediaType, PosterSize, poster_url

from medialab_web.constants import (
    DATE_LENGTH,
    ETA_UNDER_A_MINUTE_TEXT,
    ETA_UNKNOWN_TEXT,
    HOME_PATH,
    JOB_ROW_ID_PREFIX,
    RELEASE_NAME_SEPARATORS,
    SECONDS_PER_DAY,
    SECONDS_PER_HOUR,
    SECONDS_PER_MINUTE,
    SHORT_ID_LENGTH,
    SHOWS_PATH,
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
    fields, with season and episode present only when the job has them."""
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
    return vals


def episode_code(episode: Episode) -> str:
    return f"S{episode.season:02d}E{episode.episode:02d}"


def card_vals(item: DiscoverItem) -> dict[str, object]:
    """``item`` as hx-vals: a missing value is sent as an empty string, since
    htmx would otherwise send the literal text ``null``."""
    return {k: "" if v is None else v for k, v in item.model_dump(mode="json").items()}
