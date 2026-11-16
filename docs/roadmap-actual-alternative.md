# AutoFin Roadmap: A Lighter, Agentic Alternative to Actual Budget

Written: 2026-11-16. Updated the same day after the August ledger work (`todo/2026-08-09-clawfin-ledger`) was merged into `main`.

## Goal

AutoFin (formerly ClawFin) is meant to become a full alternative to Actual Budget for a savings-first, agent-assisted personal finance workflow. It should be lighter to run, easier to keep clean, and agentic by default.

Until it gets there, AutoFin runs **in parallel** with Actual Budget. Both pull from SimpleFIN. AutoFin never writes to Actual. Work is prioritized by where AutoFin can beat Actual first, not by matching Actual feature-for-feature.

## Design Principles

- **Savings-first, not envelopes.** The main control is "did the savings engine hit its monthly target", reconciled weekly. Real-time category budgets are deliberately out of scope.
- **The agent proposes, the human approves.** The AI can read everything and stage changes. Every write goes through a reviewable proposal with a preview. The agent never executes trades or moves money.
- **A correct ledger beats more features.** Transfers, card payments and savings movements must never be counted as spending.
- **Everything the UI can do, the API and MCP can do.**
- **One `docker compose up`.** No new infrastructure for single-user self-hosting.

## Reference Workflow

This is the workflow AutoFin must support end to end, based on how it is currently run in Actual Budget plus a Codex agent over MCP:

1. **Sync.** Pull transactions from SimpleFIN and report the status of each institution.
2. **Weekly recon.**
   - Find uncategorized transactions and apply high-confidence categorizations in a reviewed batch.
   - Send card payments, transfers, ambiguous incoming money and reimbursements to a manual review queue.
   - Report the pace against the monthly savings target.
3. **Monthly close.** Produce a P&L-style statement:
   - income
   - core living
   - life and one-offs
   - normalized loan run-rate
   - operating surplus
   - savings and investments
   - data quality: remaining uncategorized items and suspected transfers
4. **Savings scorecard.** Track the monthly saved/invested amount against a target, plus per-paycheque pace. Score each month green, yellow or red.
5. **Shared expenses.** Partner and roommate reimbursements offset the matching spending instead of counting as income. The splitting itself happens in Splitwise.
6. **Portfolio review.** Import Wealthsimple holdings and activity exports, then compare against the previous review date.

## Already in AutoFin

The August ledger work already covers much of what Actual is used for:

| Capability | Where |
|---|---|
| Transfer pair detection (equal and opposite amounts, ≤2 days apart, different accounts), excluded from dashboard totals | `backend/ingestion/transfer_detector.py`, `backend/routers/dashboard.py` |
| On-budget/off-budget accounts; investment accounts kept out of cash-flow totals | `Account.on_budget`, `_budget_transaction_query` |
| Manual transaction create, edit and delete; bulk actions; exact-amount splits | `backend/routers/transactions.py` |
| Rule management with impact preview, and merchant merge | `backend/routers/settings.py` (`/rules/preview`, `/rules/{id}/impact`) |
| CSV import preview before commit | `backend/routers/import_data.py` (`/csv/preview`) |
| SimpleFIN sync metadata, pending transactions, stale-sync status | `/simplefin/status` |
| Date-range dashboard, recurring detection, planning, holdings snapshot browsing | dashboard, transactions and holdings routers |
| CSV export, DB backup download, Alembic migrations, CI | settings router, `backend/db/migrations/`, `.github/workflows/ci.yml` |

## Fixed on 2026-11-16

| Issue | Fix |
|---|---|
| A Wealthsimple holdings import deleted every earlier snapshot, so snapshot browsing only ever had one date | Only the snapshot dates being imported are replaced (`backend/routers/import_data.py`) |
| With history kept, dashboard and agent holdings totals would have summed every snapshot | New `latest_holdings()` helper used by the dashboard and agent tools (`backend/routers/holdings.py`) |
| The agent's `query_spending` counted transfers while the dashboard excluded them, so the agent and the dashboard disagreed | Transfers are excluded unless asked for explicitly (`backend/ai/tools.py`) |
| `gap`, `event` and `lens` matched inside other words (Singapore, Prevention, Allens) | Word boundaries added (`backend/ingestion/categorizer.py`) |

Covered by `backend/tests/test_ledger_fixes.py`.

## What's Left, in Order

### 1. Savings and reimbursement as first-class kinds

Transfer detection currently treats a chequing→TFSA contribution as a plain transfer. That keeps it out of spending, but nothing counts it as **savings**, so a savings scorecard can't be computed. Add a transaction kind (`spend | income | transfer | savings | reimbursement`) or equivalent flags:

- Transfers into investment or savings accounts become `savings`.
- Incoming money that offsets shared costs becomes `reimbursement`.
- Every total and agent tool uses the kind.

Also add parity fixtures: a few known months with expected income, expenses and savings, checked against AutoFin's output.

### 2. Review queue (where AutoFin starts beating Actual)

One screen listing:

- uncategorized transactions
- low-confidence AI categorizations
- unpaired transfer candidates
- reimbursement candidates

Approve in a batch with a preview of totals before applying, building on the existing bulk and rule-preview endpoints.

Add a **one-way import from Actual Budget** that turns already-cleaned merchant→category history into rules, so the parallel run starts from existing judgement.

### 3. Savings scorecard and monthly P&L

- **Savings target** in settings: a monthly amount, an optional per-paycheque amount, and yellow/red thresholds. Use it instead of the "Budgeting + goals" item from the old roadmap.
- **Monthly P&L view.** Categories get a group (`core` or `one-off`). A fixed "loan run-rate" setting normalizes loan payments that land on uneven dates. Include a data-quality line.

### 4. Agentic layer

- A **proposals table**. The agent stages categorizations, kind changes and transfer pairings there; the user approves them in the review queue.
- New agent tools: `get_review_queue`, `monthly_pnl`, `savings_scorecard`, `propose_changes`. Give the existing tools date-range parameters.
- An **MCP endpoint** that exposes the same tools, so external agents (Codex, Claude, OpenClaw) can run weekly recon against AutoFin. While both ledgers run, the same agent can query both and compare them.

### 5. Remaining parity with Actual

- **Account reconciliation:** compare against a statement balance and flag the difference.
- **Per-institution sync errors** surfaced in the UI, for example "auth required".

## When AutoFin Replaces Actual

AutoFin is "the better one" when all of these hold:

- Its monthly P&L matches the parallel Actual recon within a small tolerance for 2–3 consecutive months.
- Weekly cleanup takes less manual work than in Actual: fewer items in the queue, and no writes that silently fail to persist.
- The scorecard and P&L come straight from AutoFin, with no external agent assembling a report.

## Not Building

- Envelope or category budgets, and budget alerts.
- Multi-user support. Sharing is handled through reimbursements plus Splitwise.
- PDF report export, benchmark comparisons, ACB and capital-gains summaries, CRA integration, crypto, Supabase or cloud sync.
- In-app trade or DCA recommendations. Portfolio judgement stays outside the app.

## Related Docs

- `docs/review.md`: architecture review of the April `main`. Many of its Phase 0–1 items, such as auth enforcement, migrations, transfer exclusion and payroll categorization, were addressed by the August ledger work.
