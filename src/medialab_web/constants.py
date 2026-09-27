"""Named values shared across the web UI."""

from medialab_contracts import DEFAULT_FOLLOW_RESOLUTION, FollowStartMode, MediaType, WatchlistKind

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
SAVED_LABEL = "Saved"
FOLLOWING_LABEL = "Following"
WATCHLIST_KIND_LABELS = {WatchlistKind.SAVED: SAVED_LABEL, WatchlistKind.FOLLOWING: FOLLOWING_LABEL}
SAVE_LABEL = "Save"
UNSAVE_LABEL = "Unsave"
FOLLOW_LABEL = "Follow"
UNFOLLOW_LABEL = "Unfollow"
PAUSE_LABEL = "Pause"
RESUME_LABEL = "Resume"
PAUSED_LABEL = "Paused"
CHECK_NOW_LABEL = "Check now"
EPISODES_LABEL = "Episodes"
RETRY_LABEL = "Retry"
CANCEL_LABEL = "Cancel"
SUBMITTED_LABEL = "Submitted"
IGNORED_LABEL = "Ignored"
WANTED_LABEL = "Wanted"
NEVER_TEXT = "never"
FOLLOW_RESOLUTIONS = ("4K", "1080p", "720p")
DEFAULT_RESOLUTION = DEFAULT_FOLLOW_RESOLUTION
FOLLOW_START_LABELS = {
    FollowStartMode.NEW_ONLY: "New episodes only",
    FollowStartMode.FROM: "From season and episode",
    FollowStartMode.BEGINNING: "From the beginning",
}
NEW_EPISODES_TEXT = "New episodes"
FROM_BEGINNING_TEXT = "From the beginning"
NOTHING_SUBMITTED_NOTICE = "Nothing new to submit."
CHECK_TIMEOUT_SECONDS = 120.0
DATETIME_FORMAT = "%Y-%m-%d %H:%M"
QUEUED_LABEL = "Queued"
UNAIRED_LABEL = "Unaired"
BROWSE_LABEL = "Browse"
FIND_TORRENTS_LABEL = "Find torrents"
JOB_ROW_ID_PREFIX = "job-"
LOGIN_RATE_LIMIT = "10/minute"
RETRYABLE_STATUSES = frozenset({"FAILED", "NEEDS_ATTENTION"})
TERMINAL_STATUS_DELETED = "DELETED"
STATUS_DONE = "DONE"
REDO_LABEL = "Redo"
REDO_NOTICE = "Picking a torrent replaces the original download"
SHORT_ID_LENGTH = 8
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
WATCHLIST_PATH = "/watchlist"
LEGACY_WISHLIST_PATH = "/wishlist"
WATCHLIST_PARTIAL_PATH = "/partials/watchlist"
FOLLOW_PARTIAL_PATH = WATCHLIST_PARTIAL_PATH + "/follow"
FOLLOW_BUTTON_PARTIAL_PATH = FOLLOW_PARTIAL_PATH + "/button"
WATCHLIST_SHOW_PARTIAL_PATH = WATCHLIST_PARTIAL_PATH + "/{tmdb_id}"
EPISODES_SLOT_CLASS = "episodes-slot"
WATCHLIST_ACTIONS_CLASS = "watchlist-actions"
FOLLOW_NOTICE_CLASS = "follow-notice"
SHOWS_PATH = "/shows"
SHOW_PATH = SHOWS_PATH + "/{tmdb_id}"
NAV_LINKS = (
    (HOME_PATH, "Jobs"),
    (SEARCH_PATH, "Search"),
    (DISCOVER_PATH, "Discover"),
    (WATCHLIST_PATH, "Watchlist"),
    (SETTINGS_PATH, "Settings"),
)
TRAILERS_PARTIAL_PATH = "/partials/trailers"
TRAILER_PLAY_PATH = TRAILERS_PARTIAL_PATH + "/play"
TRAILER_SLOT_CLASS = "trailer-slot"
WATCH_TRAILER_LABEL = "Watch trailer"
TRAILER_CLOSE_LABEL = "Close"
OFFICIAL_LABEL = "Official"
NO_TRAILER_NOTICE = "No trailer on TMDB"
TRAILERS_UNAVAILABLE_MESSAGE = "Could not load trailers. TMDB or the gateway is not reachable."
FIRST_PAGE = 1
TMDB_ATTRIBUTION = "This product uses the TMDB API but is not endorsed or certified by TMDB."
MEDIA_TYPE_LABELS = {MediaType.MOVIE: "Movies", MediaType.SHOW: "Shows"}
