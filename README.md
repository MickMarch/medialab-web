# medialab-web

Browser UI for the medialab suite. A thin client of the
[medialab-orchestrator](https://github.com/MickMarch/medialab-orchestrator)
gateway, beside the Discord bot: the bot keeps notifications and quick search,
this page holds the tables and the buttons. Spec:
[docs/specs/web-ui.md](https://github.com/MickMarch/medialab/blob/main/docs/specs/web-ui.md).

Workspace rules, conventions and the release flow:
[medialab/CLAUDE.md](https://github.com/MickMarch/medialab/blob/main/CLAUDE.md).

## Run

```bash
uv sync --dev
cp .env.example .env   # fill ORCHESTRATOR_API_KEY, WEB_PASSWORD, WEB_SECRET_KEY
uv run medialab-web-dev
uv run pytest
```

## Pages

| Page | Gateway calls | Controls |
|---|---|---|
| `/login` | none | shared password (`WEB_PASSWORD`); signed cookie for `SESSION_MAX_AGE_SECONDS` |
| `/` | `GET /jobs`, `GET /storage`, `GET /health` | status filter; on a flagged row (FAILED, NEEDS_ATTENTION) the action its `attention_cause` calls for: Redo when the torrent vanished with nothing placed, Retry otherwise, and Dismiss either way (`POST /jobs/{id}/dismiss`); Delete (plan, then confirm); Redo (DONE); Stop seeding; rows link a replaced job and its replacement; DISMISSED rows stay listed, muted |
| `/jobs/dismiss` (Dismiss selected in the bulk bar) | `POST /jobs/dismiss` | dismisses the checked rows in one gateway call with no plan step (nothing on disk changes), then re-renders the table with a notice naming any refused row and why |
| `/jobs/{id}/plan` | `GET /jobs/{id}/deletion-plan` | the plan and the red Delete button; nothing is touched before it |
| `/partials/jobs/{id}/redo` | `GET /search/torrents`, `POST /jobs/{id}/redo` | the torrent step with the job's scope preset, above the table; Replace per row (confirmed) deletes the original and submits the replacement in one gateway action, then re-renders the table |
| `/search` | `GET /search/tmdb`, `GET /search/tmdb/show/{id}`, `GET /search/torrents`, `POST /download` | title cards with Save and Follow (shows); season/episode scope for shows; torrent table by resolution with languages; Download per row (confirmed), carrying the searched season and episode |
| `/search/cache` (button on `/search`) | `DELETE /search/cache` | drops the downloader's cached search result sets so the next search runs fresh |
| `/discover` | `GET /discover/{type}`, `GET /discover/{type}/genres` | Movies/Shows toggle; genre select; poster grid with More; detail card with Download (the `/search` torrent or season step), Save / Unsave, Follow for shows and Watch trailer; "In Jellyfin" and "Saved" / "Following" badges |
| `/watchlist` (`/wishlist` redirects here) | `GET /watchlist?kind=`, `PUT` and `DELETE /watchlist/{type}/{id}` | Saved tab: poster grid with Download, Follow (shows) and Remove per title. Following tab: one card per followed show with start point, resolution, last check, last submitted, Pause / Resume, Check now, Unfollow, Browse and an Episodes panel |
| `/partials/watchlist/follow` (Follow on show cards and the show page) | `GET /shows/{id}` for the season list, `PUT /watchlist/show/{id}` when not yet saved, `PUT /watchlist/show/{id}/follow` | the picker: new episodes only, from a season and episode, or from the beginning; resolution (4K, 1080p, 720p; default 1080p) |
| `/partials/watchlist/{id}/follow/pause`, `/resume`, `/check`; `DELETE /partials/watchlist/follow` | `POST /watchlist/show/{id}/follow/pause`, `/resume`, `/check`; `DELETE /watchlist/show/{id}/follow` | the Following card's controls; Check now reports the episodes submitted |
| `/partials/watchlist/{id}/episodes` (Episodes on a Following card) | `GET /watchlist/show/{id}/episodes`, `DELETE /watchlist/show/{id}/episodes/{s}/{e}/submission` | the show page's season rows with the extra "Submitted" / "Ignored" / "Wanted" badges; Retry clears a submission and re-renders |
| `/shows/{tmdb_id}` | `GET /shows/{tmdb_id}`, and `GET /watchlist/show/{tmdb_id}/episodes` when the show is followed | show header with badges, Save / Unsave and Follow (picker seeded from the page); seasons as collapsible rows (latest open) listing episodes with still, air date, overview and "In Jellyfin" / "Queued" / "Unaired" plus the follow badges and Retry when followed; Find torrents per series, season and episode into the `/search` torrent step; reached by Browse on show cards and from a show's job row |
| `/partials/trailers` (Watch trailer on the detail card and on each season row of `/shows/{tmdb_id}`) | `GET /search/tmdb/{type}/{id}/videos` | nothing loads before the click; one trailer plays at once in an embedded youtube-nocookie player, several are listed (official first) to pick from, none shows a notice; Close stops playback and one player is open at a time |
| `/settings` | `GET /settings`, `PUT` and `DELETE /settings/{service}/{key}` | one row per runtime setting per service: value, source, when it applies; Save and Reset per row |
| `/health` | none | liveness for the doctor and compose |

Every control is an HTMX request that swaps the affected row or panel. The
jobs table refreshes itself every 30 seconds.

Posters are hotlinked from the TMDB image CDN, which the browser caches; a
missing or broken poster falls back to a text card. This product uses the
TMDB API but is not endorsed or certified by TMDB.

## Config

`.env.example` is the authoritative variable list. `WEB_PASSWORD` and
`WEB_SECRET_KEY` are secrets; where they come from is in the workspace
[secrets map](https://github.com/MickMarch/medialab/blob/main/docs/secrets.md).
