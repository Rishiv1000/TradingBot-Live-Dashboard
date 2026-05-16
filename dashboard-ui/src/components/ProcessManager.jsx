import { useState, useEffect, useCallback } from "react";
import api from "../api";

export default function ProcessManager() {
  const [processes, setProcesses] = useState([]);
  const [killPid, setKillPid] = useState("");
  const [loading, setLoading] = useState(false);
  const [msg, setMsg] = useState("");

  const fetchProcesses = useCallback(async () => {
    try {
      const res = await api.get("/api/system/processes");
      setProcesses(res.data);
    } catch (e) {
      console.error("Failed to fetch processes");
    }
  }, []);

  useEffect(() => {
    fetchProcesses();
    const id = setInterval(fetchProcesses, 10000);
    return () => clearInterval(id);
  }, [fetchProcesses]);

  const handleKill = async () => {
    if (!killPid) return;
    if (!window.confirm(`Are you sure you want to KILL process ${killPid}?`)) return;
    setLoading(true);
    setMsg("");
    try {
      const res = await api.post("/api/system/kill", { pid: parseInt(killPid) });
      if (res.data.success) {
        setMsg(`✅ Process ${killPid} killed.`);
        setKillPid("");
        fetchProcesses();
      } else {
        setMsg(`❌ Failed to kill process ${killPid}. Check permissions.`);
      }
    } catch (e) {
      setMsg(`❌ Error: ${e.message}`);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="card" style={{ marginTop: "24px" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "16px" }}>
        <h3 className="section-title" style={{ margin: 0, fontSize: "16px" }}>🧠 System Process Manager</h3>
        <div style={{ display: "flex", gap: "8px", alignItems: "center" }}>
          <input 
            type="number" 
            placeholder="PID" 
            value={killPid} 
            onChange={(e) => setKillPid(e.target.value)}
            style={{ 
                width: "80px", 
                padding: "6px 10px", 
                borderRadius: "6px", 
                border: "1px solid var(--border-color)", 
                background: "var(--input-bg)", 
                color: "var(--text-color)",
                fontSize: "13px"
            }}
          />
          <button className="btn-danger btn-sm" onClick={handleKill} disabled={loading} style={{ height: "32px", padding: "0 12px" }}>
            {loading ? "..." : "Kill -9"}
          </button>
        </div>
      </div>

      {msg && <div style={{ fontSize: "12px", marginBottom: "12px", padding: "8px", borderRadius: "4px", background: msg.includes("✅") ? "#2ea04311" : "#da363311", color: msg.includes("✅") ? "#2ea043" : "#da3633" }}>{msg}</div>}

      <div style={{ maxHeight: "350px", overflowY: "auto", border: "1px solid var(--border-color)", borderRadius: "8px" }}>
        <table style={{ width: "100%", fontSize: "12px", borderCollapse: "collapse" }}>
          <thead style={{ background: "var(--bg-secondary)", position: "sticky", top: 0, zIndex: 1 }}>
            <tr>
              <th style={{ textAlign: "left", padding: "10px", borderBottom: "2px solid var(--border-color)", width: "60px" }}>PID</th>
              <th style={{ textAlign: "left", padding: "10px", borderBottom: "2px solid var(--border-color)", width: "80px" }}>Start</th>
              <th style={{ textAlign: "left", padding: "10px", borderBottom: "2px solid var(--border-color)" }}>Command Line / Path</th>
            </tr>
          </thead>
          <tbody>
            {processes.length === 0 ? (
                <tr><td colSpan="3" style={{ padding: "20px", textAlign: "center", color: "var(--muted-text)" }}>No active project processes found.</td></tr>
            ) : (
                processes.map((p) => (
                    <tr key={p.pid} style={{ borderBottom: "1px solid var(--border-color)" }} className="hover-row">
                      <td style={{ padding: "10px", color: "#1f6feb", fontWeight: "bold" }}>{p.pid}</td>
                      <td style={{ padding: "10px", color: "var(--muted-text)" }}>{p.created}</td>
                      <td style={{ padding: "10px", fontFamily: "monospace", color: "var(--text-color)", wordBreak: "break-all" }}>
                        {p.cmd}
                      </td>
                    </tr>
                ))
            )}
          </tbody>
        </table>
      </div>
      <p style={{ fontSize: "11px", color: "#8b949e", marginTop: "12px" }}>
        Note: Use this to terminate orphaned uvicorn or main_runner processes. Be careful not to kill the current API process if you want to keep using the dashboard.
      </p>
    </div>
  );
}
