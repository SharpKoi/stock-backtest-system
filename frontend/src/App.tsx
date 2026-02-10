import { Routes, Route, NavLink, Navigate } from "react-router-dom";
import { useAuth } from "./contexts/AuthContext";
import ProtectedRoute from "./components/ProtectedRoute";
import Login from "./pages/Login";
import Register from "./pages/Register";
import DataPage from "./pages/DataPage";
import BacktestPage from "./pages/BacktestPage";
import ResultsPage from "./pages/ResultsPage";
import ResultDetailPage from "./pages/ResultDetailPage";
import StrategyEditorPage from "./pages/StrategyEditorPage";
import IndicatorEditorPage from "./pages/IndicatorEditorPage";

function App() {
  const { isAuthenticated, user, logout } = useAuth();

  // Auth-only pages (login/register)
  if (!isAuthenticated) {
    return (
      <div className="app-container auth-layout">
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />
          <Route path="*" element={<Navigate to="/login" replace />} />
        </Routes>
      </div>
    );
  }

  // Protected app pages
  return (
    <div className="app-container">
      <nav className="sidebar">
        <div className="sidebar-brand">Backtest System</div>
        <div className="sidebar-user">
          <span className="user-email">{user?.email}</span>
          <button onClick={logout} className="btn-logout">
            Logout
          </button>
        </div>
        <ul className="sidebar-nav">
          <li>
            <NavLink
              to="/"
              className={({ isActive }) => (isActive ? "active" : "")}
              end
            >
              Stock Data
            </NavLink>
          </li>
          <li>
            <NavLink
              to="/strategies"
              className={({ isActive }) => (isActive ? "active" : "")}
            >
              Strategy Editor
            </NavLink>
          </li>
          <li>
            <NavLink
              to="/indicators"
              className={({ isActive }) => (isActive ? "active" : "")}
            >
              Indicator Editor
            </NavLink>
          </li>
          <li>
            <NavLink
              to="/backtest"
              className={({ isActive }) => (isActive ? "active" : "")}
            >
              Run Backtest
            </NavLink>
          </li>
          <li>
            <NavLink
              to="/results"
              className={({ isActive }) => (isActive ? "active" : "")}
            >
              Results
            </NavLink>
          </li>
        </ul>
      </nav>
      <main className="main-content">
        <Routes>
          <Route
            path="/"
            element={
              <ProtectedRoute>
                <DataPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/strategies"
            element={
              <ProtectedRoute>
                <StrategyEditorPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/indicators"
            element={
              <ProtectedRoute>
                <IndicatorEditorPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/backtest"
            element={
              <ProtectedRoute>
                <BacktestPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/results"
            element={
              <ProtectedRoute>
                <ResultsPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/results/:id"
            element={
              <ProtectedRoute>
                <ResultDetailPage />
              </ProtectedRoute>
            }
          />
        </Routes>
      </main>
    </div>
  );
}

export default App;
