# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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
