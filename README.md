# US Stock Backtesting System

A comprehensive backtesting platform for US stock trading strategies. Evaluate your trading strategies against historical market data with a Python/FastAPI backend and React frontend.

## Features

- **Historical Data Management**: Download and import stock price data (OHLCV)
- **Strategy Development**: Write custom strategies using the vici-trade-sdk
- **Web-Based Code Editor**: Create and edit strategies directly in the browser
- **Built-in Indicators**: SMA, EMA, RSI, MACD, Bollinger Bands, ATR, Stochastic, VWAP
- **Backtest Engine**: Simulate strategy execution with commission and position tracking
- **Performance Analytics**: Comprehensive metrics including Sharpe ratio, max drawdown, win rate
- **Interactive Reports**: Visualize equity curves, trades, and performance metrics

## Quick Start

### Prerequisites

- Python 3.13+
- Node.js 22+
- Poetry

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd stock-backtest-system
   ```

2. **Install vici-trade-sdk** (for strategy development)
   ```bash
   pip install vici-trade-sdk
   ```

3. **Backend Setup**
   ```bash
   cd backend
   poetry install --no-root
   poetry run uvicorn app.main:app --reload --port 8000
   ```

4. **Frontend Setup** (in a new terminal)
   ```bash
   cd frontend
   npm install
   npm run dev
   ```

5. **Access the Application**
   - Frontend: http://localhost:5173
   - Backend API: http://localhost:8000/docs

## Docker Setup (Recommended for Cloud Development)

Run the entire stack (backend, frontend, PostgreSQL, Redis) with Docker Compose:

### Prerequisites
- Docker 20.10+
- Docker Compose 2.0+

### Running with Docker

```bash
# 1. Create environment file (optional, uses defaults from docker-compose.yml)
cp .env.example .env

# 2. Start all services
docker-compose up

# 3. Access the application
# - Frontend: http://localhost:5173
# - Backend: http://localhost:8000/docs
# - PostgreSQL: localhost:5432
# - Redis: localhost:6379

# 4. Stop all services
docker-compose down

# 5. Stop and remove volumes (clean state)
docker-compose down -v
```

### Services Included

- **Backend**: FastAPI app with hot-reload
- **Frontend**: Vite dev server with hot-reload
- **PostgreSQL**: Database for multi-user support (replaces SQLite)
- **Redis**: Cache and task queue (for future features)

### Development Notes

- Source code is mounted as volumes for hot-reload
- Database data persists in Docker volume `postgres_data`
- User workspaces persist in Docker volume `workspaces`
- All services have health checks for reliability

## Usage

### 1. Download Stock Data

Navigate to the "Stock Data" page and download historical data for the stocks you want to backtest.

### 2. Create a Trading Strategy

**Option A: Web Editor**
- Go to "Strategy Editor" page
- Click "New Strategy"
- Write your strategy using the provided template
- Save the file

**Option B: Local File**
- Create a `.py` file in `~/.vici-backtest/strategies/`
- Write your strategy using vici-trade-sdk

**Example Strategy:**
```python
from vici_trade_sdk import Strategy, Portfolio
import pandas as pd

class GoldenCross(Strategy):
    @property
    def name(self) -> str:
        return "Golden Cross Strategy"

    def indicators(self) -> list[dict]:
        return [
            {"name": "sma", "params": {"period": 50}},
            {"name": "sma", "params": {"period": 200}},
        ]

    def on_bar(self, date: str, data: dict[str, pd.Series],
               portfolio: Portfolio) -> None:
        for symbol in data:
            sma50 = data[symbol]["sma_50"]
            sma200 = data[symbol]["sma_200"]

            position = portfolio.get_position(symbol)

            if sma50 > sma200 and not position.is_open:
                # Golden cross: buy signal
                portfolio.buy(symbol, 100, data[symbol]["close"], date)
            elif sma50 < sma200 and position.is_open:
                # Death cross: sell signal
                portfolio.sell(symbol, position.quantity,
                             data[symbol]["close"], date)
```

### 3. Run Backtest

- Go to "Run Backtest" page
- Select your strategy
- Choose stock symbols and date range
- Set initial capital and commission rate
- Click "Run Backtest"

### 4. View Results

- Navigate to "Results" page
- Click on a backtest to view detailed performance metrics
- Analyze equity curve, trade history, and statistics

## Project Structure

```
backend/              Python backend (FastAPI)
  app/
    api/              REST API endpoints
    core/             Configuration and database
    models/           Pydantic schemas
    services/         Business logic (engine, indicators, workspace)
  strategies/         Example strategies (copied to user workspace)
  tests/              Pytest test suite

frontend/             React frontend (TypeScript + Vite)
  src/
    pages/            Page components
    services/         API client
    types/            TypeScript definitions

vici-trade-sdk/       Standalone SDK package
  vici_trade_sdk/
    strategy.py       Strategy base class
    portfolio.py      Portfolio management

~/.vici-backtest/     User workspace (auto-created)
  strategies/         User-defined strategies
```

## Development

### Running Tests

```bash
cd backend
poetry run pytest tests/ -v
```

### SDK Development

For local SDK development:

```bash
cd backend
poetry add ../vici-trade-sdk
```

This adds the SDK as an editable path dependency.

## Architecture

### Strategy Development Flow

1. Users install `vici-trade-sdk` via pip
2. Write strategies inheriting from `Strategy` base class
3. Strategies stored in `~/.vici-backtest/strategies/` (user workspace)
4. Backend auto-discovers strategies on startup
5. Strategies available for backtesting via API

### Workspace Management

- **User Workspace**: `~/.vici-backtest/strategies/`
- **Initialization**: On first startup, backend copies example strategies to workspace
- **Strategy Loading**: Backend loads strategies from workspace only (single source of truth)
- **Web Editor**: Monaco Editor provides browser-based strategy editing

### Key Technologies

- **Backend**: FastAPI, SQLite (aiosqlite), Pandas, NumPy
- **Frontend**: React 19, TypeScript, Vite, Recharts, Monaco Editor
- **SDK**: Standalone package for strategy development
- **Testing**: pytest, httpx

## API Documentation

Once the backend is running, visit:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

### Key Endpoints

- `GET /api/data/stocks` - List available stocks
- `POST /api/data/download` - Download stock data
- `GET /api/strategies` - List available strategies
- `GET /api/strategies/files` - List strategy files
- `POST /api/strategies/files` - Create/update strategy file
- `POST /api/backtests` - Run a backtest
- `GET /api/backtests` - List backtest results

## Contributing

This project is built with assistance from Claude Code agents. Contributions are welcome!

## License

MIT
