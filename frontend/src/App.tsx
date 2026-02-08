import { Routes, Route, NavLink } from "react-router-dom";
import DataPage from "./pages/DataPage";
import BacktestPage from "./pages/BacktestPage";
import ResultsPage from "./pages/ResultsPage";
import ResultDetailPage from "./pages/ResultDetailPage";
import StrategyEditorPage from "./pages/StrategyEditorPage";
import IndicatorEditorPage from "./pages/IndicatorEditorPage";

function App() {
  return (
    <div className="app-container">
      <nav className="sidebar">
        <div className="sidebar-brand">Backtest System</div>
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
          <Route path="/" element={<DataPage />} />
          <Route path="/strategies" element={<StrategyEditorPage />} />
          <Route path="/indicators" element={<IndicatorEditorPage />} />
          <Route path="/backtest" element={<BacktestPage />} />
          <Route path="/results" element={<ResultsPage />} />
          <Route path="/results/:id" element={<ResultDetailPage />} />
        </Routes>
      </main>
    </div>
  );
}

export default App;
