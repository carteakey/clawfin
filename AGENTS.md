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

```bash
python3.11 -m venv .venv && source .venv/bin/activate
pip install -r backend/requirements.txt
CLAWFIN_PASSWORD=dev uvicorn backend.main:app --reload

cd frontend
npm install
npm run dev
npm run build
```

Run tests with `PYTHONPATH=. pytest backend/tests -q`. Frontend test wiring exists via `npm test` (`vitest`), but add specs before relying on it in CI-style workflows.

To manually verify briefing features locally, run the backend with `CLAWFIN_AUTOMATION_TOKEN` and an AI provider configured, then run the frontend dev server. Open chat with `⇧⌘K`; the empty chat state should show `Daily Brief`, `Weekly Brief`, and `Private Daily` preset buttons. The direct automation endpoint can be smoke-tested with `POST /api/briefings/transactions` plus the `X-ClawFin-Automation-Token` header.

## Coding Style & Naming Conventions
Match the existing style: Python uses 4-space indentation, `snake_case` modules, and clear function names; React uses 2-space indentation, semicolons, single quotes, and `PascalCase` component files such as `Dashboard.jsx`. Keep new frontend features grouped by folder (`src/components/transactions/`, `src/components/settings/`). No formatter or linter config is checked in, so keep diffs small and consistent with nearby code.

## Testing Guidelines
Backend tests use `pytest` and follow `test_*.py` naming in `backend/tests/`. Add focused regression tests whenever you touch CSV parsers, deduplication, or API behavior. There is no enforced coverage gate today; use targeted assertions over broad fixtures. For frontend logic, add `*.test.js` or `*.test.jsx` near the component or module being exercised.

## Commit & Pull Request Guidelines
Recent history follows Conventional Commit style with optional scopes, for example `feat(v0.1): ...`, `fix(sync): ...`, and `chore(frontend): ...`. Keep subjects imperative and scoped when useful. PRs should include a short summary, impacted areas (`backend`, `frontend`, ingestion source, or Docker), manual test notes, and screenshots for visible UI changes.

## Security & Configuration Tips
Start from `.env.example`; never commit real secrets. Document new environment variables there when adding them. Treat `CLAWFIN_SECRET_KEY`, provider API keys, and the SQLite path (`~/.clawfin/clawfin.db` locally, `/data/clawfin.db` in Docker) as sensitive configuration.

Briefing and automation endpoints use a separate `CLAWFIN_AUTOMATION_TOKEN`; require the `X-ClawFin-Automation-Token` header for machine-to-machine calls. Do not reuse the UI JWT, SimpleFIN access URL, or AI provider keys in scheduler or LLM prompts.

SimpleFIN sync stores account freshness metadata on `Account`: `last_sync_at`, `last_successful_balance_date`, `last_successful_transaction_date`, `last_sync_error`, `simplefin_account_present`, and `stale_reason`. Preserve these fields when touching sync, account listing, or briefing logic because they drive reconnect nudges.

External automation/LLM handoff docs live in `docs/briefing-integration-skill.md`. Keep its request/response examples aligned with `/api/briefings/transactions` whenever the briefing API changes.
