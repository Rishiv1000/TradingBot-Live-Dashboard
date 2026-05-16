import { useState, useEffect, useCallback } from "react";
import api from "../api";
import ProcessManager from "../components/ProcessManager";

export default function SystemLogsTab() {
  const [backendLogs, setBackendLogs] = useState("Loading backend logs...");
  const [frontendLogs, setFrontendLogs] = useState("Loading frontend logs...");
  const [activeSubTab, setActiveSubTab] = useState("backend");

  const fetchLogs = useCallback(async () => {
    try {
      const bRes = await api.get("/api/logs/backend");
      setBackendLogs(bRes.data.lines);
    } catch (e) {
      setBackendLogs("Failed to fetch backend logs.");
    }

    try {
      const fRes = await api.get("/api/logs/frontend");
      setFrontendLogs(fRes.data.lines);
    } catch (e) {
      setFrontendLogs("Failed to fetch frontend logs.");
    }
  }, []);

  useEffect(() => {
    fetchLogs();
    const id = setInterval(fetchLogs, 5000);
    return () => clearInterval(id);
  }, [fetchLogs]);

  return (
    <div>
      <div className="card">
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "16px" }}>
          <h3 className="section-title" style={{ margin: 0 }}>⚙️ System Logs</h3>
          <div style={{ display: "flex", gap: "8px" }}>
            <button 
              className={`btn-sm ${activeSubTab === "backend" ? "btn-primary" : "btn-secondary"}`}
              onClick={() => setActiveSubTab("backend")}
            >
              Backend (FastAPI)
            </button>
            <button 
              className={`btn-sm ${activeSubTab === "frontend" ? "btn-blue" : "btn-secondary"}`}
              onClick={() => setActiveSubTab("frontend")}
            >
              Frontend (Vite)
            </button>
            <button className="btn-sm btn-secondary" onClick={fetchLogs}>🔄 Refresh</button>
          </div>
        </div>

        <div className="terminal-block" style={{ height: "500px", max_height: "600px" }}>
          {activeSubTab === "backend" ? backendLogs : frontendLogs}
        </div>
        
        <p style={{ fontSize: "11px", color: "#8b949e", marginTop: "12px" }}>
          Showing last 200 lines. Auto-refreshing every 5s.
        </p>
      </div>

      <ProcessManager />
    </div>
  );
}
