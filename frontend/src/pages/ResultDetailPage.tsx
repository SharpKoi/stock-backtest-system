import { useState, useEffect, useMemo } from "react";
import { useParams, Link } from "react-router-dom";
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import type { BacktestResult } from "../types";
import { getBacktestResult } from "../services/api";

function MetricCard({
  label,
  value,
  colorClass,
}: {
  label: string;
  value: string;
  colorClass: string;
}) {
  return (
    <div className="metric-card">
      <div className="metric-label">{label}</div>
      <div className={`metric-value ${colorClass}`}>{value}</div>
    </div>
  );
}

function valueColorClass(value: number): string {
  if (value > 0) return "positive";
  if (value < 0) return "negative";
  return "neutral";
}

function ResultDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [result, setResult] = useState<BacktestResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    async function fetchResult() {
      if (!id) return;
      try {
        const data = await getBacktestResult(Number(id));
        setResult(data);
      } catch {
        setError("Failed to load backtest result");
      } finally {
        setLoading(false);
      }
    }
    fetchResult();
  }, [id]);

  const drawdownData = useMemo(() => {
    if (!result?.equity_curve) return [];
    let peak = result.equity_curve[0]?.equity || 0;
    return result.equity_curve.map((point) => {
      if (point.equity > peak) peak = point.equity;
      const drawdown = peak > 0 ? ((point.equity - peak) / peak) * 100 : 0;
      return { date: point.date, drawdown: Math.round(drawdown * 100) / 100 };
    });
  }, [result]);

  if (loading) {
    return (
      <div className="loading-container">
        <span className="spinner" /> Loading...
      </div>
    );
  }

  if (error || !result) {
    return (
      <div>
        <div className="error-message">{error || "Result not found"}</div>
        <Link to="/results" className="btn btn-secondary">
          Back to Results
        </Link>
      </div>
    );
  }

  const { metrics } = result;

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <h1 className="page-title" style={{ marginBottom: 0 }}>
          {result.name}
        </h1>
        <Link to="/results" className="btn btn-secondary btn-sm">
          Back to Results
        </Link>
      </div>

      <p className="text-muted mb-4">
        Strategy: {result.strategy_name} | Symbols:{" "}
        {result.symbols.join(", ")} | {result.start_date} to {result.end_date}
      </p>

      {/* Metrics Grid */}
      <div className="metrics-grid">
        <MetricCard
          label="Total Return"
          value={`$${metrics.total_return.toLocaleString()}`}
          colorClass={valueColorClass(metrics.total_return)}
        />
        <MetricCard
          label="Return %"
          value={`${metrics.total_return_pct > 0 ? "+" : ""}${metrics.total_return_pct}%`}
          colorClass={valueColorClass(metrics.total_return_pct)}
        />
        <MetricCard
          label="Annualized"
          value={`${metrics.annualized_return_pct > 0 ? "+" : ""}${metrics.annualized_return_pct}%`}
          colorClass={valueColorClass(metrics.annualized_return_pct)}
        />
        <MetricCard
          label="Max Drawdown"
          value={`${metrics.max_drawdown_pct}%`}
          colorClass={valueColorClass(metrics.max_drawdown_pct)}
        />
        <MetricCard
          label="Sharpe Ratio"
          value={metrics.sharpe_ratio.toFixed(4)}
          colorClass={valueColorClass(metrics.sharpe_ratio)}
        />
        <MetricCard
          label="Win Rate"
          value={`${metrics.win_rate.toFixed(1)}%`}
          colorClass="neutral"
        />
        <MetricCard
          label="Total Trades"
          value={String(metrics.total_trades)}
          colorClass="neutral"
        />
        <MetricCard
          label="Profit Factor"
          value={metrics.profit_factor.toFixed(2)}
          colorClass={valueColorClass(metrics.profit_factor - 1)}
        />
      </div>

      {/* Equity Curve Chart */}
      <div className="card">
        <div className="card-title">Equity Curve</div>
        <ResponsiveContainer width="100%" height={300}>
          <AreaChart data={result.equity_curve}>
            <defs>
              <linearGradient id="equityGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#4fc3f7" stopOpacity={0.3} />
                <stop offset="100%" stopColor="#4fc3f7" stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="#1e2130" />
            <XAxis
              dataKey="date"
              tick={{ fill: "#888", fontSize: 11 }}
              tickFormatter={(val: string) => val.slice(5)}
              minTickGap={60}
            />
            <YAxis
              tick={{ fill: "#888", fontSize: 11 }}
              tickFormatter={(val: number) => `$${(val / 1000).toFixed(0)}k`}
            />
            <Tooltip
              contentStyle={{
                background: "#1a1d29",
                border: "1px solid #2a2d3a",
                borderRadius: 6,
                color: "#e0e0e0",
              }}
              formatter={(val: number | undefined) => [`$${(val ?? 0).toFixed(2)}`, "Equity"]}
            />
            <Area
              type="monotone"
              dataKey="equity"
              stroke="#4fc3f7"
              strokeWidth={1.5}
              fill="url(#equityGrad)"
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>

      {/* Drawdown Chart */}
      <div className="card">
        <div className="card-title">Drawdown</div>
        <ResponsiveContainer width="100%" height={200}>
          <AreaChart data={drawdownData}>
            <defs>
              <linearGradient id="ddGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#ff1744" stopOpacity={0} />
                <stop offset="100%" stopColor="#ff1744" stopOpacity={0.3} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="#1e2130" />
            <XAxis
              dataKey="date"
              tick={{ fill: "#888", fontSize: 11 }}
              tickFormatter={(val: string) => val.slice(5)}
              minTickGap={60}
            />
            <YAxis
              tick={{ fill: "#888", fontSize: 11 }}
              tickFormatter={(val: number) => `${val}%`}
            />
            <Tooltip
              contentStyle={{
                background: "#1a1d29",
                border: "1px solid #2a2d3a",
                borderRadius: 6,
                color: "#e0e0e0",
              }}
              formatter={(val: number | undefined) => [`${(val ?? 0).toFixed(2)}%`, "Drawdown"]}
            />
            <Area
              type="monotone"
              dataKey="drawdown"
              stroke="#ff1744"
              strokeWidth={1.5}
              fill="url(#ddGrad)"
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>

      {/* Trade Log */}
      <div className="card">
        <div className="card-title">
          Trade Log ({result.trades.length} trades)
        </div>
        {result.trades.length === 0 ? (
          <p className="text-muted">No trades executed.</p>
        ) : (
          <div style={{ overflowX: "auto" }}>
            <table className="data-table">
              <thead>
                <tr>
                  <th>#</th>
                  <th>Date</th>
                  <th>Symbol</th>
                  <th>Side</th>
                  <th>Qty</th>
                  <th>Price</th>
                  <th>Total</th>
                  <th>Commission</th>
                </tr>
              </thead>
              <tbody>
                {result.trades.map((trade, idx) => (
                  <tr key={idx}>
                    <td>{idx + 1}</td>
                    <td>{trade.date}</td>
                    <td style={{ fontWeight: 600 }}>{trade.symbol}</td>
                    <td
                      className={
                        trade.side === "BUY" ? "positive" : "negative"
                      }
                    >
                      {trade.side}
                    </td>
                    <td>{trade.quantity}</td>
                    <td>${trade.price.toFixed(2)}</td>
                    <td>
                      ${(trade.quantity * trade.price).toLocaleString(undefined, {
                        minimumFractionDigits: 2,
                        maximumFractionDigits: 2,
                      })}
                    </td>
                    <td>${trade.commission.toFixed(2)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}

export default ResultDetailPage;
