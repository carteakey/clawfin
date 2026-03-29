# ClawFin — Implementation Plan (v3 · Final)

## Philosophy

**Form over function. Density over style. AI-native.**

Bloomberg Terminal meets personal finance. Dense, dark, monospace numbers, no wasted pixels. AI is woven through — categorizing transactions, answering questions, surfacing insights. Self-hosted, Docker-deployable, privacy-first.

---

## Design Decisions (Locked)

| # | Decision | Answer |
|---|---|---|
| 1 | First-run experience | Dual path: "Connect SimpleFin" + "Drop a CSV" side by side |
| 2 | SimpleFin | User has account; build full setup flow |
| 3 | AI provider | Direct httpx to OpenAI-compatible APIs; default Ollama |
| 4 | Database | SQLite (file-backed, volume mount) |
| 5 | AI architecture | Built-in agent only (no MCP) |
| 6 | Auth | Simple password gate via `CLAWFIN_PASSWORD` env var |
| 7 | Bank CSVs | All Big 5: TD, RBC, Scotiabank, BMO, CIBC |
| 8 | Wealthsimple | Holdings (priority) + activity (both) |
| 9 | Chat UI | Collapsible sidebar, ⌘K toggle |
| 10 | Currency | Multi-currency; Bank of Canada daily FX rates |
| 11 | SimpleFin sync | Manual "Sync Now" button only |
| 12 | Contribution room | Optional manual input for TFSA/RRSP/FHSA |
| 13 | Categories | Customizable; 12 defaults + reset-to-defaults |
| 14 | Dev workflow | Local dev (`uvicorn` + `npm run dev`); Docker for deploy |
| 15 | Holdings view | Simple table from Wealthsimple CSV data |

**Account types:** Chequing, Savings, Credit Card, TFSA, RRSP, FHSA, Margin, Crypto

**Default categories (12):** Groceries, Dining, Transit, Subscriptions, Housing, Utilities, Transfer, Income, Entertainment, Health, Shopping, Other

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         DOCKER COMPOSE                          │
│                                                                 │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  FRONTEND (Vite build → nginx :3000)                      │ │
│  │  Dashboard │ Holdings │ Transactions │ Chat (⌘K) │ Settings│ │
│  └──────────────────────────┬─────────────────────────────────┘ │
│                             │ REST API                          │
│  ┌──────────────────────────┴─────────────────────────────────┐ │
│  │  BACKEND (Python · FastAPI :8000)                          │ │
│  │                                                            │ │
│  │  ┌────────────┐ ┌─────────────┐ ┌───────────────────────┐ │ │
│  │  │ SimpleFin  │ │ CSV Ingest  │ │ AI Agent (httpx)      │ │ │
│  │  │ Client     │ │ + Normalize │ │ tools: query, cat,    │ │ │
│  │  │            │ │ + Wlthsmpl  │ │   simulate            │ │ │
│  │  └─────┬──────┘ └──────┬──────┘ └──────────┬────────────┘ │ │
│  │        └───────────────┴───────────────────┘              │ │
│  │                        ↓                                   │ │
│  │  ┌─────────────────────┴──────────────────────────────┐   │ │
│  │  │  SQLite + SQLAlchemy  (volume: /data/clawfin.db)   │   │ │
│  │  └────────────────────────────────────────────────────┘   │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                 │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  OLLAMA (optional --profile ai-local)                     │ │
│  └────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
         ↕                    ↕                    ↕
   SimpleFin Bridge    Bank of Canada FX     OpenAI/Anthropic
                                              (remote, optional)
```

---

## Tech Stack

| Layer | Choice |
|---|---|
| **Backend** | Python 3.12 · FastAPI · SQLAlchemy · Alembic · SQLite |
| **AI** | Direct httpx → OpenAI-compatible APIs (Ollama / OpenAI / Anthropic) |
| **FX** | Bank of Canada daily rate CSV |
| **Frontend** | Vite · React 19 · Zustand · Recharts · Lucide |
| **Styling** | Vanilla CSS · Inter + JetBrains Mono |
| **Deploy** | Docker Compose (backend + nginx + optional Ollama) |

---

## Repo Structure

```
clawfin/
├── docker-compose.yml
├── Dockerfile.backend
├── Dockerfile.frontend
├── .env.example
│
├── backend/
│   ├── requirements.txt
│   ├── main.py                    # FastAPI app + auth middleware
│   ├── config.py                  # Settings from env vars
│   ├── db/
│   │   ├── models.py              # Transaction, Holding, Account, Snapshot, etc.
│   │   ├── database.py            # Engine + session
│   │   └── seed.py                # Default categories
│   ├── alembic/                   # Schema migrations from day one
│   │   └── versions/
│   ├── ingestion/
│   │   ├── simplefin.py           # Bridge API client
│   │   ├── parser.py              # CSV orchestrator + bank auto-detect
│   │   ├── normalizers/
│   │   │   ├── td.py
│   │   │   ├── rbc.py
│   │   │   ├── scotiabank.py
│   │   │   ├── bmo.py
│   │   │   └── cibc.py
│   │   ├── wealthsimple.py        # Holdings + activity CSV parser
│   │   ├── categorizer.py         # AI batch by merchant (cached) + rule fallback
│   │   ├── dedup.py               # SHA256 hash dedup (sequence counter for same-day)
│   │   └── fx.py                  # Bank of Canada FX rate fetcher
│   ├── ai/
│   │   ├── provider.py            # Direct httpx OpenAI-compatible client
│   │   ├── agent.py               # Agent loop + tool dispatch
│   │   └── tools.py               # query_ledger, categorize, simulate
│   └── routers/
│       ├── auth.py                # POST /api/auth/login
│       ├── transactions.py
│       ├── holdings.py
│       ├── import_data.py         # CSV + SimpleFin + Wealthsimple
│       ├── dashboard.py           # Pre-computed KPIs + breakdown
│       ├── chat.py                # SSE streaming
│       └── settings.py            # AI config, categories, contribution room
│
├── frontend/
│   ├── index.html
│   ├── vite.config.js
│   ├── package.json
│   ├── nginx.conf
│   └── src/
│       ├── main.jsx
│       ├── App.jsx
│       ├── index.css              # Design system (brand tokens)
│       ├── api/
│       │   └── client.js
│       ├── store/
│       │   └── ledger.js          # Zustand
│       ├── components/
│       │   ├── layout/            # Shell, Sidebar, Header
│       │   ├── dashboard/         # KpiStrip, SpendingGrid, Sparkline, etc.
│       │   ├── holdings/          # Holdings table
│       │   ├── transactions/      # TxTable, TxRow, TxFilters
│       │   ├── chat/              # Collapsible chat sidebar
│       │   ├── import/            # Onboarding + CSV drop + SimpleFin setup
│       │   ├── settings/          # AI config, categories, contribution room
│       │   ├── auth/              # Login screen
│       │   └── shared/            # Currency, Delta, Sparkline
│       └── utils/
│           ├── format.js
│           ├── categories.js
│           └── constants.js
│
└── README.md
```

---

## Build Order

### Phase 1a — Foundation
1. Project scaffold (Docker, backend shell, frontend shell)
2. Design system (`index.css`)
3. Data layer (SQLAlchemy models, DB init)
4. Auth middleware + login screen

### Phase 1b — Data In
5. CSV ingestion pipeline (parser + 5 normalizers + dedup)
6. Categorizer (AI-first + rule fallback)
7. Wealthsimple parser (holdings + activity)
8. SimpleFin client (setup token exchange + sync)
9. FX rate fetcher (Bank of Canada)

### Phase 1c — Data Out (UI)
10. Layout shell (sidebar, header, routing)
11. Dashboard (KPI strip, spending grid, sparklines, top merchants)
12. Holdings view (table)
13. Transaction explorer (dense table + filters)
14. Import flow (onboarding, drop zone, SimpleFin setup, preview)

### Phase 1d — AI + Polish
15. AI provider setup (litellm config)
16. Agent + tools (query, categorize, simulate)
17. Chat sidebar (collapsible, ⌘K, SSE streaming)
18. Settings (AI config, categories, contribution room)
19. Docker Compose + Dockerfiles

---

## Dashboard Layout

```
┌───────────────────────────────────────────────────────────────────────────┐
│ 🐾 ClawFin  │ Dashboard │ Holdings │ Transactions │ ⚙ │  ⬆ Import │ 💬 │
├─────────────┼─────────────────────────────────────────────┬───────────────┤
│             │ ┌─────────┐┌─────────┐┌─────────┐┌───────┐ │ ░░░░░░░░░░░░ │
│  ACCOUNTS   │ │ Income  ││Expenses ││Savings  ││ N.W.  │ │ ░ ⌘K CHAT  ░ │
│  ─────────  │ │ $6,240  ││ $4,180  ││ 33.0%   ││$84.2K │ │ ░░░░░░░░░░░░ │
│  🏦 TD Chq  │ │ ▁▂▃▃▄▅▅ ││ ▅▄▃▃▄▅▆ ││ ▃▄▅▅▆▅▄ ││▁▂▃▄▅▆│ │   collapsed  │
│  💳 RBC Visa│ │ ▲ +2.1% ││ ▼ -3.4% ││ ▲+5.2pp ││▲1.8% │ │   by default │
│  📈 TFSA    │ └─────────┘└─────────┘└─────────┘└───────┘ │              │
│  📈 RRSP    │                                             │              │
│             │ SPENDING BY CATEGORY        [30d ▾]         │              │
│ ──────────  │ ┌────────────────────────────────────────┐   │              │
│  SIMPLEFIN  │ │ Category    Amount   %   Δ    Trend   │   │              │
│  ● Synced   │ │ Housing     $1,800 43%  ━━   ▅▅▅▅▅▅  │   │              │
│  2h ago     │ │ Groceries     $620 15%  ▲3%  ▃▃▄▅▄▃ │   │              │
│             │ │ Dining        $340  8%  ▼8%  ▅▄▃▃▂▃ │   │              │
│ ──────────  │ └────────────────────────────────────────┘   │              │
│  🤖 Ollama  │                                             │              │
│  llama3.1   │ TOP MERCHANTS          DAILY SPEND          │              │
│             │ ┌────────────────┐    ┌────────────────┐    │              │
│  1,847 txs  │ │ Loblaws $280 12│    │▃▅▂▇▃▄▅▂▆▃▅▃▂▅│    │              │
│  5 accounts │ │ Uber    $180  8│    │M T W T F S S  │    │              │
└─────────────┴─┴────────────────┘────┴────────────────┘────┴──────────────┘
```

---

## Verification Plan

| Step | Method | What |
|---|---|---|
| 1 | `pytest` | Ingestion normalizers, dedup, categorizer, FX, API routes |
| 2 | `vitest` | Frontend store logic, formatting utils |
| 3 | Browser | Upload test CSV → dashboard populates |
| 4 | Browser | SimpleFin sync → new transactions appear |
| 5 | Browser | Chat → ask about spending → get answer |
| 6 | Browser | Screenshot final dashboard for review |
| 7 | Manual | User drops real bank CSV, confirms numbers |
