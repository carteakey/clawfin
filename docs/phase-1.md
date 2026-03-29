# ClawFin Phase 1 — Walkthrough

Phase 1 of ClawFin is officially complete! We've successfully transitioned from a complex, monolithic boilerplate to a lightweight, fast, and secure API-driven architecture that runs entirely on your local machine.

## What Was Accomplished

### 1. The Architecture Pivot (Client-Server)
We split the app into a true local-first appliance:
- **Backend (`/backend`)**: A robust, lightweight Python API powered by FastAPI and SQLAlchemy (SQLite), removing heavy dependencies to maximize speed and privacy.
- **Frontend (`/frontend`)**: A blazing-fast React 19 SPA built with Vite, utilizing Zustand for state management and styled with a custom Bloomberg-terminal-inspired "dense data" CSS framework.

### 2. Formidable Data Ingestion
ClawFin now automatically ingests your entire financial picture securely:
- **Canadian Auto-Detect CSV Parser**: Drop a CSV from TD, RBC, Scotiabank, BMO, or CIBC, and ClawFin instantly identifies the bank via header signatures, normalizes date parsing, and standardizes amounts.
- **Wealthsimple Integration**: Supports both Holdings and Activity CSV exports. The Holdings parser seamlessly extracts security types, tickers, and handles dual-currency market/book values without breaking a sweat, taking advantage of the "As Of" footer dates.
- **SimpleFin Sync**: Built a direct bridge client to import accounts and transactions seamlessly via the SimpleFin API (with a built-in mock mode for CI/CD).
- **Bulletproof Deduplication**: Every incoming transaction generates a unique SHA-256 hash containing a per-day sequence counter. This guarantees that buying identical coffees on the same day won't cause deduplication collisions.
- **Bank of Canada FX Rate Fetcher**: Automatically pulls the daily CAD/USD/EUR/GBP rates directly from the official Valet API to keep your foreign holdings accurate.

### 3. AI-Native Classification & Tools
We ripped out the bloated `litellm` library in favor of a sleek, secure, dependency-free `httpx` provider abstraction:
- **Batch Categorization**: New transaction merchants are grouped in batches and sent to the LLM for categorization. The resulting rules are cached locally in SQLite (as `CategoryRule` objects) so that "Loblaws" only ever costs 1 LLM inference for the lifetime of your app.
- **Unified Wire Format**: We locked the system to the OpenAI function-calling wire format. Whether you use Ollama (local, default), Anthropic, or OpenAI, `provider.py` automatically translates the tool-call blocks so `agent.py` never has to care which model is running.
- **6 Built-in Agent Tools**: The assistant can now natively execute queries for spending, account balances, real-time holdings, net worth, specific transaction searches, and even multi-year compounding savings simulations.

### 4. The Glass & Data Dashboard
We implemented a stunning, high-density React frontend specifically designed for heavy data:
- **The Brand Reality**: Fully translated the 7-color teal/ink `clawfin_brand.svg` logo into a comprehensive design system utilizing `Inter` for prose and `JetBrains Mono` for all tabular numbers.
- **Dashboard**: Features a responsive KPI strip with automatic period-over-period percentage deltas, a visual spending breakdown by Top Categories / Top Merchants, and a beautiful daily `Recharts` spending bar graph.
- **Holdings Explorer**: A dense, 32px-row table showing exact currency details, precise quantities, and color-coded total gains/losses.
- **The ⌘K Sidebar**: A globally accessible UI layer where the ClawFin agent slides in from the right. It streams in real-time (SSE streaming) and understands the conversation history, allowing rapid "what if" scenarios based on your live SQLite data.

## Docker Setup

The entire stack is containerized for appliance-like deployment:
- Run `docker compose up -d` for the standard backend + nginx frontend frontend.
- Run `docker compose --profile ai-local up -d` to automatically spin up the `ollama` sidecar. 

## Next Steps
You have a rock-solid, incredibly fast foundation. Phase 2 (the next phase of development) will focus on surfacing more advanced Budgeting/Goals logic, a multi-user abstraction layer if you want to host family members, and exposing an interface to let you tweak the AI's cached regex rules manually!
