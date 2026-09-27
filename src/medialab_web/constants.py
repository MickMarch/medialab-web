"""Named values shared across the web UI."""

from medialab_contracts import MediaType

SESSION_COOKIE_NAME = "medialab_session"
SESSION_VALUE = "ok"
LOGIN_PATH = "/login"
HOME_PATH = "/"
DEFAULT_SESSION_MAX_AGE_SECONDS = 30 * 24 * 60 * 60
JOBS_REFRESH_SECONDS = 30
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
