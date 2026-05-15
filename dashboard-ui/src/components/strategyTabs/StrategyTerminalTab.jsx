import { useEffect, useRef, useState } from "react";
import api from "../../api";

export default function StrategyTerminalTab({ strategy, color, endpointPrefix }) {
  const [lines, setLines] = useState("No log yet.");
  const [loading, setLoading] = useState(false);
  const terminalRef = useRef(null);

  useEffect(() => {
    const fetchLog = async () => {
      try {
        const res = await api.get(`${endpointPrefix}/terminal`);
        setLines(res.data.lines || "Log is empty.");
      } catch {
        setLines("Error reading log.");
      }
    };
    fetchLog();
    const id = setInterval(fetchLog, 3000);
    return () => clearInterval(id);
  }, [endpointPrefix]);

  useEffect(() => {
    if (terminalRef.current) terminalRef.current.scrollTop = terminalRef.current.scrollHeight;
  }, [lines]);

  const clearLog = async () => {
    setLoading(true);
    try {
      await api.delete(`${endpointPrefix}/terminal`);
      setLines("Log cleared.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="strategy-section">
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "10px" }}>
        <div className="strategy-section-header" style={{ color, marginBottom: 0 }}>{strategy} Terminal</div>
        <button className="btn-secondary btn-sm" onClick={clearLog} disabled={loading}>Clear</button>
      </div>
      <div className="terminal-block" ref={terminalRef}>{lines}</div>
    </div>
  );
}
