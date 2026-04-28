# TODO

Roadmap and upcoming features for ClawFin.

## High Priority
- [x] **Manual Transactions:** Add ability to create, edit, and delete manual transactions for manual accounts.
- [x] **End-to-End Encryption:** Encrypt sensitive database fields (SimpleFin access URLs, API keys) at rest.
- [x] **Ledger Pagination:** Implement server-side pagination for the transactions list to handle thousands of rows efficiently.
- [x] **Mobile Optimization:** Audit and fix layout issues on small screens for the Brutalist design.

## Features
- [x] **Bulk Actions:** Ability to select multiple transactions for bulk categorization or deletion.
- [x] **Advanced Filtering:** Add date-range picker and amount-range filters to the Ledger view.
- [x] **CSV Export:** Export filtered ledger views back to CSV.
- [x] **Rule Management UI:** Dedicated interface to view, edit, and delete saved merchant categorization rules.
- [ ] **Split Transactions:** Support for splitting a single transaction into multiple categories.

## AI & Automation
- [x] **AI Performance Audit:** Improve categorization accuracy for edge-case merchants.
- [x] **Local Model Optimization:** Better support for structured output when using Ollama/local providers.
- [ ] **Briefing Customization:** Allow users to configure the day/time for automated briefings.

## Engineering & Debt
- [x] **Frontend Testing:** Implement Vitest/Playwright for core UI flows.
- [x] **API Documentation:** Auto-generate OpenAPI/Swagger docs for the FastAPI backend.
- [ ] **Dependency Audit:** Regular updates for Python and Node.js packages.

## QoL Backlog
- [x] **Destructive Confirmations:** Add confirmations for delete account, delete manual transaction, and bulk delete.
- [ ] **Inline Status System:** Replace alerts and silent catches with consistent inline success/error messages.
- [x] **Manual Account Empty State:** When no manual account exists, show a direct action before creating manual transactions.
- [ ] **Ledger URL State:** Preserve ledger filters, sorting, and page in URL query params.
- [ ] **Mutation Locking:** Add loading/disabled states to mutation buttons to prevent double submits.
- [x] **Clear Ledger Filters:** Add one-click reset for ledger filters and sorting.
- [x] **Account Source Badges:** Show Manual, SimpleFin, CSV, and Wealthsimple source badges in account rows.
- [ ] **Import Result Details:** Surface skipped counts, duplicate reasons, transfer-marked count, and stale SimpleFin accounts.
- [x] **Manual Transaction Validation:** Validate date, amount, merchant, and account in the frontend before submit.
- [ ] **Toast Messages:** Add a lightweight toast/status surface for short-lived success and failure messages.
- [x] **Memo Search:** Display and search transaction memos in the ledger.
- [ ] **Account Filter Search:** Add search for account chips when many accounts exist.
- [ ] **Saved Ledger Views:** Add quick views for Uncategorized, Manual only, Off-budget, Subscriptions, and Last 30 days.
- [ ] **Uncategorized Quick Filter:** Add a shortcut for category `Other`.
- [ ] **Rule Impact Preview:** Preview how many transactions a rule would affect before recategorizing.
- [ ] **Undo Category Change:** Allow undo after inline transaction recategorization.
- [ ] **Bulk Transfer/Other Actions:** Add bulk mark as Transfer and mark as Other.
- [x] **Non-Manual Mutation Tests:** Test rejection of non-manual edit/delete paths.
- [ ] **SimpleFin Encryption Tests:** Test encrypted SimpleFin credential storage.
- [ ] **API Shape Tests:** Add response shape tests for ledger filters and CSV export.
- [ ] **API Client Tests:** Add frontend tests for API client parameter generation.
- [ ] **Default Secret Warning:** Warn at startup when `CLAWFIN_SECRET_KEY` is still the default.
- [ ] **Backup Failure Handling:** Improve database export errors for missing or locked DB files.
- [ ] **Advanced Filter Disclosure:** Collapse less common ledger filters behind an Advanced control.
- [ ] **Sticky Ledger Header:** Keep ledger table header sticky inside the scroll container.
- [ ] **Row Density Toggle:** Add compact and comfortable ledger density modes.
- [ ] **Ledger Keyboard Shortcuts:** Add `/` search focus and `Esc` clear selection.
- [ ] **Selection Count Placement:** Surface selected-row count near the table header.
- [ ] **Icon Action Polish:** Use icon-only buttons for row actions and labeled buttons for global actions.
- [ ] **Mobile Account Chips:** Improve account chips with horizontal scrolling on mobile.
- [ ] **Manual Merchant Normalization:** Normalize merchant casing for manual entries.
- [ ] **Merchant Merge Helper:** Add helper to merge duplicate merchant names.
- [ ] **Category Suggestions:** Suggest categories while typing a manual transaction merchant.
- [ ] **Categorization Diagnostics:** Show why a transaction received a category.
- [ ] **Import Preview:** Preview CSV rows before committing an import.
