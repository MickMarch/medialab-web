"""Presentation helpers used by the templates."""

from markupsafe import Markup, escape

from medialab_web.constants import DATE_LENGTH, RELEASE_NAME_SEPARATORS
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


def breakable(name: str) -> Markup:
    """Escaped ``name`` with a ``<wbr>`` after each separator so it wraps between tokens."""
    return Markup("").join(
        escape(char) + Markup("<wbr>") if char in RELEASE_NAME_SEPARATORS else escape(char)
        for char in name
    )
