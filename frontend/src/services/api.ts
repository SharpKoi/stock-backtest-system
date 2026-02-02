import axios from "axios";
import type {
  BacktestRequest,
  BacktestResult,
  BacktestSummary,
  DateRange,
  OHLCVBar,
  StockInfo,
  StrategyInfo,
} from "../types";

const api = axios.create({
  baseURL: "http://localhost:8000/api",
  headers: { "Content-Type": "application/json" },
});

// ── Data Management ──

export async function listStocks(): Promise<StockInfo[]> {
  const { data } = await api.get<StockInfo[]>("/data/stocks");
  return data;
}

export async function getStockOHLCV(
  symbol: string,
  startDate?: string,
  endDate?: string
): Promise<OHLCVBar[]> {
  const params: Record<string, string> = {};
  if (startDate) params.start_date = startDate;
  if (endDate) params.end_date = endDate;
  const { data } = await api.get<OHLCVBar[]>(`/data/stocks/${symbol}/ohlcv`, {
    params,
  });
  return data;
}

export async function getDateRange(symbol: string): Promise<DateRange> {
  const { data } = await api.get<DateRange>(`/data/stocks/${symbol}/date-range`);
  return data;
}

export async function downloadStock(
  symbol: string,
  startDate?: string,
  endDate?: string,
  period?: string
): Promise<{ symbol: string; rows_imported: number; message: string }> {
  const { data } = await api.post("/data/download", {
    symbol,
    start_date: startDate || null,
    end_date: endDate || null,
    period: period || "5y",
  });
  return data;
}

export async function importCSV(
  symbol: string,
  file: File,
  name?: string
): Promise<{ symbol: string; rows_imported: number; message: string }> {
  const formData = new FormData();
  formData.append("symbol", symbol);
  formData.append("file", file);
  if (name) formData.append("name", name);
  const { data } = await api.post("/data/import-csv", formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return data;
}

export async function deleteStock(symbol: string): Promise<void> {
  await api.delete(`/data/stocks/${symbol}`);
}

// ── Strategies ──

export async function listStrategies(): Promise<StrategyInfo[]> {
  const { data } = await api.get<StrategyInfo[]>("/strategies");
  return data;
}

// ── Backtests ──

export async function runBacktest(
  request: BacktestRequest
): Promise<BacktestResult> {
  const { data } = await api.post<BacktestResult>("/backtests", request);
  return data;
}

export async function listBacktests(): Promise<BacktestSummary[]> {
  const { data } = await api.get<BacktestSummary[]>("/backtests");
  return data;
}

export async function getBacktestResult(
  id: number
): Promise<BacktestResult> {
  const { data } = await api.get<BacktestResult>(`/backtests/${id}`);
  return data;
}

export async function deleteBacktest(id: number): Promise<void> {
  await api.delete(`/backtests/${id}`);
}
