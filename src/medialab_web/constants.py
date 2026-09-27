"""Named values shared across the web UI."""

from medialab_contracts import MediaType

SESSION_COOKIE_NAME = "medialab_session"
SESSION_VALUE = "ok"
LOGIN_PATH = "/login"
HOME_PATH = "/"
DEFAULT_SESSION_MAX_AGE_SECONDS = 30 * 24 * 60 * 60
JOBS_REFRESH_SECONDS = 30
JOBS_ACTIVE_REFRESH_SECONDS = 5
JOBS_POLL_ELEMENT_ID = "jobs-poll"
SECONDS_PER_MINUTE = 60
SECONDS_PER_HOUR = 60 * SECONDS_PER_MINUTE
SECONDS_PER_DAY = 24 * SECONDS_PER_HOUR
ETA_UNKNOWN_TEXT = "-"
ETA_UNDER_A_MINUTE_TEXT = "<1m"
IN_LIBRARY_LABEL = "In Jellyfin"
WISHLISTED_LABEL = "Wishlisted"
QUEUED_LABEL = "Queued"
UNAIRED_LABEL = "Unaired"
BROWSE_LABEL = "Browse"
FIND_TORRENTS_LABEL = "Find torrents"
JOB_ROW_ID_PREFIX = "job-"
LOGIN_RATE_LIMIT = "10/minute"
RETRYABLE_STATUSES = frozenset({"FAILED", "NEEDS_ATTENTION"})
TERMINAL_STATUS_DELETED = "DELETED"
DATE_LENGTH = len("YYYY-MM-DD")
SEARCH_PATH = "/search"
WHOLE_SERIES = "all"
MIN_TARGETABLE_SEASON = 1
TMDB_RESULTS_MAX = 12
MAGNET_PREFIX = "magnet:"
HTTP_PREFIX = "http"
DOWNLOADER_SERVICE_NAME = "torrent-downloader"
SEARCH_TIMEOUT_SETTING = "search_timeout_seconds"
DEFAULT_SEARCH_TIMEOUT_SECONDS = 15
RELEASE_NAME_SEPARATORS = "._- "
SETTINGS_PATH = "/settings"
DISCOVER_PATH = "/discover"
WISHLIST_PATH = "/wishlist"
SHOWS_PATH = "/shows"
SHOW_PATH = SHOWS_PATH + "/{tmdb_id}"
NAV_LINKS = (
    (HOME_PATH, "Jobs"),
    (SEARCH_PATH, "Search"),
    (DISCOVER_PATH, "Discover"),
    (WISHLIST_PATH, "Wishlist"),
    (SETTINGS_PATH, "Settings"),
)
FIRST_PAGE = 1
TMDB_ATTRIBUTION = "This product uses the TMDB API but is not endorsed or certified by TMDB."
MEDIA_TYPE_LABELS = {MediaType.MOVIE: "Movies", MediaType.SHOW: "Shows"}
