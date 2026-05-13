import { useState, useEffect } from "react";
import api from "../../api";

export default function DatabaseTab() {
  const [dbStatus, setDbStatus] = useState(null);
  const [loading, setLoading] = useState(false);
  const [newSize, setNewSize] = useState(64);
  const [resizeMsg, setResizeMsg] = useState("");

  const fetchDbStatus = async () => {
    setLoading(true);
    try {
      const res = await api.get("/api/db/status");
      setDbStatus(res.data);
      if (res.data.pool_size) setNewSize(res.data.pool_size);
    } catch (e) {
      console.error("Fetch DB status failed:", e);
    } finally {
      setLoading(false);
    }
  };

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
    const id = setInterval(fetchDbStatus, 5000);
    return () => clearInterval(id);
  }, []);

  if (!dbStatus && loading) return <div style={{ padding: "20px", color: "#8b949e" }}>Loading Database Info...</div>;

  return (
    <div className="strategy-section" style={{ maxWidth: "800px" }}>
      <div className="strategy-section-header" style={{ color: "#58a6ff" }}>
        🗄️ MySQL Connection Pool Management
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: "16px", marginBottom: "24px" }}>
        <div className="stat-card" style={{ background: "#161b22", padding: "16px", borderRadius: "8px", border: "1px solid #30363d" }}>
          <div style={{ fontSize: "12px", color: "#8b949e", marginBottom: "4px" }}>Connected Threads</div>
          <div style={{ fontSize: "24px", fontWeight: 700, color: "#58a6ff" }}>{dbStatus?.threads_connected || 0}</div>
        </div>
        <div className="stat-card" style={{ background: "#161b22", padding: "16px", borderRadius: "8px", border: "1px solid #30363d" }}>
          <div style={{ fontSize: "12px", color: "#8b949e", marginBottom: "4px" }}>Running Threads</div>
          <div style={{ fontSize: "24px", fontWeight: 700, color: "#2ea043" }}>{dbStatus?.threads_running || 0}</div>
        </div>
        <div className="stat-card" style={{ background: "#161b22", padding: "16px", borderRadius: "8px", border: "1px solid #30363d" }}>
          <div style={{ fontSize: "12px", color: "#8b949e", marginBottom: "4px" }}>Active Pool Size</div>
          <div style={{ fontSize: "24px", fontWeight: 700, color: "#ff9800" }}>{dbStatus?.pool_size || 0}</div>
        </div>
      </div>

      <div style={{ padding: "20px", background: "#0d1117", borderRadius: "8px", border: "1px solid #30363d" }}>
        <h3 style={{ fontSize: "16px", marginBottom: "16px", color: "var(--text-color)" }}>Resize Connection Pool</h3>
        <p style={{ fontSize: "13px", color: "#8b949e", marginBottom: "20px" }}>
          Current Pool: <strong style={{ color: "#58a6ff" }}>{dbStatus?.pool_name}</strong> | 
          Database: <strong style={{ color: "#58a6ff" }}>{dbStatus?.db_name}</strong>
        </p>

        <div style={{ display: "flex", alignItems: "center", gap: "20px", marginBottom: "20px" }}>
          <div style={{ flex: 1 }}>
            <input 
              type="range" 
              min="10" 
              max="200" 
              step="5" 
              value={newSize} 
              onChange={(e) => setNewSize(e.target.value)} 
              style={{ width: "100%", height: "8px", borderRadius: "4px", background: "#30363d", cursor: "pointer" }}
            />
            <div style={{ display: "flex", justifyContent: "space-between", marginTop: "8px", fontSize: "12px", color: "#8b949e" }}>
              <span>10</span>
              <span style={{ color: "var(--text-color)", fontWeight: 700 }}>New Size: {newSize}</span>
              <span>200</span>
            </div>
          </div>
          <button 
            className="btn-primary" 
            onClick={handleResize}
            style={{ padding: "10px 24px" }}
          >
            Update Pool Size
          </button>
        </div>

        {resizeMsg && (
          <div style={{ 
            padding: "12px", 
            borderRadius: "6px", 
            fontSize: "13px",
            background: resizeMsg.startsWith("✅") ? "#2ea04311" : "#da363311",
            color: resizeMsg.startsWith("✅") ? "#2ea043" : "#da3633",
            border: `1px solid ${resizeMsg.startsWith("✅") ? "#2ea043" : "#da3633"}`
          }}>
            {resizeMsg}
          </div>
        )}
      </div>

      <div style={{ marginTop: "24px", padding: "12px", borderRadius: "6px", background: "#f8514911", border: "1px solid #f8514933" }}>
        <p style={{ fontSize: "12px", color: "#f85149", margin: 0 }}>
          ⚠️ <b>Note:</b> Changing pool size updates the configuration. For immediate effect, please restart the backend server using the <b>Shutdown</b> button in the sidebar and let the auto-restarter bring it back up.
        </p>
      </div>
    </div>
  );
}
