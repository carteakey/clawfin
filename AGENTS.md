# Repository Guidelines

## Project Structure & Module Organization
`backend/` contains the FastAPI app. Keep API endpoints in `backend/routers/`, database code in `backend/db/`, AI integrations in `backend/ai/`, and ingestion/parsing logic in `backend/ingestion/` plus `backend/ingestion/normalizers/`. Backend tests live in `backend/tests/`.

`frontend/` contains the Vite + React app. Main entry points are `src/main.jsx` and `src/App.jsx`; feature UI lives under `src/components/<feature>/`, shared API code in `src/api/`, state in `src/store/`, and formatting helpers in `src/utils/`. Project notes and rollout plans belong in `docs/`. Docker entrypoints stay at the repo root.

## Build, Test, and Development Commands
Use Docker for the full stack:

```bash
docker compose up -d
docker compose --profile ai-local up -d
```

Use local dev when iterating on one side:

Use Python 3.12 and Node.js 24 for parity with CI.

```bash
python3.12 -m venv .venv && source .venv/bin/activate
pip install -r backend/requirements.txt
AUTOFIN_PASSWORD=dev uvicorn backend.main:app --reload

cd frontend
npm ci
npm run dev
npm run build
npm test -- --run
```

Run backend tests with `PYTHONPATH=. pytest backend/tests -q` and frontend tests with `cd frontend && npm test -- --run`.

To manually verify briefing features locally, run the backend with `AUTOFIN_AUTOMATION_TOKEN` and an AI provider configured, then run the frontend dev server. Open chat with `⇧⌘K`; the empty chat state should show `Daily Brief`, `Weekly Brief`, and `Private Daily` preset buttons. The direct automation endpoint can be smoke-tested with `POST /api/briefings/transactions` plus the `X-AutoFin-Automation-Token` header.

## Coding Style & Naming Conventions
Match the existing style: Python uses 4-space indentation, `snake_case` modules, and clear function names; React uses 2-space indentation, semicolons, single quotes, and `PascalCase` component files such as `Dashboard.jsx`. Keep new frontend features grouped by folder (`src/components/transactions/`, `src/components/settings/`). No formatter or linter config is checked in, so keep diffs small and consistent with nearby code.

## Testing Guidelines
Backend tests use `pytest` and follow `test_*.py` naming in `backend/tests/`. Add focused regression tests whenever you touch CSV parsers, deduplication, or API behavior. There is no enforced coverage gate today; use targeted assertions over broad fixtures. For frontend logic, add `*.test.js` or `*.test.jsx` near the component or module being exercised.

## Commit & Pull Request Guidelines
Recent history follows Conventional Commit style with optional scopes, for example `feat(v0.1): ...`, `fix(sync): ...`, and `chore(frontend): ...`. Keep subjects imperative and scoped when useful. PRs should include a short summary, impacted areas (`backend`, `frontend`, ingestion source, or Docker), manual test notes, and screenshots for visible UI changes.

## Security & Configuration Tips
Start from `.env.example`; never commit real secrets. Document new environment variables there when adding them. Treat `AUTOFIN_SECRET_KEY`, provider API keys, and the SQLite path (`~/.autofin/autofin.db` locally, `/data/autofin.db` in Docker) as sensitive configuration.

When `AUTOFIN_PASSWORD` is configured, normal app API routers require the UI JWT from `/api/auth/login`. Keep `/api/auth/*` and `/api/health` public, and keep machine-to-machine briefing automation on the separate automation-token path.

Briefing and automation endpoints use a separate `AUTOFIN_AUTOMATION_TOKEN`; require the `X-AutoFin-Automation-Token` header for machine-to-machine calls. Do not reuse the UI JWT, SimpleFIN access URL, or AI provider keys in scheduler or LLM prompts.

The frontend must not call automation-token endpoints. UI briefing buttons should use the normal authenticated `/api/chat/briefing` path; `/api/briefings/transactions` is for cron/n8n/service calls only.

SimpleFIN sync stores account freshness metadata on `Account`: `last_sync_at`, `last_successful_balance_date`, `last_successful_transaction_date`, `last_sync_error`, `simplefin_account_present`, and `stale_reason`. Preserve these fields when touching sync, account listing, or briefing logic because they drive reconnect nudges. Stale sync detection is based on `AUTOFIN_SIMPLEFIN_STALE_DAYS`, not transaction activity recency.

Database schema changes must use versioned Alembic revisions under `backend/db/migrations/`. Backend startup runs migrations to `head`; do not reintroduce `create_all()` or ad-hoc `ALTER TABLE` patches for application startup. Migration downgrades are intentionally unsupported for SQLite, so document a backup-first recovery path for every schema change.

External automation/LLM handoff docs live in `docs/briefing-integration-skill.md`. Keep its request/response examples aligned with `/api/briefings/transactions` whenever the briefing API changes.

## Planning

Linear is the source of truth for committed planned work in this repository.

- Team: `carteakey` (`CAR`)
- Project: [AutoFin](https://linear.app/carteakey/project/autofin-b8b356505b56)
- `TODO.md` remains a speculative thinking backlog; move an item to Linear only when it is intentionally committed for implementation, then remove the duplicate from `TODO.md`.

The 2026-08-09 ledger backlog is tracked in the `Ledger safety and usability` milestone. The promoted TODO items are grouped into CAR-123 (credentials, backups, dependency safety), CAR-124 (safe/reversible mutations and categorization), CAR-125 (import previews, API contracts, and feedback), CAR-126 (ledger navigation and responsive controls), and CAR-127 (configurable briefing schedules). Linear is authoritative for their status and acceptance criteria; this repository remains authoritative for implementation and verification evidence.
