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
├── format.py       presentation helpers (also show, browse and job URLs, episode codes)
├── client/         OrchestratorClient mixins (copied from medialab-bot); _shows.py is web-only
├── schemas/        gateway response models; CardItem (a poster card's hx-vals)
├── routes/         pages (/, /login, /logout), jobs (partials + actions),
│                   search (/search, tmdb/scope/torrents partials, /downloads),
│                   settings (/settings page, save and reset rows), system (/health),
│                   discover (/discover, /wishlist, detail and wishlist toggle partials),
│                   shows (/shows/{tmdb_id}: seasons and episodes, Find torrents per level)
├── media.py        TMDB media type -> contracts MediaType
├── templates/      base, login, index, search, discover, wishlist, show, settings, partials/
│                   (poster_card macro shared by discover, wishlist and search results)
└── static/         stylesheet
```

## Testing patterns

- `httpx.AsyncClient` with `ASGITransport` against the app; the gateway client
  is a `MagicMock` installed through `app.state.client`. Never mock `httpx`
  except in `test_client.py`.
- `logged_in` fixture posts the password once and reuses the cookie.
