import { useState, useEffect, useCallback } from "react";
import type { StockInfo, DateRange } from "../types";
import { listStocks, downloadStock, deleteStock, getDateRange } from "../services/api";

function DataPage() {
  const [stocks, setStocks] = useState<StockInfo[]>([]);
  const [dateRanges, setDateRanges] = useState<Record<string, DateRange>>({});
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  // Download form state
  const [symbol, setSymbol] = useState("");
  const [period, setPeriod] = useState("5y");
  const [downloading, setDownloading] = useState(false);

  const fetchStocks = useCallback(async () => {
    try {
      const data = await listStocks();
      setStocks(data);

      const ranges: Record<string, DateRange> = {};
      for (const stock of data) {
        try {
          ranges[stock.symbol] = await getDateRange(stock.symbol);
        } catch {
          // Skip if no data
        }
      }
      setDateRanges(ranges);
    } catch {
      setError("Failed to load stocks");
    }
  }, []);

  useEffect(() => {
    fetchStocks();
  }, [fetchStocks]);

  async function handleDownload(e: React.FormEvent) {
    e.preventDefault();
    if (!symbol.trim()) return;

    setDownloading(true);
    setError("");
    setSuccess("");

    try {
      const result = await downloadStock(symbol.trim(), undefined, undefined, period);
      setSuccess(result.message);
      setSymbol("");
      await fetchStocks();
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : "Download failed";
      setError(message);
    } finally {
      setDownloading(false);
    }
  }

  async function handleDelete(sym: string) {
    if (!confirm(`Delete all data for ${sym}?`)) return;

    setError("");
    setSuccess("");
    try {
      await deleteStock(sym);
      setSuccess(`Deleted data for ${sym}`);
      await fetchStocks();
    } catch {
      setError(`Failed to delete ${sym}`);
    }
  }

  return (
    <div>
      <h1 className="page-title">Stock Data</h1>

      {error && <div className="error-message">{error}</div>}
      {success && <div className="success-message">{success}</div>}

      <div className="card">
        <div className="card-title">Download Stock Data</div>
        <form onSubmit={handleDownload}>
          <div className="form-row">
            <div className="form-group">
              <label className="form-label">Symbol</label>
              <input
                type="text"
                className="form-input"
                placeholder="e.g. AAPL, MSFT, GOOGL"
                value={symbol}
                onChange={(e) => setSymbol(e.target.value.toUpperCase())}
              />
            </div>
            <div className="form-group">
              <label className="form-label">Period</label>
              <select
                className="form-select"
                value={period}
                onChange={(e) => setPeriod(e.target.value)}
              >
                <option value="1y">1 Year</option>
                <option value="2y">2 Years</option>
                <option value="5y">5 Years</option>
                <option value="10y">10 Years</option>
                <option value="max">Max</option>
              </select>
            </div>
          </div>
          <button
            type="submit"
            className="btn btn-primary"
            disabled={downloading || !symbol.trim()}
          >
            {downloading ? (
              <>
                <span className="spinner" /> Downloading...
              </>
            ) : (
              "Download"
            )}
          </button>
        </form>
      </div>

      <div className="card">
        <div className="card-title">Stored Stocks ({stocks.length})</div>
        {stocks.length === 0 ? (
          <div className="empty-state">
            <p>No stock data stored yet.</p>
            <p className="text-sm text-muted">
              Use the form above to download data from Yahoo Finance.
            </p>
          </div>
        ) : (
          <table className="data-table">
            <thead>
              <tr>
                <th>Symbol</th>
                <th>Name</th>
                <th>Exchange</th>
                <th>Sector</th>
                <th>Date Range</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {stocks.map((stock) => {
                const range = dateRanges[stock.symbol];
                return (
                  <tr key={stock.symbol}>
                    <td style={{ fontWeight: 600 }}>{stock.symbol}</td>
                    <td>{stock.name || "-"}</td>
                    <td>{stock.exchange || "-"}</td>
                    <td>{stock.sector || "-"}</td>
                    <td className="text-sm text-muted">
                      {range
                        ? `${range.start_date} to ${range.end_date}`
                        : "-"}
                    </td>
                    <td>
                      <button
                        className="btn btn-danger btn-sm"
                        onClick={() => handleDelete(stock.symbol)}
                      >
                        Delete
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}

export default DataPage;
