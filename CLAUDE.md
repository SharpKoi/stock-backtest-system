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
    services/      Core business logic (data manager, indicators, engine, etc.)
    api/           REST API route handlers
    main.py        FastAPI app entrypoint
  strategies/      User-defined strategy files (auto-discovered)
  tests/           Pytest test suite
  data/            SQLite database files (gitignored)
  reports/         Generated HTML reports (gitignored)
  pyproject.toml   Poetry config and dependencies
  poetry.lock
  pytest.ini

frontend/          React frontend (Vite + TypeScript)
  src/
    pages/         Page components (Data, Backtest, Results, ResultDetail)
    services/      API client (axios)
    types/         TypeScript type definitions
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
- **Strategies:** User strategies go in `backend/strategies/`. Each file exports a class inheriting `Strategy` with `name`, `indicators()`, and `on_bar()`. Strategies are auto-discovered by the strategy loader.

## Tech Stack

| Layer     | Technology                          |
|-----------|-------------------------------------|
| Backend   | Python 3.13, FastAPI, Pydantic, Poetry |
| Database  | SQLite (aiosqlite)                  |
| Data      | yfinance, pandas, numpy             |
| Charts    | Plotly (HTML reports), Recharts (frontend) |
| Frontend  | React 19, Vite 7, TypeScript 5.9    |
| Testing   | pytest, pytest-asyncio, httpx       |
