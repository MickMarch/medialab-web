"""Presentation helpers used by the templates."""

from markupsafe import Markup, escape
from medialab_contracts import DiscoverItem, PosterSize, poster_url

from medialab_web.constants import (
    DATE_LENGTH,
    ETA_UNDER_A_MINUTE_TEXT,
    ETA_UNKNOWN_TEXT,
    RELEASE_NAME_SEPARATORS,
    SECONDS_PER_DAY,
    SECONDS_PER_HOUR,
    SECONDS_PER_MINUTE,
)
from medialab_web.schemas.jobs import JobView

_GB = 1024**3
_MB = 1024**2


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


def card_vals(item: DiscoverItem) -> dict[str, object]:
    """``item`` as hx-vals: a missing value is sent as an empty string, since
    htmx would otherwise send the literal text ``null``."""
    return {k: "" if v is None else v for k, v in item.model_dump(mode="json").items()}
