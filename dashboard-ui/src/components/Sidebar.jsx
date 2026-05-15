import { useState, useEffect } from "react";
import api from "../api";

const SIDEBAR_STYLE = {
  position: "fixed",
  left: 0,
  top: 0,
  bottom: 0,
  width: "260px",
  background: "var(--sidebar-bg)",
  borderRight: "1px solid var(--border-color)",
  overflowY: "auto",
  padding: "16px 14px",
  zIndex: 100,
  display: "flex",
  flexDirection: "column",
  gap: "0",
};

export default function Sidebar({
  status,
  kiteLoggedIn,
  autoRefresh,
  setAutoRefresh,
  refreshInterval,
  setRefreshInterval,
  lastSync,
  onRefresh,
  onSessionSaved,
  theme,
  onToggleTheme,
}) {
  const [loginUrl, setLoginUrl] = useState("");
  const [showUrlModal, setShowUrlModal] = useState(false);
  const [requestToken, setRequestToken] = useState("");
  const [sessionMsg, setSessionMsg] = useState("");
  const [sessionLoading, setSessionLoading] = useState(false);
  const [realTradingEnabled, setRealTradingEnabled] = useState(false);
  const [configLoading, setConfigLoading] = useState(false);

  useEffect(() => {
    const fetchConfig = async () => {
      try {
        const res = await api.get("/api/config/trading");
        setRealTradingEnabled(res.data.real_trading_enabled);
      } catch (e) {
        console.error("Failed to fetch trading config", e);
      }
    };
    fetchConfig();
  }, []);

  const handleToggleRealTrading = async () => {
    const newValue = !realTradingEnabled;
    if (newValue && !window.confirm("⚠️ WARNING: enabling REAL TRADING will place actual orders. Are you sure?")) return;
    
    setConfigLoading(true);
    try {
      const res = await api.post("/api/config/trading", { real_trading_enabled: newValue });
      if (res.data.success) {
        setRealTradingEnabled(res.data.real_trading_enabled);
      }
    } catch (e) {
      alert("Failed to update config: " + (e.response?.data?.detail || e.message));
    } finally {
      setConfigLoading(false);
    }
  };

  const handleGetLoginUrl = async () => {
    try {
      const res = await api.get("/api/kite/login_url");
      setLoginUrl(res.data.url);
      setShowUrlModal(true);
    } catch (e) {
      alert("Failed to get login URL: " + (e.response?.data?.detail || e.message));
    }
  };

  const handleGenerateSession = async () => {
    if (!requestToken.trim()) {
      setSessionMsg("Enter a request token first.");
      return;
    }
    setSessionLoading(true);
    setSessionMsg("");
    try {
      const res = await api.post("/api/kite/session", { request_token: requestToken.trim() });
      if (res.data.success) {
        setSessionMsg("✅ Session saved!");
        setRequestToken("");
        onSessionSaved();   // re-check kite status once
        onRefresh();
      } else {
        setSessionMsg("❌ " + (res.data.error || "Unknown error"));
      }
    } catch (e) {
      setSessionMsg("❌ " + (e.response?.data?.detail || e.message));
    } finally {
      setSessionLoading(false);
    }
  };

  const handleStart = async (strategy) => {
    try {
      await api.post(`/api/strategy/${strategy}/start`);
      onRefresh();
    } catch (e) {
      alert("Start failed: " + (e.response?.data?.detail || e.message));
    }
  };

  const handleStop = async (strategy) => {
    try {
      await api.post(`/api/strategy/${strategy}/stop`);
      onRefresh();
    } catch (e) {
      alert("Stop failed: " + (e.response?.data?.detail || e.message));
    }
  };

  const handleTerminate = async (strategy) => {
    try {
      await api.post(`/api/strategy/${strategy}/terminate`);
      onRefresh();
    } catch (e) {
      alert("Terminate failed: " + (e.response?.data?.detail || e.message));
    }
  };

  const [setupDbMsg, setSetupDbMsg] = useState("");
  const [setupDbLoading, setSetupDbLoading] = useState(false);
  const [defaultsMsg, setDefaultsMsg] = useState("");
  const [defaultsLoading, setDefaultsLoading] = useState(false);
  const [reloadLoading, setReloadLoading] = useState(false);
  const [stopApiMsg, setStopApiMsg] = useState("");
  const [logoutMsg, setLogoutMsg] = useState("");

  const handleSetupDb = async () => {
    setSetupDbLoading(true); setSetupDbMsg("");
    try {
      const res = await api.post("/api/setup-db");
      setSetupDbMsg(res.data.success ? `✅ ${res.data.message}` : `❌ ${res.data.error}`);
    } catch (e) {
      setSetupDbMsg("❌ " + (e.response?.data?.detail || e.message));
    } finally { setSetupDbLoading(false); }
  };

  const handleSetDefaults = async () => {
    setDefaultsLoading(true); setDefaultsMsg("");
    try {
      const res = await api.post("/api/set-defaults");
      setDefaultsMsg(res.data.success ? `✅ ${res.data.updated} tokens updated` : `❌ ${res.data.error}`);
      onRefresh();
    } catch (e) {
      setDefaultsMsg("❌ " + (e.response?.data?.detail || e.message));
    } finally { setDefaultsLoading(false); }
  };


  const handleLogout = async () => {
    if (!window.confirm("This will kill all strategies and clear the session token. Continue?")) return;
    setLogoutMsg("");
    try {
      const res = await api.post("/api/kite/logout");
      if (res.data.success) {
        setLogoutMsg("✅ Logged out. All strategies stopped.");
        onSessionSaved(); // re-check kite status → will show Not Logged In
        onRefresh();
      } else {
        setLogoutMsg("❌ " + (res.data.error || "Unknown error"));
      }
    } catch (e) {
      setLogoutMsg("❌ " + (e.response?.data?.detail || e.message));
    }
  };

  return (
    <>
      <div style={SIDEBAR_STYLE}>
        {/* Title */}
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "16px" }}>
          <div style={{ fontSize: "16px", fontWeight: 800, color: "var(--text-color)" }}>
            📡 Live Terminal
          </div>
          <button 
            onClick={onToggleTheme}
            className="btn-secondary btn-sm"
            style={{ padding: "4px 8px", fontSize: "14px" }}
            title={`Switch to ${theme === 'dark' ? 'light' : 'dark'} mode`}
          >
            {theme === 'dark' ? '☀️' : '🌙'}
          </button>
        </div>

        <hr className="divider" />

        {/* Kite Login */}
        <div style={{ marginBottom: "16px" }}>
          <div style={{ fontSize: "12px", fontWeight: 700, color: "var(--muted-text)", textTransform: "uppercase", letterSpacing: "0.5px", marginBottom: "8px" }}>
            🔑 Kite Login
          </div>
          {kiteLoggedIn ? (
            <div style={{ color: "#2ea043", fontWeight: 700, fontSize: "13px", marginBottom: "8px" }}>
              ✅ Session Active
            </div>
          ) : (
            <div style={{ color: "#e3b341", fontWeight: 700, fontSize: "13px", marginBottom: "8px" }}>
              ⚠️ Not Logged In
            </div>
          )}
          <button
            className="btn-blue"
            style={{ width: "100%", marginBottom: "8px" }}
            onClick={handleGetLoginUrl}
          >
            Get Login URL
          </button>
          <input
            type="text"
            placeholder="Paste Request Token"
            value={requestToken}
            onChange={(e) => setRequestToken(e.target.value)}
            style={{ width: "100%", marginBottom: "6px" }}
          />
          <button
            className="btn-primary"
            style={{ width: "100%" }}
            onClick={handleGenerateSession}
            disabled={sessionLoading}
          >
            {sessionLoading ? "Generating..." : "Generate Session"}
          </button>
          {sessionMsg && (
            <div style={{ fontSize: "12px", marginTop: "6px", color: sessionMsg.startsWith("✅") ? "#2ea043" : "#da3633" }}>
              {sessionMsg}
            </div>
          )}

          <div style={{ marginTop: "16px", padding: "10px", borderRadius: "8px", border: `1px solid ${realTradingEnabled ? "#da3633" : "var(--border-color)"}`, background: realTradingEnabled ? "#da363311" : "transparent" }}>
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
              <div style={{ fontSize: "12px", fontWeight: 700, color: realTradingEnabled ? "#da3633" : "var(--text-color)" }}>
                🚀 REAL TRADING
              </div>
              <div 
                onClick={handleToggleRealTrading}
                style={{ 
                  width: "40px", 
                  height: "20px", 
                  background: realTradingEnabled ? "#da3633" : "#30363d", 
                  borderRadius: "10px", 
                  position: "relative", 
                  cursor: configLoading ? "not-allowed" : "pointer",
                  transition: "0.2s"
                }}
              >
                <div style={{ 
                  width: "16px", 
                  height: "16px", 
                  background: "#fff", 
                  borderRadius: "50%", 
                  position: "absolute", 
                  top: "2px", 
                  left: realTradingEnabled ? "22px" : "2px",
                  transition: "0.2s"
                }} />
              </div>
            </div>
            <div style={{ fontSize: "10px", color: "var(--muted-text)", marginTop: "4px" }}>
              {realTradingEnabled ? "Real orders will be placed." : "Paper trading mode active."}
            </div>
          </div>
        </div>

        <hr className="divider" />

        {/* Strategy Control */}
        <div style={{ marginBottom: "16px" }}>
          <div style={{ fontSize: "12px", fontWeight: 700, color: "var(--muted-text)", textTransform: "uppercase", letterSpacing: "0.5px", marginBottom: "10px" }}>
            ⚙️ Strategy Control
          </div>

          {status && Object.entries(status).map(([strategy, info]) => {
            const running = info.running;
            const statusColor = running ? "#2ea043" : "#da3633";
            const statusLabel = running ? "RUNNING" : "STOPPED";
            return (
              <div key={strategy} style={{ marginBottom: "14px" }}>
                <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "4px" }}>
                  <span style={{ fontWeight: 800, color: "var(--text-color)", fontSize: "13px" }}>{strategy}</span>
                  <span
                    className="pill"
                    style={{
                      background: statusColor + "22",
                      color: statusColor,
                      border: `1px solid ${statusColor}`,
                    }}
                  >
                    {statusLabel}
                  </span>
                </div>
                <div style={{ fontSize: "11px", color: "var(--muted-text)", marginBottom: "6px" }}>
                  Symbols: {info.symbol_count} &nbsp;|&nbsp; Open: {info.open_count}
                </div>
                <div style={{ display: "flex", gap: "4px" }}>
                  <button
                    className="btn-primary btn-sm"
                    style={{ flex: 1 }}
                    onClick={() => handleStart(strategy)}
                    title={`Start ${strategy}`}
                  >
                    ▶
                  </button>
                  <button
                    className="btn-secondary btn-sm"
                    style={{ flex: 1 }}
                    onClick={() => handleStop(strategy)}
                    title={`Stop ${strategy}`}
                  >
                    ■
                  </button>
                  <button
                    className="btn-danger btn-sm"
                    style={{ flex: 1 }}
                    onClick={() => handleTerminate(strategy)}
                    title={`Terminate ${strategy}`}
                  >
                    ✕
                  </button>
                </div>
              </div>
            );
          })}

        </div>

        <hr className="divider" />

        {/* Setup */}
        <div style={{ marginBottom: "16px" }}>
          <div style={{ fontSize: "12px", fontWeight: 700, color: "var(--muted-text)", textTransform: "uppercase", letterSpacing: "0.5px", marginBottom: "8px" }}>
            🔧 Setup
          </div>
          <button className="btn-blue" style={{ width: "100%", marginBottom: "6px" }} onClick={handleSetupDb} disabled={setupDbLoading}>
            {setupDbLoading ? "Setting up..." : "🗄️ Setup DB"}
          </button>
          {setupDbMsg && <div style={{ fontSize: "11px", marginBottom: "6px", color: setupDbMsg.startsWith("✅") ? "#2ea043" : "#da3633" }}>{setupDbMsg}</div>}
          <button className="btn-secondary" style={{ width: "100%" }} onClick={handleSetDefaults} disabled={defaultsLoading}>
            {defaultsLoading ? "Running..." : "⚙️ Set Defaults"}
          </button>
          <div style={{ fontSize: "11px", color: "var(--muted-text)", marginTop: "4px" }}>Resets positions & fills tokens</div>
          {defaultsMsg && <div style={{ fontSize: "11px", marginTop: "4px", color: defaultsMsg.startsWith("✅") ? "#2ea043" : "#da3633" }}>{defaultsMsg}</div>}
        </div>

        <hr className="divider" />

        <div style={{ fontSize: "11px", color: "var(--muted-text)", marginTop: "auto", paddingTop: "8px" }}>
          Last sync: {lastSync || "—"}
        </div>

        {/* Logout */}
        <div style={{ marginTop: "12px" }}>
          <button
            className="btn-danger"
            style={{ width: "100%", fontSize: "12px" }}
            onClick={handleLogout}
          >
            🔴 Logout &amp; Expire Session
          </button>
          {logoutMsg && (
            <div style={{ fontSize: "11px", marginTop: "6px", color: logoutMsg.startsWith("✅") ? "#2ea043" : "#da3633" }}>
              {logoutMsg}
            </div>
          )}
        </div>

      </div>

      {/* Login URL Modal */}
      {showUrlModal && (
        <div className="modal-overlay" onClick={() => setShowUrlModal(false)}>
          <div className="modal-box" onClick={(e) => e.stopPropagation()}>
            <div className="modal-title">🔗 Kite Login URL</div>
            <div className="modal-url">{loginUrl}</div>
            <div style={{ display: "flex", gap: "8px" }}>
              <button
                className="btn-blue"
                onClick={() => { navigator.clipboard.writeText(loginUrl); }}
              >
                Copy URL
              </button>
              <a href={loginUrl} target="_blank" rel="noreferrer">
                <button className="btn-primary">Open in Browser</button>
              </a>
              <button className="btn-secondary" onClick={() => setShowUrlModal(false)}>
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
