# CLAUDE.md

This file serves a guidance for Claude Code to work on this repository.

## Project Overview

US Stock Backtesting System — a service for traders to evaluate trading strategies against historical market data. Python/FastAPI backend with a React/Vite frontend.

## Repository Structure

```
backend/           Python backend (FastAPI)
  app/
    core/          Config and database setup
    models/        Pydantic schemas
    services/      Core business logic (data manager, indicators, engine, workspace)
    api/           REST API route handlers
    main.py        FastAPI app entrypoint
  strategies/      Example strategies (copied to user workspace on first run)
  tests/           Pytest test suite
  data/            SQLite database files (gitignored)
  reports/         Generated HTML reports (gitignored)
  pyproject.toml   Poetry config and dependencies
  poetry.lock
  pytest.ini

frontend/          React frontend (Vite + TypeScript)
  src/
    pages/         Page components (Data, Backtest, Results, StrategyEditor)
    services/      API client (axios)
    types/         TypeScript type definitions

vici-trade-sdk/    Standalone SDK package for strategy development
  vici_trade_sdk/
    strategy.py    Strategy base class
    portfolio.py   Portfolio, Position, Trade, Side classes
  pyproject.toml   SDK package configuration

~/.vici-backtest/  User workspace (auto-created)
  strategies/      User-defined strategy files (loaded at runtime)
```

## Development Environment

**Prerequisites:** Python 3.13+, Node.js 22+

### Backend

```bash
cd backend
poetry install --no-root
poetry run uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

## Running Tests

```bash
cd backend
poetry run pytest tests/ -v
```

Pytest is configured with `asyncio_mode = auto` in `pytest.ini`. Tests use `httpx.AsyncClient` for API testing.

## Key Conventions

- **Language:** Code in English, documentation may be in Chinese
- **Backend style:** Follow PEP 8. Use type hints. Pydantic for validation.
- **Frontend style:** TypeScript strict mode. Functional components with hooks.
- **Database:** SQLite stored at `backend/data/backtest.db` (auto-created on startup)
- **Async:** FastAPI routes are async. Database operations use `aiosqlite`.
- **Indicators:** Built-in indicators live in `backend/app/services/indicators.py`. Each extends the `Indicator` base class.
- **Strategies:**
  - Users install `vici-trade-sdk`: `pip install vici-trade-sdk`
  - User strategies live in `~/.vici-backtest/strategies/` (user workspace)
  - Each strategy file imports from `vici_trade_sdk` and defines a class inheriting `Strategy`
  - Backend copies example strategies from `backend/strategies/` to workspace on first startup
  - Backend loads strategies from workspace only (not from codebase)
  - Web UI provides code editor for creating/editing strategies inline

## Tech Stack

| Layer     | Technology                          |
|-----------|-------------------------------------|
| Backend   | Python 3.13, FastAPI, Pydantic, Poetry |
| SDK       | vici-trade-sdk (standalone package) |
| Database  | SQLite (aiosqlite)                  |
| Data      | yfinance, pandas, numpy             |
| Charts    | Plotly (HTML reports), Recharts (frontend) |
| Frontend  | React 19, Vite 7, TypeScript 5.9, Monaco Editor |
| Testing   | pytest, pytest-asyncio, httpx       |

## Strategy Development Workflow

1. **Installation:** Users run `pip install vici-trade-sdk`
2. **Writing Strategies:**
   - Option A: Create `.py` files in `~/.vici-backtest/strategies/`
   - Option B: Use web UI Strategy Editor (Monaco code editor)
3. **Strategy Structure:**
   ```python
   from vici_trade_sdk import Strategy, Portfolio
   import pandas as pd

   class MyStrategy(Strategy):
       @property
       def name(self) -> str:
           return "My Custom Strategy"

       def indicators(self) -> list[dict]:
           return [{"name": "sma", "params": {"period": 50}}]

       def on_bar(self, date: str, data: dict[str, pd.Series],
                  portfolio: Portfolio) -> None:
           # Trading logic here
           pass
   ```
4. **Backend Loading:** Backend auto-discovers strategies from workspace on startup
5. **API Access:** Strategies available via `/api/strategies` endpoint for backtesting
