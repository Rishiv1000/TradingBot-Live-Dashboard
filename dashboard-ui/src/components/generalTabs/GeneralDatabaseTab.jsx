import { useState, useEffect, useCallback } from "react";
import api from "../../api";

export default function GeneralDatabaseTab() {
  const [dbStatus, setDbStatus] = useState(null);
  const [backendLogs, setBackendLogs] = useState("Loading backend logs...");
  const [frontendLogs, setFrontendLogs] = useState("Loading frontend logs...");
  const [activeLogTab, setActiveLogTab] = useState("backend");

  const fetchDbStatus = async () => {
    try {
      const res = await api.get("/api/db/status");
      setDbStatus(res.data);
    } catch (e) {
      setDbStatus({ error: e.response?.data?.detail || e.message });
    }
  };

  const fetchLogs = useCallback(async () => {
    try {
      const bRes = await api.get("/api/logs/backend");
      setBackendLogs(bRes.data.lines);
    } catch {
      setBackendLogs("Failed to fetch backend logs.");
    }
    try {
      const fRes = await api.get("/api/logs/frontend");
      setFrontendLogs(fRes.data.lines);
    } catch {
      setFrontendLogs("Failed to fetch frontend logs.");
    }
  }, []);

  useEffect(() => {
    fetchDbStatus();
    fetchLogs();
    const id = setInterval(() => {
      fetchDbStatus();
      fetchLogs();
    }, 5000);
    return () => clearInterval(id);
  }, [fetchLogs]);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "24px" }}>
      <div className="strategy-section">
        <div className="strategy-section-header" style={{ color: "#58a6ff" }}>
          Database Status
        </div>
        <div className="metric-box" style={{ maxWidth: "420px" }}>
          <div className="metric-label">Database</div>
          <div className="metric-value" style={{ fontSize: "18px" }}>
            {dbStatus?.error ? "Not Connected" : dbStatus?.db_name || "Unknown"}
          </div>
          {dbStatus?.error && <div style={{ color: "#da3633", fontSize: "12px", marginTop: "8px" }}>{dbStatus.error}</div>}
        </div>
      </div>

      <div className="strategy-section">
        <div className="strategy-section-header" style={{ color: "#79c0ff", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <span>System Logs</span>
          <div style={{ display: "flex", gap: "6px" }}>
            <button className={`btn-sm ${activeLogTab === "backend" ? "btn-primary" : "btn-secondary"}`} onClick={() => setActiveLogTab("backend")} style={{ padding: "2px 8px", fontSize: "11px" }}>
              Backend
            </button>
            <button className={`btn-sm ${activeLogTab === "frontend" ? "btn-blue" : "btn-secondary"}`} onClick={() => setActiveLogTab("frontend")} style={{ padding: "2px 8px", fontSize: "11px" }}>
              Frontend
            </button>
          </div>
        </div>
        <div className="terminal-block" style={{ height: "400px", fontSize: "11px", background: "#010409" }}>
          {activeLogTab === "backend" ? backendLogs : frontendLogs}
        </div>
        <div style={{ fontSize: "10px", color: "#8b949e", marginTop: "8px", textAlign: "right" }}>
          Auto-refreshing every 5s | Last 200 lines
        </div>
      </div>
    </div>
  );
}
