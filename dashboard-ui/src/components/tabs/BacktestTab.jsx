import { useState, useEffect } from "react";
import api from "../../api";

export default function BacktestTab() {
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState(false);
  const [message, setMessage] = useState("");

  const fetchBacktestHistory = async () => {
    try {
      const res = await api.get("/api/backtest/history");
      setHistory(res.data);
    } catch {
      setHistory([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchBacktestHistory();
    const interval = setInterval(fetchBacktestHistory, 5000);
    return () => clearInterval(interval);
  }, []);

  const runBacktest = async () => {
    setRunning(true);
    setMessage("Starting EMA Backtest...");
    try {
      const res = await api.post("/api/strategy/EMA/backtest");
      if (res.data.success) {
        setMessage("Backtest running in background. Please wait...");
      }
    } catch (err) {
      setMessage("Error starting backtest: " + (err.response?.data?.detail || err.message));
    } finally {
      setTimeout(() => {
        setRunning(false);
        setMessage("");
      }, 5000);
    }
  };

  const downloadReport = () => {
    const downloadUrl = `${api.defaults.baseURL || ""}/api/strategy/EMA/backtest/download`;
    window.open(downloadUrl, "_blank");
  };

  const totalPnl = history.reduce((sum, t) => sum + (t.pnl || 0), 0);
  const wins = history.filter((t) => (t.pnl || 0) > 0).length;
  const winRate = history.length > 0 ? (wins / history.length) * 100 : 0;

  return (
    <div>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "16px", flexWrap: "wrap", gap: "12px" }}>
        <div className="section-title">📊 EMA Backtest Control</div>
        <div style={{ display: "flex", gap: "12px" }}>
          <button 
            className="action-btn" 
            onClick={runBacktest} 
            disabled={running}
            style={{ background: "#ff9800", color: "white", border: "none" }}
          >
            {running ? "🏃 Running..." : "🚀 Run EMA Backtest"}
          </button>
          <button 
            className="action-btn" 
            onClick={downloadReport}
            style={{ background: "#2ea043", color: "white", border: "none" }}
          >
            📥 Download Excel Report
          </button>
        </div>
      </div>

      {message && (
        <div style={{ 
          padding: "10px", 
          marginBottom: "16px", 
          background: "#1f6feb22", 
          color: "#58a6ff", 
          borderRadius: "8px", 
          fontSize: "14px",
          border: "1px solid #1f6feb"
        }}>
          {message}
        </div>
      )}

      <div style={{ display: "flex", gap: "12px", marginBottom: "20px" }}>
        <div className="metric-box">
          <div style={{ fontSize: "12px", color: "#8b949e" }}>BACKTEST TRADES</div>
          <div style={{ fontWeight: 700, fontSize: "24px" }}>{history.length}</div>
        </div>
        <div className="metric-box">
          <div style={{ fontSize: "12px", color: "#8b949e" }}>TOTAL BACKTEST PNL</div>
          <div style={{ fontWeight: 700, fontSize: "24px", color: totalPnl >= 0 ? "#2ea043" : "#da3633" }}>
            ₹ {totalPnl.toFixed(2)}
          </div>
        </div>
        <div className="metric-box">
          <div style={{ fontSize: "12px", color: "#8b949e" }}>WIN RATE</div>
          <div style={{ fontWeight: 700, fontSize: "24px" }}>{winRate.toFixed(1)}%</div>
        </div>
      </div>

      <div className="table-wrapper">
        <table>
          <thead>
            <tr>
              <th>Symbol</th>
              <th>Buy Time</th>
              <th>Trigger</th>
              <th>Entry Price</th>
              <th>Sell Time</th>
              <th>Exit Price</th>
              <th>PnL</th>
              <th>Slippage</th>
              <th>Reason</th>
            </tr>
          </thead>
          <tbody>
            {history.map((trade, i) => (
              <tr key={i}>
                <td style={{ fontWeight: 600 }}>{trade.symbol}</td>
                <td style={{ color: "#8b949e", fontSize: "12px" }}>{trade.buytime || "—"}</td>
                <td style={{ color: "#8b949e" }}>{trade.trigger_buy_price || "—"}</td>
                <td style={{ color: "#58a6ff" }}>₹ {Number(trade.buyprice).toFixed(2)}</td>
                <td style={{ color: "#8b949e", fontSize: "12px" }}>{trade.selltime || "—"}</td>
                <td style={{ color: "#58a6ff" }}>₹ {Number(trade.sellprice).toFixed(2)}</td>
                <td style={{ fontWeight: 700, color: (trade.pnl || 0) >= 0 ? "#2ea043" : "#da3633" }}>
                  ₹ {Number(trade.pnl).toFixed(2)}
                </td>
                <td style={{ color: "#ff7b72" }}>{trade.slippage != null ? `₹ ${trade.slippage.toFixed(2)}` : "—"}</td>
                <td style={{ color: "#8b949e", fontSize: "12px" }}>{trade.reason || "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
