# CLAUDE.md - medialab-web

Workspace rules, conventions, standards and workflow live in the root
[`medialab/CLAUDE.md`](../CLAUDE.md); it is the authority when anything here
disagrees. This file holds only what is specific to this code.

## Commands

```bash
uv sync --dev
uv run medialab-web-dev
uv run pytest
```

## Architecture

Server-rendered FastAPI + Jinja2 + HTMX. No JavaScript build. No business
logic: every action is one gateway call and a re-rendered fragment. The
gateway client (`client/`, `schemas/`) is a copy of the bot's; extract into a
shared package on the third consumer, not before.

Auth is one shared password and an `itsdangerous` signed cookie. Every page
route depends on `require_session`; `/login`, `/health` and `/static` do not.

## Module layout

```
src/medialab_web/
├── main.py         app factory, routers, static mount, startup password check
├── config.py       AppConfig (pydantic-settings)
├── constants.py    named limits and cookie/session values
├── auth.py         password check, cookie sign/verify, require_session
├── deps.py         request-scoped gateway client
├── format.py       presentation helpers (show, browse and job URLs, episode codes, follow start text)
├── client/         OrchestratorClient mixins (copied from medialab-bot); _shows.py and
│                   _watchlist.py (save, follow, pause, check, episodes, retry) are web-only
├── schemas/        gateway response models; CardItem (a poster card's hx-vals);
│                   watchlist.py (FollowCard / FollowForm: the picker's fields, FollowView)
├── routes/         pages (/, /login, /logout), jobs (partials + actions; select mode posts the checked ids to the combined plan and bulk delete),
│                   search (/search, tmdb/scope/torrents partials, /downloads),
│                   settings (/settings page, save and reset rows), system (/health),
│                   discover (/discover grid and detail partial),
│                   watchlist (/watchlist tabs, /wishlist redirect, save and unsave, the
│                   follow picker and follow, pause/resume/check/unfollow, episodes and retry,
│                   the season pack decision),
│                   shows (/shows/{tmdb_id}: seasons and episodes, Find torrents per level;
│                   episode_list_context and picker_seasons shared with watchlist),
│                   trailers (/partials/trailers: player, list or notice; /play; nothing on render)
├── media.py        TMDB media type -> contracts MediaType
├── templates/      base, login, index, search, discover, watchlist, show, settings, partials/
│                   (poster_card macro shared by discover, watchlist and search results, opening
│                   discover_detail in place; the card hosts the download flow in a .download-slot
│                   and the trailer in a .trailer-slot; scope and torrents target
│                   "closest .download-slot", which the show, jobs and watchlist pages put on #stage;
│                   watchlist_actions is wrapped in a .watchlist-actions element that its
│                   buttons re-render; episode_list is shared by the show page and the
│                   Following card; follow_picker, follow_card)
└── static/         stylesheet
```

## Testing patterns

- `httpx.AsyncClient` with `ASGITransport` against the app; the gateway client
  is a `MagicMock` installed through `app.state.client`. Never mock `httpx`
  except in `test_client.py`.
- `logged_in` fixture posts the password once and reuses the cookie.
