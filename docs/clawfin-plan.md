# ClawFin 🐾
### Your AI grip on Canadian finances

---

## What is ClawFin?

ClawFin is a personal AI finance hub built for Canadians. It connects your real bank accounts, investment holdings, and legacy transaction history into a single unified ledger — then puts an AI agent on top so you can ask questions, run simulations, and get smart reports without ever opening a spreadsheet.

---

## Brand

**Name:** ClawFin  
**Tagline:** Your AI grip on Canadian finances  
**Logo concept:** Three diagonal claw strokes (bear/eagle claw) doubling as an upward chart  
**Primary colour:** Teal green `#1D9E75` — money without being banker-blue  
**Palette:** Teal · Dark teal · Ink · Muted gray  
**Tone:** Smart, analytical, quietly Canadian. A tool, not a bank.

---

## Data Sources

### SimpleFin (via Bridge API)
- Real-time bank transaction feeds
- Connects checking, savings, credit cards
- Polled daily via the SimpleFin Bridge API
- Covers most major Canadian financial institutions

### Wealthsimple
- No public API — export-based workflow
- User exports CSV / PDF holding reports periodically
- ClawFin parses and tracks portfolio over time
- Supports TFSA, RRSP, FHSA, margin accounts

### Bank CSVs
- Manual export from TD, RBC, Scotiabank, BMO, CIBC, etc.
- ClawFin normalizes each bank's format into a unified schema
- Deduplication handled automatically across sources

### Future sources
- CRA My Account (contribution room, NOA)
- Crypto wallets
- Employer stock / ESPP plans

---

## Core Data Model

Everything funnels into a single unified ledger:

| Entity | Fields |
|---|---|
| **Transaction** | date, amount, merchant, category, account, source, currency |
| **Holding** | asset, ticker, quantity, book value, market value, as-of date, account |
| **Account** | institution, type (chequing/TFSA/RRSP/FHSA/margin), currency |
| **Snapshot** | net worth, assets, liabilities, date |

---

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                    DATA SOURCES                     │
│  SimpleFin API  │  Wealthsimple CSV  │  Bank CSVs  │
└────────────────────────┬────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────┐
│              INGESTION + NORMALIZER                 │
│  Dedup · Category tagging · Schema mapping          │
│  TFSA/RRSP/FHSA room tracking · ACB calculation     │
└────────────────────────┬────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────┐
│           UNIFIED LEDGER (SQLite / Supabase)        │
│  Transactions · Holdings · Accounts · Snapshots     │
└────────────────────────┬────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────┐
│                  AI AGENT LAYER                     │
│  Orchestrator (Claude + tool use)                   │
│  ├── DB query tool     (read ledger)                │
│  ├── Simulator tool    (what-if projections)        │
│  └── Report tool       (generate PDFs)              │
└──────┬──────────────┬──────────────┬───────┬────────┘
       ↓              ↓              ↓       ↓
  Spending        Investment      Net     AI Chat
  Report          Report          Worth   Interface
```

---

## The Three Report Pillars

### 1. Spending Report
- Monthly and weekly breakdowns by category (groceries, dining, subscriptions, transit, etc.)
- Trend lines over time — spot creeping expenses
- Anomaly detection ("You spent 40% more on food in March")
- Budget vs. actual tracking
- Merchant-level drill-down
- Top spending leaks highlighted automatically

### 2. Investment Report
- Portfolio allocation by asset class, sector, and geography
- Performance vs. benchmarks (TSX Composite, S&P 500, XEQT)
- TFSA / RRSP / FHSA contribution room remaining
- Unrealized gains and losses
- Adjusted cost base (ACB) tracking for capital gains
- Dividend income summary

### 3. Net Worth Over Time
- Total assets minus liabilities, trended monthly
- Breakdown: cash, registered accounts, non-registered, real estate, debt
- Progress toward user-defined goals (retirement, home purchase, FIRE)

---

## AI Agent — What You Can Ask

The ClawFin AI agent has full read access to your unified ledger and can answer natural language questions, run simulations, and generate reports on demand.

**Spending questions**
- "How much did I spend on eating out last quarter?"
- "What are my three biggest spending leaks?"
- "How much have I spent on subscriptions this year?"

**Investment questions**
- "If I move $10K from my TFSA cash to XEQT, what does my allocation look like?"
- "Am I on track to max my RRSP this year?"
- "What's my portfolio return vs the TSX this year?"

**Simulation questions**
- "What happens to my net worth if I invest $500/month for 10 years at 7%?"
- "If I cut dining out by half, how much extra could I invest per year?"
- "Show me my TFSA balance at 65 if I max it every year from now."

**Read + simulate only** — ClawFin never executes trades or transfers. You get the insight, you take the action.

---

## Tech Stack

| Layer | Choice | Notes |
|---|---|---|
| Bank data | SimpleFin Bridge API | OAuth-based, Canadian bank support |
| Storage | SQLite (local) or Supabase (cloud) | Start local, migrate if needed |
| Backend | Python (FastAPI) or Node (Express) | Python preferred for data work |
| AI agent | Claude API with tool use | Orchestrator + 3 tools |
| Frontend | React + Recharts | Spending/investment visualizations |
| Auth | Clerk or local session | Simple to start |
| PDF export | WeasyPrint (Python) or Puppeteer | For shareable reports |

---

## Build Phases

### Phase 1 — Data Foundation
- SimpleFin Bridge API connection
- CSV import for Wealthsimple + bank exports
- Unified transaction schema + deduplication
- Auto-categorization (rule-based to start)
- Basic account and holding store

### Phase 2 — Reports
- Spending dashboard (categories, trends, anomalies)
- Investment snapshot (allocation, performance, ACB)
- Net worth tracker (monthly snapshots, goal progress)

### Phase 3 — AI Chat
- Claude agent with DB query tool
- Natural language Q&A over your financial data
- Simulator tool for projections
- Report generation tool (PDF export)

### Phase 4 — Automation & Intelligence
- ML-based auto-categorization
- Recurring transaction detection
- Budget alerts and threshold notifications
- TFSA/RRSP contribution room alerts
- Canadian tax-aware summaries (ACB, capital gains estimates)

---

## Key Design Decisions

**Local vs. cloud**  
Start local (SQLite, no server). Add Supabase cloud sync in Phase 3 for multi-device access. Local-first means better privacy and no infrastructure costs during development.

**Wealthsimple sync frequency**  
Manual CSV upload for now. A browser-based scraper is possible but sits in a grey area — evaluate after MVP.

**Canadian tax awareness**  
TFSA/RRSP/FHSA room tracking is in scope from Phase 1. ACB tracking for capital gains in Phase 2. Full tax report generation (T5, T3) is Phase 4+.

**AI safety boundary**  
Read and simulate only. No trade execution, no bank transfers, no write access to any financial account. ClawFin is a co-pilot, not an autopilot.

---

## Repo Structure (proposed)

```
clawfin/
├── ingestion/
│   ├── simplefin.py        # SimpleFin Bridge API client
│   ├── wealthsimple.py     # CSV/PDF parser
│   └── bank_csv.py         # Multi-bank CSV normalizer
├── ledger/
│   ├── models.py           # Transaction, Holding, Account, Snapshot
│   └── db.py               # SQLite / Supabase client
├── agent/
│   ├── orchestrator.py     # Claude agent + tool routing
│   ├── tools/
│   │   ├── query.py        # DB query tool
│   │   ├── simulator.py    # Projection tool
│   │   └── report.py       # PDF generation tool
├── api/
│   └── main.py             # FastAPI routes
├── frontend/
│   ├── src/
│   │   ├── pages/
│   │   │   ├── Spending.jsx
│   │   │   ├── Investments.jsx
│   │   │   ├── NetWorth.jsx
│   │   │   └── Chat.jsx
│   │   └── components/
└── README.md
```

---

## What Makes ClawFin Different

- **Canadian-first** — TFSA, RRSP, FHSA, ACB, CAD/USD handling built in from day one
- **AI that knows your numbers** — not generic advice, answers grounded in your actual data
- **Privacy-first** — local-first storage, no selling data, no ads
- **Dev-grade tool** — open, extensible, yours to run and modify
- **Read-only safety** — the AI can advise, never act

---

*ClawFin — get a grip on your money.*
