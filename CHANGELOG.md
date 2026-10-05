# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.21.0] - 2026-10-05

### Changed

- A download or redo the gateway refuses with a retryable code
  (`SOURCE_UNREACHABLE`, `TMDB_UNAVAILABLE`) shows the gateway's own detail
  instead of the generic failure message. The client returns a `GatewayError`
  for a parsed error envelope; other codes keep the generic message.

## [0.20.0] - 2026-10-04

### Added

- Dismiss on flagged job rows and `Dismiss selected` in the bulk bar: close a
  `FAILED` or `NEEDS_ATTENTION` job without touching files. Dismissed rows stay
  listed, muted, and the status filter offers `DISMISSED`.
- Flagged rows offer the action that resolves them from the gateway's
  `attention_cause`: Redo when the torrent vanished with nothing placed, Retry
  otherwise.

## [0.19.0] - 2026-10-03

### Added

- The Services card shows whether qBittorrent is bound to an accepted VPN
  interface, from the gateway's `vpn_interface_bound` health flag
  (MickMarch/medialab#114).

## [0.18.0] - 2026-10-02

### Added

- Season rows on the Following card and the show page show the follow's
  season-pack state: a Season pack badge linking to the pack job, Retrying
  pack, Episode by episode, or, when no pack was found, the three choices
  (retry with a longer search, retry with fewer seeders, episode by
  episode) that post the decision and re-render the list
  (MickMarch/medialab#104).
- medialab-contracts pinned to v1.1.0 for the season follow models.

## [0.17.0] - 2026-10-02

### Added

- Select mode on the Jobs page: a checkbox per row, a sticky bar with the
  count and Delete selected, one combined deletion plan and one
  confirmation for every checked job. Jobs the single delete would refuse
  are listed and skipped; the rest are removed in one gateway call
  (MickMarch/medialab#105).

## [0.16.0] - 2026-10-02

### Changed

- The trailer list is a grid of YouTube thumbnails with the name clamped
  to two lines, so a title with many videos fits a phone
  (MickMarch/medialab#102).

## [0.15.0] - 2026-10-02

### Changed

- Search results are poster cards that open the same detail card as
  Discover, so a title found by either page has the same Download, Save /
  Follow and Watch trailer actions (MickMarch/medialab#101).
- The detail card opens in place, spanning the grid under the poster that
  opened it, and the download flow (season scope, torrent table, started
  notice) renders in a slot inside the card instead of at the top of the
  page. The show, jobs and watchlist pages keep their page-level stage
  (MickMarch/medialab#103).
- The step strip on the Search page is gone; the card is the flow.

## [0.14.0] - 2026-09-27

### Changed

- Breaking: the wishlist is the watchlist. `/wishlist` redirects permanently
  to `/watchlist`, the nav reads "Watchlist", the "Wishlisted" badge is now
  "Saved" or "Following", and the detail card's Add to / Remove from wishlist
  is Save / Unsave. Client methods, card fields and the search result fields
  follow the medialab-contracts rename (`on_watchlist`, `watchlist_kind`)
  (MickMarch/medialab#24).
- medialab-contracts pinned to v1.0.0 for the watchlist and follow models.
- Search result cards carry Save and, for shows, Follow beside the download
  step.

### Added

- Watchlist page with Saved and Following tabs (`?kind=`). A Following card
  shows the start point ("New episodes", "From S02E03", "From the
  beginning"), resolution, last check and last submitted episode, with
  Pause / Resume, Check now (reports what was submitted), Unfollow and an
  Episodes panel that loads the show's seasons on first open with the extra
  Submitted, Ignored and Wanted badges and Retry on submitted or ignored
  episodes (MickMarch/medialab#24).
- Follow on show cards (discover detail, search results, the Saved tab) and
  in the show page header. It opens a picker: "New episodes only", "From
  season and episode" (season and episode selects, seeded from the page data
  on the show page and from the show browser elsewhere) or "From the
  beginning", plus a resolution select defaulting to 1080p. A show not yet
  saved is saved first, then followed; from the Saved tab the page moves to
  the Following tab (MickMarch/medialab#24).
- The show page of a followed show reads its episodes from the watchlist
  view, so the follow badges and Retry appear there too.
- Client `list_watchlist(kind=)`, `follow_show`, `unfollow_show`,
  `pause_follow`, `resume_follow`, `check_follow`, `watchlist_episodes` and
  `retry_episode` for the gateway's follow routes.

## [0.13.0] - 2026-09-27

### Added

- Watch trailer on the discover and search detail card and on every season
  row of the show page. Nothing is fetched until the button is pressed; then
  the title's (or season's) YouTube trailers and teasers are listed, official
  first, and picking one plays it in an embedded privacy-enhanced YouTube
  player that fills the card width. A single video plays at once; no video
  shows "No trailer on TMDB"; a gateway failure shows the error fragment.
  Close empties the player and only one player is open per page
  (MickMarch/medialab#96).
- Client `videos(media_type, tmdb_id, season=None)` for the gateway's
  `/search/tmdb/{media_type}/{id}/videos` route (MickMarch/medialab#96).

### Changed

- medialab-contracts pinned to v0.12.0 for `Video`, `VideosResponse` and
  `youtube_embed_url`.

## [0.12.0] - 2026-09-27

### Fixed

- Error notices (failed delete, retry, redo, download, wishlist toggle) now
  render: htmx is configured to swap 4xx and 5xx responses.

### Added

- Redo on a finished job: the jobs page opens the torrent step above the
  table with the job's title, year, media type and scope (episode, season or
  whole series) preset, under the notice "Picking a torrent replaces the
  original download". Replace on a row confirms, posts to the gateway's redo
  route (one action: delete the original, submit the replacement as a job
  linked to it) and re-renders the whole table. A refused or failed redo
  leaves the original untouched. The replaced row shows `Replaced by <id>`
  and the replacement `Redo of <id>`, each linking the other row
  (MickMarch/medialab#92).
- `JobView.redo_of` and `JobView.redone_by`; client `redo` beside `download`
  (MickMarch/medialab#92).

## [0.11.0] - 2026-09-27

### Added

- Show page (`/shows/{tmdb_id}`): poster, title, year, status, overview and
  badges, then every season as a collapsible row with its episodes (still,
  `S02E05 Title`, air date, clamped overview, and "In Jellyfin", "Queued"
  linking to the job, or "Unaired"). The latest season opens on load. Find
  torrents at the series, season and episode level enters the existing
  torrent step with that scope preset. A gateway failure renders a friendly
  message with a link back to Discover (MickMarch/medialab#91).
- Show poster cards in Discover, title search results and the wishlist carry
  a Browse link to the show page; a show's title in the jobs table links
  there too (MickMarch/medialab#91).
- Download forwards the searched season and episode to the gateway so the
  job records its scope; a whole-series download sends neither
  (MickMarch/medialab#91).

### Changed

- medialab-contracts pin bumped to v0.11.0 for `ShowBrowseResponse` and
  `still_url`.

## [0.10.0] - 2026-09-27

### Added

- Jobs table: downloading jobs show a progress bar under the status badge
  with percent, speed and ETA (`42% - 3.1 MB/s - ETA 12m`; ETA reads `-` when
  unknown). The table refreshes every 5 seconds while anything is
  downloading and every 30 seconds otherwise, and pauses while a deletion
  plan is open (MickMarch/medialab#86).
- Poster cards show a "Wishlisted" badge for titles on the wishlist, and
  title search results now carry both the "Wishlisted" and "In Jellyfin"
  badges (MickMarch/medialab#88).

### Changed

- medialab-contracts pin bumped to v0.10.0 for `JobProgress`.
- The jobs table poll keeps the chosen status filter instead of falling
  back to the filter the page was opened with.

## [0.9.0] - 2026-09-27

### Added

- Discover page: trending movies or shows as a poster grid, narrowed by
  genre, with More for the next page. A poster opens a detail card with
  Download (into the existing torrent or season step) and Add to / Remove
  from wishlist. Titles already in Jellyfin carry an "In Jellyfin" badge.
  The page carries the TMDB attribution notice (MickMarch/medialab#81).
- Wishlist page: the shared wishlist as a poster grid with Download and
  Remove per title (MickMarch/medialab#81).
- Discover and Wishlist links in the navigation of every page.
- Title search results show each title's poster, with a text card when
  there is none or it fails to load (MickMarch/medialab#84).

### Changed

- medialab-contracts pin bumped to v0.9.0 for the discover and wishlist
  models and the TMDB poster URL helper.

## [0.8.1] - 2026-09-27

### Fixed

- Torrent results give the release name the remaining width instead of a
  narrow column, and release names in both tables wrap at their separators
  rather than mid-word. Torrent results stack on narrow screens.

## [0.8.0] - 2026-09-26

### Added

- A searching panel with a progress bar bounded by the downloader's
  configured search timeout while torrents are being searched.

## [0.7.0] - 2026-09-26

### Added

- Settings page: every service's runtime settings with save and reset per
  row and when each change applies.

## [0.6.0] - 2026-09-26

### Changed

- Download sends the picked torrent's name, so the jobs table shows it while
  the download runs.

## [0.5.0] - 2026-09-26

### Changed

- The torrent search also searches what you typed plus the picked year, for
  titles TMDB spells differently from release names.

## [0.4.0] - 2026-09-26

### Added

- Clear search cache button on the search page.

## [0.3.0] - 2026-09-26

### Changed

- Search is a single stage that each step replaces, with a step indicator,
  back links, and a scroll to the top on every swap, so a phone always shows
  the current step.

## [0.2.0] - 2026-09-26

### Added

- Search page: TMDB title cards, season/episode scope for shows, torrent
  table grouped by resolution with seeders, size and audio languages, and a
  confirmed Download button per row.

## [0.1.0] - 2026-09-26

### Added

- Password login with a signed session cookie.
- Jobs page: every pipeline job with title, year, release name, status and
  age; filter by status; Retry for FAILED and NEEDS_ATTENTION; Stop seeding;
  storage panel; auto-refresh.
- Delete flow: the gateway's deletion plan shown inline, confirmed with a
  second click.
