import axios from "axios";
import type {
  BacktestRequest,
  BacktestResult,
  BacktestSummary,
  DateRange,
  OHLCVBar,
  StockInfo,
  StrategyInfo,
  Token,
  UserCreate,
  UserLogin,
  UserResponse,
} from "../types";

export const api = axios.create({
  baseURL: "http://localhost:8000/api",
  headers: { "Content-Type": "application/json" },
});

// Add auth token to all requests
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem("auth_token");
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Handle 401 Unauthorized responses
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Clear invalid token and redirect to login
      localStorage.removeItem("auth_token");
      if (window.location.pathname !== "/login" && window.location.pathname !== "/register") {
        window.location.href = "/login";
      }
    }
    return Promise.reject(error);
  }
);

// ── Authentication ──

export async function registerUser(userData: UserCreate): Promise<UserResponse> {
  const { data } = await api.post<UserResponse>("/auth/register", userData);
  return data;
}

export async function loginUser(credentials: UserLogin): Promise<Token> {
  const { data } = await api.post<Token>("/auth/login", credentials);
  return data;
}

export async function getCurrentUser(): Promise<UserResponse> {
  const { data } = await api.get<UserResponse>("/auth/me");
  return data;
}

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
