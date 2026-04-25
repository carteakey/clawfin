# TODO

Roadmap and upcoming features for ClawFin.

## High Priority
- [ ] **Manual Transactions:** Add ability to create, edit, and delete manual transactions for manual accounts.
- [ ] **End-to-End Encryption:** Encrypt sensitive database fields (SimpleFin access URLs, API keys) at rest.
- [ ] **Ledger Pagination:** Implement server-side pagination for the transactions list to handle thousands of rows efficiently.
- [ ] **Mobile Optimization:** Audit and fix layout issues on small screens for the Brutalist design.

## Features
- [ ] **Bulk Actions:** Ability to select multiple transactions for bulk categorization or deletion.
- [ ] **Advanced Filtering:** Add date-range picker and amount-range filters to the Ledger view.
- [ ] **CSV Export:** Export filtered ledger views back to CSV.
- [ ] **Rule Management UI:** Dedicated interface to view, edit, and delete saved merchant categorization rules.
- [ ] **Split Transactions:** Support for splitting a single transaction into multiple categories.

## AI & Automation
- [ ] **AI Performance Audit:** Improve categorization accuracy for edge-case merchants.
- [ ] **Local Model Optimization:** Better support for structured output when using Ollama/local providers.
- [ ] **Briefing Customization:** Allow users to configure the day/time for automated briefings.

## Engineering & Debt
- [ ] **Frontend Testing:** Implement Vitest/Playwright for core UI flows.
- [ ] **API Documentation:** Auto-generate OpenAPI/Swagger docs for the FastAPI backend.
- [ ] **Dependency Audit:** Regular updates for Python and Node.js packages.
