import { useState } from "react";
import api from "../../api";

export default function StrategyBacktestTab({ strategy, endpointPrefix }) {
  const [days, setDays] = useState(30);
  const [running, setRunning] = useState(false);
  const [result, setResult] = useState(null);

  const runBacktest = async () => {
    setRunning(true);
    setResult(null);
    try {
      const res = await api.post(`${endpointPrefix}/backtest`, { strategy, days });
      setResult(res.data);
    } catch (e) {
      setResult({ success: false, error: e.response?.data?.detail || e.message });
    } finally {
      setRunning(false);
    }
  };

  return (
    <div>
      <div className="section-title">{strategy} Backtest</div>
      <div style={{ display: "flex", gap: "16px", alignItems: "flex-end", flexWrap: "wrap", marginBottom: "16px" }}>
        <div>
          <div style={{ fontSize: "11px", color: "#8b949e", marginBottom: "4px" }}>Days: <strong style={{ color: "var(--text-color)" }}>{days}</strong></div>
          <input type="range" min={1} max={365} value={days} onChange={(e) => setDays(Number(e.target.value))} style={{ width: "220px" }} />
        </div>
        <button className="btn-purple" onClick={runBacktest} disabled={running}>{running ? "Running..." : "Run Backtest"}</button>
      </div>
      {result && (
        <div style={{ background: result.success ? "#2ea04322" : "#da363322", border: `1px solid ${result.success ? "#2ea043" : "#da3633"}`, borderRadius: "8px", padding: "12px 16px" }}>
          {result.success ? (
            <div style={{ display: "flex", gap: "24px", flexWrap: "wrap" }}>
              <strong style={{ color: "#2ea043" }}>Backtest complete</strong>
              <span>Trades: <strong>{result.trades}</strong></span>
              <span>PnL: <strong>{result.total_pnl}</strong></span>
              <span>Win Rate: <strong>{result.win_rate}%</strong></span>
            </div>
          ) : <span style={{ color: "#da3633" }}>{result.error || "Backtest failed."}</span>}
        </div>
      )}
    </div>
  );
}
