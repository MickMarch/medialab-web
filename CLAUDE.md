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
├── format.py       presentation helpers
├── client/         OrchestratorClient mixins (copied from medialab-bot)
├── schemas/        gateway response models
├── routes/         pages (/, /login, /logout), jobs (partials + actions),
│                   search (/search, tmdb/scope/torrents partials, /downloads), system (/health)
├── media.py        TMDB media type -> contracts MediaType
├── templates/      base, login, index, partials/
└── static/         stylesheet
```

## Testing patterns

- `httpx.AsyncClient` with `ASGITransport` against the app; the gateway client
  is a `MagicMock` installed through `app.state.client`. Never mock `httpx`
  except in `test_client.py`.
- `logged_in` fixture posts the password once and reuses the cookie.
