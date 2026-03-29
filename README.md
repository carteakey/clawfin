# 🐾 ClawFin

ClawFin is a privacy-first, self-hosted, AI-native personal finance dashboard tailored for Canadians. It offers a dense, Bloomberg-terminal-inspired "glass and data" aesthetic, focusing on speed, automated data ingestion, and a powerful conversational interface for querying your finances.

<p align="center">
  <img src="clawfin_brand.svg" width="200" alt="ClawFin Branding" />
</p>

## ✨ Core Features

- **Canadian-First Ingestion**:
  - Auto-detecting CSV parsers for the Big 5 (TD, RBC, Scotiabank, BMO, CIBC).
  - Wealthsimple CSV integration (Holdings & Activity) with dual-currency Book/Market value tracking.
- **Automated AI Categorization**:
  - Uses a batch LLM pipeline to categorize merchants and caches results locally in SQLite.
  - Regex fallback for known generic merchants to save API calls.
- **Smart Data Sync**:
  - Optional **SimpleFin** integration for continuous secure API syncing.
  - Multi-currency support powered by the **Bank of Canada Valet API** (daily CAD/USD/EUR/GBP rates).
  - SHA-256 transaction deduplication (with per-day sequence counters to allow identical same-day purchases).
- **AI Agent (⌘K)**:
  - A persistent, sliding chat sidebar with SSE (Server-Sent Events) streaming.
  - Armed with 6 native data tools to query spending, calculate net worth, search transactions, and project investment growth securely without exposing raw DB access.
  - Supports Ollama (local), Anthropic, and OpenAI architectures via a unified wire-format abstraction layer.
- **Privacy by Design**:
  - File-backed SQLite database.
  - Simple `CLAWFIN_PASSWORD` gate for the entire UI.
  - No bloated framework dependencies; direct `httpx` provider calls.

## 🏗️ Architecture

- **Backend**: Python 3.12, FastAPI, SQLAlchemy, Alembic (Migrations).
- **Frontend**: React 19, Vite, Zustand (State), Recharts (Visuals), Lucide (Icons).
- **Design System**: Custom CSS variables, dark-mode exclusive, custom Mono-fonts for dense tabular data.

## 🚀 Getting Started

ClawFin is designed to be run as an appliance via Docker.

### 1. Configure

Copy the environment example and set your secure password:

```bash
cp .env.example .env
```
Edit `.env` to set:
- `CLAWFIN_PASSWORD`: Your UI password.
- `CLAWFIN_SECRET_KEY`: A long random string.
- `CLAWFIN_AI_PROVIDER`: Choose `ollama`, `anthropic`, or `openai`.

### 2. Run via Docker Compose

Run the standard stack (FastAPI Backend + Nginx Frontend):
```bash
docker compose up -d
```

To automatically spin up a local Ollama container alongside ClawFin:
```bash
docker compose --profile ai-local up -d
```

### 3. Usage

1. Open `http://localhost:3000` (or `http://localhost:5174` if running `npm run dev` locally).
2. Log in using your `CLAWFIN_PASSWORD`.
3. Press **⌘K** to open the AI Chat, or navigate to **Settings** to ensure your LLM provider is connected.
4. Drag and drop a bank CSV or Wealthsimple export into the **Import** tab.

## 🛠️ Local Development

If you want to build and iterate on ClawFin without Docker:

**Terminal 1 (Backend):**
```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
CLAWFIN_PASSWORD="dev" uvicorn backend.main:app --reload
```

**Terminal 2 (Frontend):**
```bash
cd frontend
npm install
npm run dev
```

## 🗺️ Phase Roadmap

- **Phase 1 (Current)**: Foundation, Data Ingestion, UI Dashboard, AI Tools, Docker.
- **Phase 2 (Next)**: Automated Rule Management UI, Advanced Budgeting Goals, Multi-user support.
