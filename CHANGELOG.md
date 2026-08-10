# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-04-25

### Added
- **Account Management:** Support for manual account creation, account deletion, and live account type reclassification.
- **Budgeting Controls:** Introduced "On-Budget" vs "Off-Budget" account flags to exclude investment or tracking accounts from cash-flow reporting.
- **Ledger Enhancements:** Added "Include Off-Budget" toggle and alphabetical sorting by Category.
- **Briefings API:** Added a high-context Weekly Briefing engine for automated financial status reports.
- **UX Polish:** Improved navigation structure, added account sync health indicators, and interactive chart animations.
- **Chat:** Added "Clear Chat" functionality and UI-safe briefing presets.

### Fixed
- Resolved CORS issues and 500 errors in the Briefings API.
- Fixed account filtering when clicking through from the Accounts view.
- Standardized recurring transaction detection window to 5-45 days for better reliability.
- Patched several frontend syntax errors and white screen crashes.

### Changed
- Simplified Briefings API by removing redundant `daily` period and merchant redaction flags.
- Made SimpleFin stale sync thresholds configurable via environment variables.

## [0.0.3] - 2026-04-16

### Added
- **Redesign:** Implemented a new Brutalist Minimalist design system across the entire UI.
- **Recurring Transactions:** Automated detection of subscriptions, bills, and cadence-based outflows.
- **Planning:** New module for financial planning and projections.
- **Command Palette:** Quick-action menu accessible via `Cmd+K`.
- **Snapshots:** Support for historical net worth snapshots.

## [0.0.2] - 2026-04-01

### Fixed
- **Sync:** Patched SimpleFin API synchronization history limits.
- **Deduplication:** Resolved crashes related to large transaction payload deduplication.

## [0.0.1] - 2026-03-28

### Added
- **Initial Alpha Foundation:** 
  - FastAPI backend with SQLAlchemy models and JWT authentication.
  - Data ingestion pipeline supporting CSV (TD, RBC, Scotiabank, BMO, CIBC), Wealthsimple, and SimpleFin.
  - AI Layer with provider abstraction and natural language financial agent.
  - React frontend with a custom brand design system.
  - Docker deployment configuration (Compose, Dockerfiles, Nginx).
