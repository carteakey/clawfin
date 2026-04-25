# ClawFin — Design & Functionality Review

A thorough audit of the current v0.1 codebase with honest opinions on what fits the product's identity and what doesn't.

---

## What's Working Well

**The brutalist design system is coherent and fast.** The 1px rules, mono typography, teal accent, and zero-radius approach feel genuinely distinctive — it reads like Bloomberg terminal meets a fintech CLI. The token system in `index.css` is clean and the dark/light themes are well-executed.

**The data model is solid.** `Transaction` with `normalized_merchant`, hash dedup, pending markers, and the `CategoryRule` learning system is a genuinely good foundation. The `on_budget` account flag, SimpleFIN staleness fields, and multi-source ingestion are all well-thought-out.

**The AI agent integration is a real differentiator.** Provider switching (Ollama / OpenAI / Anthropic) at runtime with no restart is slick. The preset brief buttons in chat are the right pattern for a power user.

**The command palette (`⌘K`) is excellent UX** for a keyboard-first app. It fits the Bloomberg-terminal identity perfectly.

---

## What to Rethink

### 1. 🔁 **Recurring → Subscription Finder** (your instinct is right)

**The current problem:**  
The `Recurring` view is a pure algorithmic dump — "≥3 charges, 6-35d cadence, ±15% amount." It catches Netflix, Spotify, and rent. It also catches your bi-weekly grocery run and bi-weekly payroll. The UI shows a dense table with "Cadence: 14d" but gives you no way to act on anything. There's no concept of "is this wanted or not?" and no per-item management.

**What to build instead — a Subscription Finder:**
- **Intent:** Surface what you're *paying for*, not just what's periodic
- **Behavior:** Filter the recurring scan to expenses-only (already done), then layer a "subscription confidence" signal:  
  - Known subscription merchants (Netflix, Spotify, Adobe, AWS, etc.) → `HIGH`
  - Exact same amount, monthly cadence, consumer brand → `MEDIUM`  
  - Wages, rent, insurance, loan payments → separate "Fixed Costs" section, not subscriptions
- **UI changes:**
  - Rename nav item `Subscriptions` (or `Fixed Costs`)
  - Split into two sections: **Subscriptions** (discretionary, cancellable) vs **Fixed Obligations** (rent, loan, insurance)
  - Add a `Cancel?` or `Review` action button per row — could link to a URL, or just flag the row as "reviewed"
  - Show a `Subscriptions this year` vs `Fixed obligations this year` breakdown, not just one total
  - Show **time since last reviewed** — the real value is prompting "why am I still paying for this?"

**Backend changes needed:** The heuristic in `transactions.py:list_recurring` already does the hard work. Add a `known_subscription_merchants` list and a `subscription_type` field (`subscription | fixed | income | other`) on each row. The cadence window of 6-35 days misses annual subscriptions (e.g., Apple One, domain renewals) — extend to 300-400 days for known patterns.

---

### 2. 📊 **Planning page is underbuilt for its ambition**

**The current problem:**  
Planning shows: net worth over time (chart) + 3-month cashflow forecast (bar chart + tiny table). The forecast is powered entirely by the recurring detection, which means if recurring is noisy, Planning is noisy. The page reads like a container for two disconnected features that happen to share a route.

**What it should be:**
- **Net Worth** should stay, but clearly show what's "real" vs synthetic. The `source: synthetic | snapshot` flag exists in the API but isn't surfaced at all — users have no idea if the chart is real or estimated.
- **Cash Flow Forecast** should become its own proper view or be promoted to the dashboard, not buried at the bottom of Planning.
- **Planning should become a Goals view:** RRSP/TFSA/FHSA contribution room is already in Settings (the `Contribution` tab) — this belongs in Planning, not Settings. Move it here and show "room used vs available" with a progress bar.
- Add a simple "months until goal" calculator: target amount, current savings rate → projected date.

---

### 3. 🏦 **Accounts page is missing stale sync visibility**

**The current problem:**  
The `Account` model has rich staleness metadata: `last_sync_at`, `last_successful_balance_date`, `stale_reason`, `simplefin_account_present`. None of this is shown in the Accounts view. The only visible sync signal is a raw balance date if you know to look.

**Fix:** Show a stale/healthy indicator per account row. Even a simple `●` dot colored green/amber/red based on `stale_reason` would make the page actionable. SimpleFIN users especially need to know when a bank connection has broken.

---

### 4. 📉 **Dashboard is one-dimensional**

**The current problem:**  
The dashboard shows: account balance hero → KPI row (income/expenses/savings rate/txn count) → cash flow waterfall → spending by category → top merchants → daily spending bar chart. That's a lot, but it's all **backward-looking spend analysis** for the selected period. Nothing is forward-looking or contextual.

**What's missing:**
- **"This month vs last month" framing** is good but the delta labels (`+4.2%`) on KPIs are tiny and easy to miss
- **No outstanding/pending callout** — pending transactions exist in the DB but aren't surfaced on the dashboard
- **No recurring cost summary** — showing "your subscriptions cost $X/mo" on the dashboard would connect Planning and Recurring
- **Savings rate** is calculated but not visualized in any meaningful way — a simple sparkline or goal indicator would make it feel real
- The `top_merchants` table has no navigation — clicking a merchant should filter Transactions to that merchant

---

### 5. 🤖 **AI is powerful but underconnected**

**The current problem:**  
The AI chat is a floating panel (`⇧⌘K`) and is completely disconnected from the rest of the app. The AI has access to transactions via briefing tool calls, but there's no in-context AI where you'd expect it — in Transactions (explain this charge), in Recurring (why is this flagged?), in the Dashboard (what's driving my expense spike?).

**What to build:**
- **Inline insights** — small "Ask AI" buttons next to anomalies (e.g., a category that spiked 40% this month)
- **Transaction explainer** — right-click or hover on a transaction merchant → "What is this?" triggers a focused AI lookup
- **Dashboard brief widget** — a small "Today's insight" card on the Dashboard that auto-runs a lightweight brief (not a full briefing, just 2-3 sentences)

The briefing presets (Daily Brief / Weekly Brief / Private Daily) are the right idea but they're hidden behind `⇧⌘K`. They deserve to be more discoverable.

---

### 6. 📥 **Import UX needs more feedback**

The import flow (CSV upload + SimpleFIN sync) works, but gives almost no feedback on what happened. After importing a TD CSV, you get a generic success count. You should show:
- New transactions added (vs. skipped duplicates)
- Category breakdown of what was imported
- Any parsing errors or unmapped merchants
- "What's new" diff — the last 10 transactions just added

---

### 7. 🧭 **Navigation information architecture is off**

Current sidebar order: `Dashboard → Accounts → Holdings → Transactions → Recurring → Planning → Import → Settings`

Problems:
- `Holdings` is a niche view (Wealthsimple users only) at position 3. Should be lower.
- `Import` is buried at the bottom — for new users, it's the **first** thing they need.
- `Recurring` and `Planning` feel like sub-sections of each other but are presented as equals.

Suggested reorder:
```
Dashboard
Transactions
Accounts
 ↳ Holdings (sub-item or tab within Accounts)
Subscriptions   ← renamed from Recurring  
Planning
──────────
Import          ← demote to utility section with a divider
Settings
```

---

## Quick Wins (Low Effort, High Value)

| What | Why |
|---|---|
| Rename `Recurring` → `Subscriptions` in nav | Sets clearer user expectation |
| Show stale indicator on Accounts rows | Makes SimpleFIN health visible |
| Make merchant names in Dashboard clickable | Opens Transactions filtered to that merchant |
| Move Contribution Room from Settings → Planning | It's a planning concept, not a setting |
| Show `source: synthetic` label on Net Worth chart | Builds trust in the data |
| Add "N pending transactions" banner to Dashboard | Surfaces data that already exists |
| Extend recurring cadence scan to 400 days | Catches annual subscriptions |

---

## Feature Ideas Ranked by Impact / Effort

| Feature | Impact | Effort | Notes |
|---|---|---|---|
| **Subscription Finder** (split from Recurring) | 🔥 High | Medium | Core UX improvement |
| **Spending Trends** (month-over-month per category) | 🔥 High | Low | Data already exists |
| **Inline AI Insights** (anomaly callouts) | 🔥 High | High | Needs UI + agent work |
| **Import diff / preview** | Medium | Medium | Better onboarding |
| **Goal tracker** in Planning | Medium | Medium | TFSA/RRSP room already in DB |
| **Merchant detail drilldown** | Medium | Low | Filter Transactions by merchant |
| **Annual subscription scan** | Medium | Low | Extend cadence window |
| **Account stale indicators** | Medium | Low | Data already in model |
| **"What is this charge?" AI button** | Medium | High | Needs tool call routing |
| **Mobile-responsive layout** | Low-Medium | High | Already in v0.2 roadmap |

---

## Design Notes

**Keep:**  
- The brutalist aesthetic — it's a strong differentiator and perfectly fits the "Bloomberg for your finances" positioning
- JetBrains Mono for numbers — tabular rendering is exactly right for financial data
- The command palette — power users will love it once they know it exists (discoverability is the gap)

**Improve:**
- The `hero-stat` 64px number is bold but the sub-line text (`Income $X · Expenses $Y · Savings Z%`) is doing too much on one line — consider a 2-line layout or dedicated KPI cards below
- Category colors exist in the model (`Category.color`) but are not used anywhere in the UI — the spending breakdown bars are all monochrome ink. Using category colors in the waterfall chart would make it dramatically more readable.
- The `section-head::after` teal underline accent is a nice touch but the 40px fixed width looks odd at narrower widths
- Charts use `isAnimationActive={false}` everywhere — intentional (fast) but a very subtle 200ms fade-in on page load would feel more premium without hurting performance

