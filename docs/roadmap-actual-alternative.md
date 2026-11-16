# ClawFin Roadmap: A Lighter, Agentic Alternative to Actual Budget

Written: 2026-11-16

## Goal

ClawFin is meant to become a full alternative to Actual Budget for a savings-first, agent-assisted personal finance workflow. It should be lighter to run, easier to keep clean, and agentic by default.

Until it gets there, ClawFin runs **in parallel** with Actual Budget. Both pull from SimpleFIN. ClawFin never writes to Actual. Work is prioritized by where ClawFin can beat Actual first, not by matching Actual feature-for-feature.

## Design Principles

- **Savings-first, not envelopes.** The main control is "did the savings engine hit its monthly target", reconciled weekly. Real-time category budgets are deliberately out of scope.
- **The agent proposes, the human approves.** The AI can read everything and stage changes. Every write goes through a reviewable proposal with a preview. The agent never executes trades or moves money.
- **A correct ledger beats more features.** Transfers, card payments and savings movements must never be counted as spending.
- **Everything the UI can do, the API and MCP can do.** No hidden row caps, and calendar-month windows are supported everywhere.
- **One `docker compose up`.** No new infrastructure for single-user self-hosting.

## Reference Workflow

This is the workflow ClawFin must support end to end, based on how it is currently run in Actual Budget plus a Codex agent over MCP:

1. **Sync.** Pull transactions from SimpleFIN and report the status of each institution (for example "auth required").
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

## Blocking Bugs (Fix First)

| # | Issue | Where | Effect |
|---|---|---|---|
| 1 | Every outflow is counted as an expense | `backend/routers/dashboard.py:27-32`, `backend/ai/tools.py:118` | Card payments, transfers and investment contributions inflate expenses and push the savings rate down |
| 2 | The Transfer rule matches `payroll` and every e-transfer, and runs before Income | `backend/ingestion/categorizer.py:32` | Payroll becomes "Transfer"; rent paid by e-transfer and reimbursements are mislabelled |
| 3 | Wealthsimple holdings import deletes all prior holdings | `backend/routers/import_data.py:94` | No history, so a review can't be compared with the previous one |

## Build Order

### 0. Fixes and tests

- Fix the three bugs above.
- Add pytest fixtures built from sanitized bank and Wealthsimple CSVs. This is the evaluation report's Phase 2 item #1.
- Add a top-level React error boundary. This is the evaluation report's item #3.
- Add parity fixtures: a few known months with expected income, expenses and savings, checked against ClawFin's output.

### 1. Ledger correctness

- Add a **transaction kind**: `spend | income | transfer | savings | reimbursement`. Every total, chart and agent tool uses it.
- Add **first-class transfers**: find likely pairs (equal and opposite amounts, a few days apart, across accounts) and link them in one click. This is the fragile part of Actual's MCP, so ClawFin should do it well.
- Support **calendar-month and custom date windows** in the dashboard and tools, not only "last N days".
- Support **transaction create and edit** for amount, date, notes and kind, in addition to category and merchant.
- Add **account flags**: tracking-only (off-budget, such as investment accounts) and closed.

### 2. The recon loop (where ClawFin starts beating Actual)

- **Review queue:**
  - uncategorized transactions
  - suspected transfers
  - low-confidence AI categorizations
  - reimbursement candidates

  Approve or edit in a batch, with a preview of totals before applying.
- **Rule editor with dry-run.** Show which past transactions a rule would match before applying it. This replaces the plain regex grid planned as the evaluation report's item #2.
- **One-way import from Actual Budget.** Turn already-cleaned merchant→category history into `CategoryRule` rows, so the parallel run starts from existing judgement instead of a blank slate.

### 3. Savings scorecard and P&L

- **Savings target** in settings: a monthly amount, an optional per-paycheque amount, and yellow/red thresholds. This replaces "Advanced Budgeting Goals" on the README roadmap.
- **Monthly P&L view.** Each category gets a group (`core` or `one-off`). A fixed "loan run-rate" setting normalizes loan payments that land on uneven dates. Include a data-quality line.

### 4. Agentic layer

- A **proposals table**. The agent stages categorizations, transfer links and kind changes there. The user approves them in the review queue. The read-only fence stays in place for direct writes.
- New agent tools: `get_review_queue`, `monthly_pnl`, `savings_scorecard`, `propose_changes`.
- An **MCP endpoint** that exposes the same tools, so external agents (Codex, Claude, OpenClaw) can run weekly recon against ClawFin. While both ledgers run, the same agent can query both and compare them.

### 5. Remaining parity with Actual

- **Account reconciliation:** compare against a statement balance and flag the difference.
- **Sync status** for each institution, with clear auth-required errors.
- **Full CSV/JSON export** as a lock-in escape hatch.
- **Split transactions.** Build only if the reimbursement kind proves insufficient.

## When ClawFin Replaces Actual

ClawFin is "the better one" when all of these hold:

- Its monthly P&L matches the parallel Actual recon within a small tolerance for 2–3 consecutive months.
- Weekly cleanup takes less manual work than in Actual: fewer items in the queue, and no writes that silently fail to persist.
- The scorecard and P&L come straight from ClawFin, with no external agent assembling a report.

## Not Building

- Envelope or category budgets, and budget alerts.
- Multi-user support. Sharing is handled through reimbursements plus Splitwise.
- PDF report export, benchmark comparisons, ACB and capital-gains summaries, CRA integration, crypto, Supabase or cloud sync.
- In-app trade or DCA recommendations. Portfolio judgement stays outside the app.
- ML or anomaly-detection categorization beyond the LLM categorizer plus rules.
- A separate dev Docker Compose setup. It's low value for a single user.

## Evaluation Report Phase 2 Items

| Item | Decision |
|---|---|
| pytest fixtures | Keep, in step 0 |
| Regex rule editor | Keep, reshaped as the rule editor with dry-run in step 2 |
| Error boundary | Keep, in step 0 |
| Blocking sync DB calls in async SSE route | Low priority for a single user |
| Stream fallback bug in `api/client.js` | Fix opportunistically |
| Dev/prod environment parity | Skip |
