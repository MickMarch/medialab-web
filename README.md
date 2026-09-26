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
| `/` | `GET /jobs`, `GET /storage`, `GET /health` | status filter; Retry (FAILED, NEEDS_ATTENTION); Delete (plan, then confirm); Stop seeding |
| `/jobs/{id}/plan` | `GET /jobs/{id}/deletion-plan` | the plan and the red Delete button; nothing is touched before it |
| `/search` | `GET /search/tmdb`, `GET /search/tmdb/show/{id}`, `GET /search/torrents`, `POST /download` | title cards; season/episode scope for shows; torrent table by resolution with languages; Download per row (confirmed) |
| `/health` | none | liveness for the doctor and compose |

Every control is an HTMX request that swaps the affected row or panel. The
jobs table refreshes itself every 30 seconds.

## Config

`.env.example` is the authoritative variable list. `WEB_PASSWORD` and
`WEB_SECRET_KEY` are secrets; where they come from is in the workspace
[secrets map](https://github.com/MickMarch/medialab/blob/main/docs/secrets.md).
