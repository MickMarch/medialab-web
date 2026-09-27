from medialab_contracts import MediaType

from medialab_web.constants import SHORT_ID_LENGTH
from medialab_web.format import (
    breakable,
    format_eta,
    format_percent,
    format_size,
    format_speed,
    job_title,
    redo_vals,
    short_date,
    short_id,
)
from tests.conftest import make_job


def test_short_id_truncates():
    assert short_id("0123456789abcdef") == "0123456789abcdef"[:SHORT_ID_LENGTH]
    assert short_id("abc") == "abc"


def test_redo_vals_carries_the_scope_only_when_set():
    assert redo_vals(make_job()) == {
        "tmdb_id": 1,
        "title": "Dune",
        "year": "2021",
        "media_type": "movie",
    }
    episode = redo_vals(make_job(media_type=MediaType.SHOW, tmdb_id=2, season=2, episode=5))
    assert episode["season"] == 2 and episode["episode"] == 5
    assert "episode" not in redo_vals(make_job(season=2))
    unresolved = redo_vals(make_job(resolved_title=None, resolved_year=None))
    assert unresolved["title"] == "Dune.2021.1080p.PORTUGUESE.DUAL-GRP"
    assert unresolved["year"] == ""


def test_job_title_variants():
    assert job_title(make_job()) == "Dune (2021)"
    assert job_title(make_job(resolved_year=None)) == "Dune"
    assert job_title(make_job(resolved_title=None, resolved_year=None)) == (
        "Dune.2021.1080p.PORTUGUESE.DUAL-GRP"
    )


def test_short_date():
    assert short_date("2026-06-26T00:00:00+00:00") == "2026-06-26"


def test_format_size():
    assert format_size(3 * 1024**3) == "3.00 GB"
    assert format_size(500 * 1024**2) == "500 MB"


def test_breakable_offers_a_break_after_each_separator():
    assert str(breakable("Dune.2021_1080p-GRP")) == "Dune.<wbr>2021_<wbr>1080p-<wbr>GRP"


def test_breakable_escapes_before_marking_up():
    assert str(breakable("<b>.x")) == "&lt;b&gt;.<wbr>x"


def test_format_eta_under_a_minute():
    assert format_eta(0) == "<1m"
    assert format_eta(59) == "<1m"


def test_format_eta_minutes():
    assert format_eta(60) == "1m"
    assert format_eta(12 * 60 + 30) == "12m"
    assert format_eta(3599) == "59m"


def test_format_eta_hours_pad_minutes():
    assert format_eta(3600) == "1h 00m"
    assert format_eta(3 * 3600 + 5 * 60) == "3h 05m"
    assert format_eta(86399) == "23h 59m"


def test_format_eta_days():
    assert format_eta(86400) == "1d 0h"
    assert format_eta(2 * 86400 + 4 * 3600 + 59 * 60) == "2d 4h"


def test_format_eta_unknown():
    assert format_eta(None) == "-"


def test_format_percent():
    assert format_percent(0.42) == "42%"
    assert format_percent(0.0) == "0%"
    assert format_percent(1.0) == "100%"


def test_format_speed():
    assert format_speed(0) == "0 KB/s"
    assert format_speed(640 * 1024) == "640 KB/s"
    assert format_speed(1024**2) == "1.0 MB/s"
    assert format_speed(int(1.25 * 1024**2)) == "1.2 MB/s"
    assert format_speed(3 * 1024**2) == "3.0 MB/s"
