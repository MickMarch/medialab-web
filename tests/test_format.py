from medialab_web.format import breakable, format_size, job_title, short_date
from tests.conftest import make_job


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
