import { useState, useEffect, useCallback } from "react";
import api from "../../api";

export default function DatabaseTab() {
  const [dbStatus, setDbStatus] = useState(null);
  const [loading, setLoading] = useState(false);
  const [newSize, setNewSize] = useState(32);
  const [resizeMsg, setResizeMsg] = useState("");
  
  // Logs state
  const [backendLogs, setBackendLogs] = useState("Loading backend logs...");
  const [frontendLogs, setFrontendLogs] = useState("Loading frontend logs...");
  const [activeLogTab, setActiveLogTab] = useState("backend");

  const fetchDbStatus = async () => {
    try {
      const res = await api.get("/api/db/status");
      setDbStatus(res.data);
      if (res.data.pool_size) setNewSize(res.data.pool_size);
    } catch (e) {
      console.error("Fetch DB status failed:", e);
    }
  };

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

  const handleResize = async () => {
    setResizeMsg("");
    try {
      const res = await api.post("/api/db/resize", { new_size: parseInt(newSize) });
      if (res.data.success) {
        setResizeMsg("✅ " + res.data.message);
        fetchDbStatus();
      } else {
        setResizeMsg("❌ " + res.data.error);
      }
    } catch (e) {
      setResizeMsg("❌ " + (e.response?.data?.detail || e.message));
    }
  };

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
      
      {/* --- DATABASE SECTION --- */}
      <div className="strategy-section">
        <div className="strategy-section-header" style={{ color: "#58a6ff", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <span>🗄️ Database & Connection Pool</span>
          {loading && <span style={{ fontSize: "12px", color: "#8b949e" }}>Refreshing...</span>}
        </div>

        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: "12px", marginBottom: "20px" }}>
          <div className="stat-card" style={{ padding: "12px", background: "#161b22", border: "1px solid #30363d", borderRadius: "8px" }}>
            <div style={{ fontSize: "11px", color: "#8b949e" }}>Connected Threads</div>
            <div style={{ fontSize: "20px", fontWeight: 700, color: "#58a6ff" }}>{dbStatus?.threads_connected || 0}</div>
          </div>
          <div className="stat-card" style={{ padding: "12px", background: "#161b22", border: "1px solid #30363d", borderRadius: "8px" }}>
            <div style={{ fontSize: "11px", color: "#8b949e" }}>Running Threads</div>
            <div style={{ fontSize: "20px", fontWeight: 700, color: "#2ea043" }}>{dbStatus?.threads_running || 0}</div>
          </div>
          <div className="stat-card" style={{ padding: "12px", background: "#161b22", border: "1px solid #30363d", borderRadius: "8px" }}>
            <div style={{ fontSize: "11px", color: "#8b949e" }}>Pool Limit</div>
            <div style={{ fontSize: "20px", fontWeight: 700, color: "#ff9800" }}>{dbStatus?.pool_size || 32}</div>
          </div>
        </div>

        <div style={{ padding: "16px", background: "#0d1117", border: "1px solid #30363d", borderRadius: "8px" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "16px" }}>
            <div style={{ flex: 1 }}>
              <div style={{ fontSize: "13px", marginBottom: "8px", color: "var(--text-color)" }}>Resize Connection Pool</div>
              <input 
                type="range" min="5" max="32" step="1" 
                value={newSize} onChange={(e) => setNewSize(e.target.value)} 
                style={{ width: "100%", height: "6px", cursor: "pointer" }}
              />
              <div style={{ display: "flex", justifyContent: "space-between", marginTop: "4px", fontSize: "11px", color: "#8b949e" }}>
                <span>5</span>
                <span>New: {newSize}</span>
                <span>32</span>
              </div>
            </div>
            <button className="btn-primary btn-sm" onClick={handleResize} style={{ height: "36px", padding: "0 16px" }}>Update</button>
          </div>
          {resizeMsg && <div style={{ fontSize: "12px", marginTop: "10px", color: resizeMsg.startsWith("✅") ? "#2ea043" : "#da3633" }}>{resizeMsg}</div>}
        </div>
      </div>

      {/* --- SYSTEM LOGS SECTION --- */}
      <div className="strategy-section">
        <div className="strategy-section-header" style={{ color: "#79c0ff", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <span>📜 System Logs (FastAPI & Vite)</span>
          <div style={{ display: "flex", gap: "6px" }}>
            <button 
              className={`btn-sm ${activeLogTab === "backend" ? "btn-primary" : "btn-secondary"}`}
              onClick={() => setActiveLogTab("backend")}
              style={{ padding: "2px 8px", fontSize: "11px" }}
            >
              Backend
            </button>
            <button 
              className={`btn-sm ${activeLogTab === "frontend" ? "btn-blue" : "btn-secondary"}`}
              onClick={() => setActiveLogTab("frontend")}
              style={{ padding: "2px 8px", fontSize: "11px" }}
            >
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
