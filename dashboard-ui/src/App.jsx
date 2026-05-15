import { useCallback, useEffect, useState } from "react";
import api from "./api";
import Sidebar from "./components/Sidebar";
import StrategyCards from "./components/StrategyCards";
import EmaStrategyPage from "./pages/EmaStrategyPage";
import GreenStrategyPage from "./pages/GreenStrategyPage";
import GeneralTerminalTab from "./pages/GeneralTerminalTab";
import "./App.css";

const PAGES = [
  { id: "ema", label: "EMA Strategy" },
  { id: "green", label: "Green Strategy" },
  { id: "terminal", label: "Terminal" },
];

export default function App() {
  const [status, setStatus] = useState(null);
  const [kiteLoggedIn, setKiteLoggedIn] = useState(false);
  const [activePage, setActivePage] = useState("ema");
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [refreshInterval, setRefreshInterval] = useState(5);
  const [lastSync, setLastSync] = useState("");
  const [symbolsCache, setSymbolsCache] = useState({});
  const [isConnected, setIsConnected] = useState(false);
  const [theme, setTheme] = useState(localStorage.getItem("theme") || "dark");

  const fetchStatus = useCallback(async () => {
    try {
      const res = await api.get("/api/status");
      setStatus(res.data);
      setIsConnected(true);
      setLastSync(new Date().toLocaleTimeString());
    } catch {
      setIsConnected(false);
    }
  }, []);

  const fetchLiveStatus = useCallback(async () => {
    try {
      const res = await api.get("/api/kite/status");
      setKiteLoggedIn(res.data.logged_in);
    } catch {
      setKiteLoggedIn(false);
    }
  }, []);

  const fetchAllSymbols = useCallback(async () => {
    const strategies = ["EMA", "GREEN"];
    const results = await Promise.all(strategies.map((s) => api.get(`/api/${s.toLowerCase()}/symbols`).then((r) => [s, r.data]).catch(() => [s, []])));
    const cache = {};
    results.forEach(([strategy, data]) => { cache[strategy] = data; });
    setSymbolsCache(cache);
  }, []);

  const refreshSymbols = useCallback(async (strategy) => {
    try {
      const res = await api.get(`/api/${strategy.toLowerCase()}/symbols`);
      setSymbolsCache((prev) => ({ ...prev, [strategy]: res.data }));
    } catch {
      // ignore refresh failures in the UI shell
    }
  }, []);

  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
    localStorage.setItem("theme", theme);
  }, [theme]);

  useEffect(() => {
    fetchLiveStatus();
    fetchStatus();
    fetchAllSymbols();
  }, [fetchLiveStatus, fetchStatus, fetchAllSymbols]);

  useEffect(() => {
    if (!autoRefresh) return;
    const id = setInterval(() => {
      fetchStatus();
      fetchLiveStatus();
    }, refreshInterval * 1000);
    return () => clearInterval(id);
  }, [autoRefresh, refreshInterval, fetchStatus, fetchLiveStatus]);

  const handleRefresh = useCallback(() => {
    fetchStatus();
    fetchLiveStatus();
    fetchAllSymbols();
  }, [fetchStatus, fetchLiveStatus, fetchAllSymbols]);

  return (
    <div style={{ display: "flex", minHeight: "100vh" }}>
      <Sidebar
        status={status}
        kiteLoggedIn={kiteLoggedIn}
        autoRefresh={autoRefresh}
        setAutoRefresh={setAutoRefresh}
        refreshInterval={refreshInterval}
        setRefreshInterval={setRefreshInterval}
        lastSync={lastSync}
        onRefresh={handleRefresh}
        onSessionSaved={fetchLiveStatus}
        theme={theme}
        onToggleTheme={() => setTheme((prev) => prev === "dark" ? "light" : "dark")}
      />

      <div style={{ marginLeft: "260px", flex: 1, padding: "24px 28px", minWidth: 0 }}>
        <div style={{ marginBottom: "20px", display: "flex", alignItems: "center", gap: "12px", flexWrap: "wrap" }}>
          <h1 style={{ fontSize: "22px", fontWeight: 800, color: "var(--text-color)", margin: 0 }}>Multi-Strategy Live Terminal</h1>
          <div className="pill" style={{ background: isConnected ? "#2ea04322" : "#da363322", color: isConnected ? "#2ea043" : "#da3633", border: `1px solid ${isConnected ? "#2ea043" : "#da3633"}` }}>
            {isConnected ? "Backend Connected" : "Backend Not Connected"}
          </div>
          <div className="pill" style={{ background: kiteLoggedIn ? "#1f6feb22" : "#da363322", color: kiteLoggedIn ? "#1f6feb" : "#da3633", border: `1px solid ${kiteLoggedIn ? "#1f6feb" : "#da3633"}` }}>
            {kiteLoggedIn ? "Kite Connected" : "Kite Not Connected"}
          </div>
        </div>

        <StrategyCards status={status} />

        <div className="tab-bar">
          {PAGES.map((page) => (
            <button key={page.id} className={`tab-btn${activePage === page.id ? " active" : ""}`} onClick={() => setActivePage(page.id)}>
              {page.label}
            </button>
          ))}
        </div>

        <div style={{ display: activePage === "ema" ? "block" : "none" }}>
          <EmaStrategyPage status={status} symbols={symbolsCache.EMA || []} onRefreshSymbols={refreshSymbols} />
        </div>
        <div style={{ display: activePage === "green" ? "block" : "none" }}>
          <GreenStrategyPage status={status} symbols={symbolsCache.GREEN || []} onRefreshSymbols={refreshSymbols} />
        </div>
        <div style={{ display: activePage === "terminal" ? "block" : "none" }}>
          <GeneralTerminalTab />
        </div>
      </div>
    </div>
  );
}
