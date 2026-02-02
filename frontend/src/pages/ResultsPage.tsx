import { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import type { BacktestSummary } from "../types";
import { listBacktests, deleteBacktest } from "../services/api";

function ResultsPage() {
  const [backtests, setBacktests] = useState<BacktestSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  async function fetchBacktests() {
    try {
      const data = await listBacktests();
      setBacktests(data);
    } catch {
      setError("Failed to load backtests");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    fetchBacktests();
  }, []);

  async function handleDelete(id: number) {
    if (!confirm("Delete this backtest result?")) return;
    try {
      await deleteBacktest(id);
      setBacktests((prev) => prev.filter((b) => b.id !== id));
    } catch {
      setError("Failed to delete backtest");
    }
  }

  if (loading) {
    return (
      <div className="loading-container">
        <span className="spinner" /> Loading...
      </div>
    );
  }

  return (
    <div>
      <h1 className="page-title">Backtest Results</h1>

      {error && <div className="error-message">{error}</div>}

      {backtests.length === 0 ? (
        <div className="card">
          <div className="empty-state">
            <p>No backtest results yet.</p>
            <p className="text-sm text-muted">
              Run a backtest to see results here.
            </p>
          </div>
        </div>
      ) : (
        <div className="card">
          <table className="data-table">
            <thead>
              <tr>
                <th>ID</th>
                <th>Name</th>
                <th>Strategy</th>
                <th>Symbols</th>
                <th>Period</th>
                <th>Capital</th>
                <th>Status</th>
                <th>Created</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {backtests.map((bt) => (
                <tr key={bt.id}>
                  <td>{bt.id}</td>
                  <td>
                    <Link to={`/results/${bt.id}`}>{bt.name}</Link>
                  </td>
                  <td>{bt.strategy_name}</td>
                  <td>{bt.symbols.join(", ")}</td>
                  <td className="text-sm">
                    {bt.start_date} ~ {bt.end_date}
                  </td>
                  <td>${bt.initial_capital.toLocaleString()}</td>
                  <td>
                    <span
                      className={`badge ${
                        bt.status === "completed"
                          ? "badge-success"
                          : "badge-pending"
                      }`}
                    >
                      {bt.status}
                    </span>
                  </td>
                  <td className="text-sm text-muted">
                    {bt.created_at.slice(0, 16)}
                  </td>
                  <td>
                    <div className="flex gap-2">
                      <Link
                        to={`/results/${bt.id}`}
                        className="btn btn-secondary btn-sm"
                      >
                        View
                      </Link>
                      <button
                        className="btn btn-danger btn-sm"
                        onClick={() => handleDelete(bt.id)}
                      >
                        Delete
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

export default ResultsPage;
