# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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
