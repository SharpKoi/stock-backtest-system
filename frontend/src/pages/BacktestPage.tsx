import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import type { StockInfo, StrategyInfo } from "../types";
import { listStocks, listStrategies, runBacktest } from "../services/api";

function BacktestPage() {
  const navigate = useNavigate();
  const [stocks, setStocks] = useState<StockInfo[]>([]);
  const [strategies, setStrategies] = useState<StrategyInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState("");

  // Form state
  const [name, setName] = useState("");
  const [strategyName, setStrategyName] = useState("");
  const [selectedSymbols, setSelectedSymbols] = useState<string[]>([]);
  const [startDate, setStartDate] = useState("2020-01-01");
  const [endDate, setEndDate] = useState("2024-12-31");
  const [initialCapital, setInitialCapital] = useState(100000);
  const [commissionRate, setCommissionRate] = useState(0.001);
  const [paramInputs, setParamInputs] = useState("");

  useEffect(() => {
    async function fetchData() {
      try {
        const [stocksData, strategiesData] = await Promise.all([
          listStocks(),
          listStrategies(),
        ]);
        setStocks(stocksData);
        setStrategies(strategiesData);
        if (strategiesData.length > 0) {
          setStrategyName(strategiesData[0].class_name);
        }
      } catch {
        setError("Failed to load data");
      } finally {
        setLoading(false);
      }
    }
    fetchData();
  }, []);

  function toggleSymbol(symbol: string) {
    setSelectedSymbols((prev) =>
      prev.includes(symbol)
        ? prev.filter((s) => s !== symbol)
        : [...prev, symbol]
    );
  }

  function parseParams(): Record<string, unknown> {
    if (!paramInputs.trim()) return {};
    try {
      return JSON.parse(paramInputs);
    } catch {
      return {};
    }
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();

    if (selectedSymbols.length === 0) {
      setError("Select at least one stock symbol");
      return;
    }
    if (!strategyName) {
      setError("Select a strategy");
      return;
    }

    setRunning(true);
    setError("");

    try {
      const result = await runBacktest({
        name: name || `Backtest ${new Date().toISOString().slice(0, 10)}`,
        strategy_name: strategyName,
        symbols: selectedSymbols,
        start_date: startDate,
        end_date: endDate,
        initial_capital: initialCapital,
        commission_rate: commissionRate,
        strategy_params: parseParams(),
      });
      navigate(`/results/${result.backtest_id}`);
    } catch (err: unknown) {
      if (err && typeof err === "object" && "response" in err) {
        const axiosErr = err as { response?: { data?: { detail?: string } } };
        setError(axiosErr.response?.data?.detail || "Backtest failed");
      } else {
        setError("Backtest failed");
      }
    } finally {
      setRunning(false);
    }
  }

  if (loading) {
    return (
      <div className="loading-container">
        <span className="spinner" /> Loading...
      </div>
    );
  }

  const selectedStrategy = strategies.find((s) => s.class_name === strategyName);

  return (
    <div>
      <h1 className="page-title">Run Backtest</h1>

      {error && <div className="error-message">{error}</div>}

      {stocks.length === 0 ? (
        <div className="card">
          <div className="empty-state">
            <p>No stock data available.</p>
            <p className="text-sm text-muted">
              Go to the Stock Data page to download data first.
            </p>
          </div>
        </div>
      ) : (
        <form onSubmit={handleSubmit}>
          <div className="card">
            <div className="card-title">Backtest Configuration</div>

            <div className="form-group">
              <label className="form-label">Backtest Name</label>
              <input
                type="text"
                className="form-input"
                placeholder="e.g. SMA Cross Test"
                value={name}
                onChange={(e) => setName(e.target.value)}
              />
            </div>

            <div className="form-group">
              <label className="form-label">Strategy</label>
              <select
                className="form-select"
                value={strategyName}
                onChange={(e) => setStrategyName(e.target.value)}
              >
                {strategies.map((s) => (
                  <option key={s.class_name} value={s.class_name}>
                    {s.name} ({s.class_name})
                  </option>
                ))}
              </select>
              {selectedStrategy?.docstring && (
                <p className="text-sm text-muted mt-2">
                  {selectedStrategy.docstring.split("\n")[0]}
                </p>
              )}
            </div>

            <div className="form-group">
              <label className="form-label">
                Symbols ({selectedSymbols.length} selected)
              </label>
              <div className="flex gap-2" style={{ flexWrap: "wrap" }}>
                {stocks.map((stock) => (
                  <button
                    key={stock.symbol}
                    type="button"
                    className={`btn btn-sm ${
                      selectedSymbols.includes(stock.symbol)
                        ? "btn-primary"
                        : "btn-secondary"
                    }`}
                    onClick={() => toggleSymbol(stock.symbol)}
                  >
                    {stock.symbol}
                  </button>
                ))}
              </div>
            </div>

            <div className="form-row">
              <div className="form-group">
                <label className="form-label">Start Date</label>
                <input
                  type="date"
                  className="form-input"
                  value={startDate}
                  onChange={(e) => setStartDate(e.target.value)}
                />
              </div>
              <div className="form-group">
                <label className="form-label">End Date</label>
                <input
                  type="date"
                  className="form-input"
                  value={endDate}
                  onChange={(e) => setEndDate(e.target.value)}
                />
              </div>
            </div>

            <div className="form-row">
              <div className="form-group">
                <label className="form-label">Initial Capital ($)</label>
                <input
                  type="number"
                  className="form-input"
                  value={initialCapital}
                  onChange={(e) => setInitialCapital(Number(e.target.value))}
                  min={1000}
                  step={1000}
                />
              </div>
              <div className="form-group">
                <label className="form-label">Commission Rate</label>
                <input
                  type="number"
                  className="form-input"
                  value={commissionRate}
                  onChange={(e) => setCommissionRate(Number(e.target.value))}
                  min={0}
                  max={0.1}
                  step={0.0001}
                />
              </div>
            </div>

            <div className="form-group">
              <label className="form-label">
                Strategy Parameters (JSON, optional)
              </label>
              <input
                type="text"
                className="form-input"
                placeholder='e.g. {"short_period": 10, "long_period": 30}'
                value={paramInputs}
                onChange={(e) => setParamInputs(e.target.value)}
              />
            </div>
          </div>

          <button
            type="submit"
            className="btn btn-primary"
            disabled={running || selectedSymbols.length === 0}
          >
            {running ? (
              <>
                <span className="spinner" /> Running Backtest...
              </>
            ) : (
              "Run Backtest"
            )}
          </button>
        </form>
      )}
    </div>
  );
}

export default BacktestPage;
