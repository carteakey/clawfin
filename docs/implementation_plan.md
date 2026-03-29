# ClawFin — Implementation Plan

## Philosophy

**Form over function. Density over style.**

This is not a pastel fintech app with one big number and a "you're doing great!" banner. This is a financial cockpit — inspired by Bloomberg Terminal, Grafana dashboards, and racing telemetry. Every pixel earns its place by showing data. The UI should feel like opening the hood of your finances, not looking at a brochure.

Design principles:
- **Data density**: Show as much useful information as possible without scrolling. Tables, sparklines, inline deltas, mini-charts. No hero sections with a single metric.
- **Dark-first**: Deep ink backgrounds (`#0A0F0D`), teal accents (`#1D9E75`), and high-contrast data. Your financial data deserves a command center, not a greeting card.
- **Monospace numbers**: All financial figures in a monospace font (JetBrains Mono / IBM Plex Mono). Numbers should align. Always.
- **No empty states as dead ends**: If there's no data yet, the empty state is the import flow itself — not a sad illustration.
- **Motion with purpose**: Subtle number-tick animations on value changes, smooth transitions between time ranges. No decorative animation.

---

## What We're Building (Phase 1)

A single-page, local-first financial dashboard that ingests Canadian bank CSVs and displays a dense, information-rich overview. No backend server. No auth. Just a local tool that turns your messy CSV exports into a Bloomberg-style personal finance terminal.

### Scope

| In scope | Out of scope (for now) |
|---|---|
| CSV import (TD, RBC, Scotiabank, BMO, CIBC) | SimpleFin API integration |
| Transaction normalization + dedup | Wealthsimple portfolio tracking |
| Auto-categorization (rule-based) | AI chat agent |
| Spending breakdown dashboard | PDF report generation |
| Net worth snapshot (manual accounts) | Multi-device sync |
| Dark-mode terminal UI | Mobile layout |

---

## Architecture

```
┌──────────────────────────────────────────────────────┐
│                   BROWSER (Vite + React)              │
│                                                       │
│  ┌─────────────┐ ┌──────────────┐ ┌───────────────┐  │
│  │  CSV Drop    │ │  Dashboard   │ │  Tx Explorer  │  │
│  │  Zone        │ │  (Dense)     │ │  (Table)      │  │
│  └──────┬──────┘ └──────┬───────┘ └───────┬───────┘  │
│         │               │                 │           │
│  ┌──────┴───────────────┴─────────────────┴───────┐  │
│  │            Ledger Store (Zustand)               │  │
│  │  Transactions · Accounts · Snapshots · Rules    │  │
│  └──────────────────────┬──────────────────────────┘  │
│                         │                             │
│  ┌──────────────────────┴──────────────────────────┐  │
│  │         IndexedDB (Dexie.js)                    │  │
│  │  Persistent local storage — survives refresh    │  │
│  └─────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────┘
```

**Why no backend?** This is a local-first finance tool. Your bank data never leaves your machine. A Python server adds deployment complexity and a privacy question that doesn't need to exist yet. Everything runs in the browser — CSV parsing, categorization, storage (IndexedDB via Dexie), and rendering.

---

## Tech Stack

| Layer | Choice | Why |
|---|---|---|
| Build | Vite + React 19 | Fast, modern, no boilerplate |
| Styling | Vanilla CSS (CSS custom properties) | Full control over the dense layout; no utility class bloat |
| State | Zustand | Lightweight, no provider hell |
| Storage | Dexie.js (IndexedDB) | Persistent, client-side, handles large datasets |
| CSV parsing | Papa Parse | Battle-tested, handles edge cases |
| Charts | Recharts (mini) + custom SVG sparklines | Recharts for larger charts, hand-rolled sparklines for inline density |
| Fonts | Inter (UI) + JetBrains Mono (numbers) | Clean + aligned |
| Icons | Lucide React | Consistent, lightweight |

---

## Repo Structure

```
clawfin/
├── index.html
├── vite.config.js
├── package.json
├── public/
│   └── favicon.svg
├── src/
│   ├── main.jsx                  # Entry point
│   ├── App.jsx                   # Layout shell + routing
│   ├── index.css                 # Design system: tokens, reset, base
│   │
│   ├── db/
│   │   ├── schema.js             # Dexie DB schema (transactions, accounts, snapshots)
│   │   └── seed.js               # Optional demo data for development
│   │
│   ├── ingestion/
│   │   ├── parser.js             # CSV parsing orchestrator
│   │   ├── normalizers/
│   │   │   ├── td.js             # TD-specific format mapper
│   │   │   ├── rbc.js            # RBC-specific format mapper
│   │   │   ├── scotiabank.js     # Scotiabank-specific format mapper
│   │   │   ├── bmo.js            # BMO-specific format mapper
│   │   │   └── cibc.js           # CIBC-specific format mapper
│   │   ├── categorizer.js        # Rule-based category tagger
│   │   └── dedup.js              # Deduplication logic
│   │
│   ├── store/
│   │   └── ledger.js             # Zustand store: transactions, accounts, derived state
│   │
│   ├── components/
│   │   ├── layout/
│   │   │   ├── Shell.jsx         # App chrome: sidebar + header + content area
│   │   │   ├── Sidebar.jsx       # Navigation + account summary
│   │   │   └── Header.jsx        # Breadcrumb + time range selector + import trigger
│   │   │
│   │   ├── dashboard/
│   │   │   ├── Dashboard.jsx     # Main dense dashboard grid
│   │   │   ├── KpiStrip.jsx      # Top bar: income / expenses / savings rate / net worth
│   │   │   ├── SpendingGrid.jsx  # Category breakdown as dense data grid
│   │   │   ├── Sparkline.jsx     # Inline SVG sparkline component
│   │   │   ├── TrendBadge.jsx    # ▲ +12% / ▼ -3% inline badge
│   │   │   ├── MiniChart.jsx     # Small area/bar chart for category trends
│   │   │   └── TimeRange.jsx     # 7d / 30d / 90d / YTD / 1Y / All selector
│   │   │
│   │   ├── transactions/
│   │   │   ├── TxTable.jsx       # Dense, sortable, filterable transaction table
│   │   │   ├── TxRow.jsx         # Single transaction row with inline category edit
│   │   │   └── TxFilters.jsx     # Filter bar: category, account, date range, amount
│   │   │
│   │   ├── import/
│   │   │   ├── ImportModal.jsx   # Full-screen import overlay
│   │   │   ├── DropZone.jsx      # Drag-and-drop CSV target
│   │   │   ├── BankDetector.jsx  # Auto-detect bank from CSV headers
│   │   │   └── ImportPreview.jsx # Preview parsed rows before confirming
│   │   │
│   │   └── shared/
│   │       ├── Currency.jsx      # Formatted CAD/USD display with monospace
│   │       ├── Delta.jsx         # Period-over-period change display
│   │       └── EmptyState.jsx    # Contextual empty states that guide to import
│   │
│   └── utils/
│       ├── format.js             # Number/date/currency formatting
│       ├── categories.js         # Category definitions + icons + colors
│       └── constants.js          # App-wide constants
│
└── README.md
```

---

## Proposed Changes (Build Order)

### 1. Project Scaffold

#### [NEW] package.json, vite.config.js, index.html
- Init Vite + React project
- Install dependencies: `react`, `react-dom`, `zustand`, `dexie`, `papaparse`, `recharts`, `lucide-react`
- Google Fonts link for Inter + JetBrains Mono

---

### 2. Design System

#### [NEW] [index.css](file:///Users/kchauhan/repos/clawfin/src/index.css)
The entire visual identity lives here. This is the most important file in the project.

- **Color tokens**: ink backgrounds, teal accents, semantic colors for gain/loss/neutral
- **Typography scale**: tight, dense — 11px–14px for data, 18px max for section headers
- **Spacing system**: 4px base grid. Everything aligns.
- **Component primitives**: cards, tables, badges, form controls — all dark-theme
- **Data-specific styles**: tabular-nums, monospace for financial figures, right-aligned amounts
- **Dense table styles**: compact row height (32px), subtle row separators, hover highlights
- **Scrollbar styling**: thin, dark, unobtrusive

```css
/* Flavor of the design system */
:root {
  --bg-base: #0A0F0D;
  --bg-surface: #111916;
  --bg-raised: #19231E;
  --border: #1E2B25;
  --text-primary: #E8E6DF;
  --text-secondary: #888780;
  --text-muted: #555550;
  --accent: #1D9E75;
  --accent-dim: #0F6E56;
  --gain: #34D399;
  --loss: #F87171;
  --font-ui: 'Inter', system-ui, sans-serif;
  --font-mono: 'JetBrains Mono', ui-monospace, monospace;
}
```

---

### 3. Data Layer

#### [NEW] [schema.js](file:///Users/kchauhan/repos/clawfin/src/db/schema.js)
Dexie.js database definition:
- `transactions`: date, amount, merchant, normalizedMerchant, category, account, source, currency, hash (for dedup)
- `accounts`: id, institution, name, type, currency, balance
- `snapshots`: date, netWorth, totalAssets, totalLiabilities
- `categoryRules`: pattern (regex/string), category, priority

#### [NEW] [ledger.js](file:///Users/kchauhan/repos/clawfin/src/store/ledger.js)
Zustand store providing:
- Transaction CRUD with IndexedDB sync
- Derived selectors: spending by category, monthly totals, trends, income vs. expense
- Time-range filtering (7d/30d/90d/YTD/1Y/All)
- Import state management

---

### 4. CSV Ingestion Pipeline

#### [NEW] [parser.js](file:///Users/kchauhan/repos/clawfin/src/ingestion/parser.js)
- Accepts raw CSV text, auto-detects bank from header row
- Routes to the correct normalizer
- Returns unified transaction array

#### [NEW] Normalizers: [td.js](file:///Users/kchauhan/repos/clawfin/src/ingestion/normalizers/td.js), [rbc.js](file:///Users/kchauhan/repos/clawfin/src/ingestion/normalizers/rbc.js), etc.
- Each normalizer maps bank-specific columns to the unified schema
- Handles date format differences, sign conventions, description parsing

#### [NEW] [categorizer.js](file:///Users/kchauhan/repos/clawfin/src/ingestion/categorizer.js)
- Rule-based: match merchant strings against category patterns
- Default categories: Groceries, Dining, Transit, Subscriptions, Housing, Utilities, Transfer, Income, Other
- Returns categorized transactions

#### [NEW] [dedup.js](file:///Users/kchauhan/repos/clawfin/src/ingestion/dedup.js)
- Hash-based dedup: hash(date + amount + merchant + account)
- Skips transactions already in the DB

---

### 5. UI Components (Build Order)

#### [NEW] Shell, Sidebar, Header
- Fixed sidebar (48px collapsed / 220px expanded): account list, nav, storage stats
- Header: current view title, time range selector, "Import" button
- Content area fills remaining space with CSS Grid

#### [NEW] Dashboard (the centerpiece)
- **KPI Strip**: 4-column row at the top — Monthly Income, Monthly Expenses, Savings Rate, Net Worth. Each with sparkline + trend badge.
- **Spending Grid**: Dense table/grid showing each category with: total spend, % of total, vs. last period delta, sparkline of last 6 months. Sorted by spend descending.
- **Top Merchants**: Top 10 merchants by spend, with frequency count and average transaction size.
- **Daily Spend Heatmap or Bar**: Small bar chart showing daily spend for the selected period.

#### [NEW] Transaction Explorer
- Dense sortable table: date | merchant | category | account | amount
- Inline category override (click to change)
- Filter bar: multi-select category, account, date range, amount range
- Search: fuzzy match on merchant name
- Row height: 32px. Show 30+ rows without scrolling.

#### [NEW] Import Flow
- Modal overlay with drag-and-drop zone
- Auto-detect bank from headers, show detected bank badge
- Preview table of parsed transactions before committing
- Progress indicator for large files
- Summary after import: X new transactions, Y duplicates skipped

---

## The Dashboard Layout (ASCII Wireframe)

```
┌────────────────────────────────────────────────────────────────┐
│ ▸ ClawFin   │ Dashboard     │ 7d  30d [90d] YTD 1Y All │ ⬆ Import │
├─────────────┼───────────────────────────────────────────────────┤
│             │ ┌──────────┐┌──────────┐┌──────────┐┌──────────┐ │
│  ACCOUNTS   │ │ Income   ││ Expenses ││ Savings  ││ Net Worth│ │
│  ─────────  │ │ $6,240   ││ $4,180   ││ 33.0%    ││ $84,200  │ │
│  TD Cheq.   │ │ ▁▂▃▃▄▅▅  ││ ▅▄▃▃▄▅▆  ││ ▃▄▅▅▆▅▄  ││ ▁▂▃▄▅▆▇  │ │
│  RBC Visa   │ │ ▲ +2.1%  ││ ▼ -3.4%  ││ ▲ +5.2pp ││ ▲ +1.8% │ │
│  TFSA       │ └──────────┘└──────────┘└──────────┘└──────────┘ │
│  RRSP       │                                                   │
│             │ SPENDING BY CATEGORY                              │
│  ─────────  │ ┌─────────────────────────────────────────────┐   │
│  STORAGE    │ │ Category     Amount    %    Δ     Trend     │   │
│  1,847 txs  │ │ Housing      $1,800  43%  ━━    ▅▅▅▅▅▅     │   │
│  3 accounts │ │ Groceries      $620  15%  ▲3%  ▃▃▄▅▄▃     │   │
│             │ │ Dining         $340   8%  ▼8%  ▅▄▃▃▂▃     │   │
│             │ │ Transit        $180   4%  ▲1%  ▃▃▃▃▃▄     │   │
│             │ │ Subscriptions  $160   4%  ━━    ▃▃▃▃▃▃     │   │
│             │ │ ...                                         │   │
│             │ └─────────────────────────────────────────────┘   │
│             │                                                   │
│             │ TOP MERCHANTS              DAILY SPEND            │
│             │ ┌────────────────────┐    ┌──────────────────┐   │
│             │ │ Loblaws    $280 12x│    │ ▃▅▂▇▃▄▅▂▆▃▅▃▂▄▅ │   │
│             │ │ Uber Eats  $180  8x│    │ ▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁ │   │
│             │ │ Netflix     $17  1x│    │ M T W T F S S ... │   │
│             │ └────────────────────┘    └──────────────────┘   │
└─────────────┴───────────────────────────────────────────────────┘
```

---

## Verification Plan

### Automated

Since this is a greenfield project, we'll write tests alongside the code:

1. **Ingestion unit tests** (Vitest)
   - Each bank normalizer tested with a fixture CSV snippet
   - Categorizer tested against known merchant → category mappings
   - Dedup tested with overlapping transaction sets
   - Run: `npx vitest run`

2. **Store logic tests** (Vitest)
   - Derived selectors (spending by category, trends) tested with known data
   - Time-range filtering tested
   - Run: `npx vitest run`

### Browser Verification

3. **Import flow** — Use the browser tool to:
   - Open the app at `localhost:5173`
   - Trigger import modal
   - Upload a test CSV
   - Verify transactions appear in the dashboard

4. **Dashboard rendering** — Use the browser tool to:
   - Verify KPI strip shows correct values
   - Verify spending grid is populated
   - Verify time range selector changes data
   - Screenshot the final dashboard for review

### Manual Verification (User)

5. **Real data test** — After the build, I'll ask you to:
   - Export a CSV from one of your bank accounts
   - Drop it into the import modal
   - Confirm the numbers look right
   - Flag any merchant names that categorized incorrectly
