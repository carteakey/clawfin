# TODO

Roadmap and upcoming features for AutoFin.

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

## AI & Automation
- [x] **AI Performance Audit:** Improve categorization accuracy for edge-case merchants.
- [x] **Local Model Optimization:** Better support for structured output when using Ollama/local providers.

## Engineering & Debt
- [x] **Frontend Testing:** Implement Vitest/Playwright for core UI flows.
- [x] **API Documentation:** Auto-generate OpenAPI/Swagger docs for the FastAPI backend.

## QoL Backlog
- [x] **Destructive Confirmations:** Add confirmations for delete account, delete manual transaction, and bulk delete.
- [x] **Manual Account Empty State:** When no manual account exists, show a direct action before creating manual transactions.
- [x] **Clear Ledger Filters:** Add one-click reset for ledger filters and sorting.
- [x] **Account Source Badges:** Show Manual, SimpleFin, CSV, and Wealthsimple source badges in account rows.
- [x] **Manual Transaction Validation:** Validate date, amount, merchant, and account in the frontend before submit.
- [x] **Memo Search:** Display and search transaction memos in the ledger.
- [x] **Non-Manual Mutation Tests:** Test rejection of non-manual edit/delete paths.
