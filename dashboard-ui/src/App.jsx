import { useState, useEffect, useCallback, useRef } from "react";
import api from "./api";
import Sidebar from "./components/Sidebar";
import StrategyCards from "./components/StrategyCards";
import SymbolsTab from "./components/tabs/SymbolsTab";
import LiveDFTab from "./components/tabs/LiveDFTab";
import PositionsTab from "./components/tabs/PositionsTab";
import HistoryTab from "./components/tabs/HistoryTab";
import TerminalTab from "./components/tabs/TerminalTab";
import SystemLogsTab from "./components/tabs/SystemLogsTab";

const TABS = [
 
  { id: "livedf",    label: "📊 Live DF" },
  { id: "positions", label: "📂 Positions" },
  { id: "history",   label: "📜 History" },
  { id: "terminal",  label: "🖥️ Terminal" },
  { id: "symbols",   label: "📋 Symbols" },
  { id: "syslogs",   label: "⚙️ System Logs" },
];

export default function App() {
  // ── core state ──────────────────────────────────────────────────────────────
  const [status, setStatus]           = useState(null);
  const [kiteLoggedIn, setKiteLoggedIn] = useState(false);
  const [activeTab, setActiveTab]     = useState("livedf");
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [refreshInterval, setRefreshInterval] = useState(5);
  const [lastSync, setLastSync]       = useState("");
  const [theme, setTheme]             = useState(localStorage.getItem('theme') || 'dark');
  const [isConnected, setIsConnected] = useState(false);

  // ── symbols cache — fetched once, updated on add/delete ───────────────────
  // { GREEN: [...], RSI: [...] }
  const [symbolsCache, setSymbolsCache] = useState({});
  const symbolsFetched = useRef(false);

  // ── fetch strategy running status only (fast, no network to Kite) ─────────
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

  // ── fetch kite login status — on mount with retry, and after session save ──
  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('theme', theme);
  }, [theme]);

  const toggleTheme = useCallback(() => {
    setTheme(prev => prev === 'dark' ? 'light' : 'dark');
  }, []);

  const fetchKiteStatus = useCallback(async () => {
    try {
      const res = await api.get("/api/kite/status");
      setKiteLoggedIn(res.data.logged_in);
    } catch {
      setKiteLoggedIn(false);
    }
  }, []);

  // ── on mount: fetch kite status, retry once after 3s if not logged in ─────
  useEffect(() => {
    let retryTimer = null;
    const checkKite = async () => {
      try {
        const res = await api.get("/api/kite/status");
        setKiteLoggedIn(res.data.logged_in);
        if (!res.data.logged_in) {
          // Retry once after 3s — API server may still be starting up
          retryTimer = setTimeout(fetchKiteStatus, 3000);
        }
      } catch {
        setKiteLoggedIn(false);
        retryTimer = setTimeout(fetchKiteStatus, 3000);
      }
    };
    checkKite();
    return () => { if (retryTimer) clearTimeout(retryTimer); };
  }, [fetchKiteStatus]);

  // ── fetch all symbols once ─────────────────────────────────────────────────
  const fetchAllSymbols = useCallback(async () => {
    try {
      const strategies = ["GREEN", "GREEN3"];
      const results = await Promise.all(
        strategies.map((s) => api.get(`/api/symbols/${s}`).then((r) => [s, r.data]))
      );
      const cache = {};
      results.forEach(([s, data]) => { cache[s] = data; });
      setSymbolsCache(cache);
      symbolsFetched.current = true;
    } catch {
      // ignore
    }
  }, []);

  // ── refresh symbols for one strategy (after add/delete) ───────────────────
  const refreshSymbols = useCallback(async (strategy) => {
    try {
      const res = await api.get(`/api/symbols/${strategy}`);
      setSymbolsCache((prev) => ({ ...prev, [strategy]: res.data }));
    } catch {
      // ignore
    }
  }, []);

  // ── on mount: fetch status and symbols ───────────────────────────────────
  useEffect(() => {
    fetchStatus();
    fetchAllSymbols();
  }, []);

  // ── auto-refresh: only status (running/stopped counts) ────────────────────
  // kite status and symbols do NOT auto-refresh
  useEffect(() => {
    if (!autoRefresh) return;
    const id = setInterval(fetchStatus, refreshInterval * 1000);
    return () => clearInterval(id);
  }, [autoRefresh, refreshInterval, fetchStatus]);

  // ── manual refresh: status + symbols ──────────────────────────────────────
  const handleRefresh = useCallback(() => {
    fetchStatus();
    fetchAllSymbols();
  }, [fetchStatus, fetchAllSymbols]);

  // ── after session saved: re-check kite status ─────────────────────────────
  const handleSessionSaved = useCallback(() => {
    fetchKiteStatus();
  }, [fetchKiteStatus]);

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
        onSessionSaved={handleSessionSaved}
        theme={theme}
        onToggleTheme={toggleTheme}
      />

      <div style={{ marginLeft: "260px", flex: 1, padding: "24px 28px", minWidth: 0 }}>
        <div style={{ marginBottom: "20px", display: "flex", alignItems: "center", gap: "12px" }}>
          <h1 style={{ fontSize: "22px", fontWeight: 800, color: "var(--text-color)", margin: 0 }}>
            📡 Multi-Strategy Live Terminal
          </h1>
          <div style={{ 
            display: "flex", 
            alignItems: "center", 
            gap: "6px",
            padding: "4px 10px",
            borderRadius: "12px",
            fontSize: "12px",
            fontWeight: 600,
            background: isConnected ? "#2ea04322" : "#da363322",
            color: isConnected ? "#2ea043" : "#da3633",
            border: `1px solid ${isConnected ? "#2ea043" : "#da3633"}`,
          }}>
            <div style={{ 
              width: "8px", 
              height: "8px", 
              borderRadius: "50%", 
              background: isConnected ? "#2ea043" : "#da3633",
              animation: isConnected ? "pulse 2s infinite" : "none"
            }}></div>
            {isConnected ? "Backend Connected" : "Backend Not Connected"}
          </div>
          <div style={{ 
            display: "flex", 
            alignItems: "center", 
            gap: "6px",
            padding: "4px 10px",
            borderRadius: "12px",
            fontSize: "12px",
            fontWeight: 600,
            background: kiteLoggedIn ? "#1f6feb22" : "#da363322",
            color: kiteLoggedIn ? "#1f6feb" : "#da3633",
            border: `1px solid ${kiteLoggedIn ? "#1f6feb" : "#da3633"}`,
          }}>
            <div style={{ 
              width: "8px", 
              height: "8px", 
              borderRadius: "50%", 
              background: kiteLoggedIn ? "#1f6feb" : "#da3633",
              animation: kiteLoggedIn ? "pulse 2s infinite" : "none"
            }}></div>
            {kiteLoggedIn ? "Kite Connected" : "Kite Not Connected"}
          </div>
        </div>

        <StrategyCards status={status} />

        <div className="tab-bar">
          {TABS.map((tab) => (
            <button
              key={tab.id}
              className={`tab-btn${activeTab === tab.id ? " active" : ""}`}
              onClick={() => setActiveTab(tab.id)}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* All tabs always mounted (display:none when inactive) so state is preserved */}
       
        <div style={{ display: activeTab === "livedf"    ? "block" : "none" }}>
          <LiveDFTab key="livedf" symbolsCache={symbolsCache} status={status} />
        </div>
        <div style={{ display: activeTab === "positions" ? "block" : "none" }}>
          <PositionsTab key="positions" />
        </div>
        <div style={{ display: activeTab === "history"   ? "block" : "none" }}>
          <HistoryTab key="history" />
        </div>
        <div style={{ display: activeTab === "terminal"  ? "block" : "none" }}>
          <TerminalTab key="terminal" status={status} />
        </div>
        <div style={{ display: activeTab === "symbols"   ? "block" : "none" }}>
          <SymbolsTab key="symbols" symbolsCache={symbolsCache} status={status} onRefreshSymbols={refreshSymbols} />
        </div>
        <div style={{ display: activeTab === "syslogs"   ? "block" : "none" }}>
          <SystemLogsTab key="syslogs" />
        </div>
      </div>
    </div>
  );
}
