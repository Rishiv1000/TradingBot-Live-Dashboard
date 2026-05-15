import { useEffect, useState } from "react";
import api from "../../api";

export default function StrategyHistoryTab({ strategy, endpointPrefix }) {
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchHistory = async () => {
      try {
        const res = await api.get(`${endpointPrefix}/history`);
        setHistory(res.data);
      } catch {
        setHistory([]);
      } finally {
        setLoading(false);
      }
    };
    fetchHistory();
    const id = setInterval(fetchHistory, 5000);
    return () => clearInterval(id);
  }, [endpointPrefix]);

  const totalPnl = history.reduce((sum, row) => sum + (Number(row.pnl) || 0), 0);

  return (
    <div>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "16px", flexWrap: "wrap", gap: "12px" }}>
        <div className="section-title">{strategy} Trade History</div>
        <div className="metric-box" style={{ minWidth: "auto", padding: "8px 16px" }}>PnL: <strong>{totalPnl.toFixed(2)}</strong></div>
      </div>
      {loading ? <div style={{ color: "#8b949e" }}>Loading...</div> : history.length === 0 ? <div style={{ color: "#8b949e" }}>No trade history yet.</div> : (
        <div className="table-wrapper">
          <table>
            <thead><tr><th>Symbol</th><th>Buy Time</th><th>Buy Price</th><th>Sell Time</th><th>Sell Price</th><th>PnL</th><th>Reason</th><th>Mode</th></tr></thead>
            <tbody>
              {history.map((t, i) => (
                <tr key={i}>
                  <td style={{ fontWeight: 600 }}>{t.symbol}</td>
                  <td style={{ color: "#8b949e" }}>{t.buytime || "-"}</td>
                  <td>{t.buyprice != null ? Number(t.buyprice).toFixed(2) : "-"}</td>
                  <td style={{ color: "#8b949e" }}>{t.selltime || "-"}</td>
                  <td>{t.sellprice != null ? Number(t.sellprice).toFixed(2) : "-"}</td>
                  <td style={{ fontWeight: 700, color: (Number(t.pnl) || 0) >= 0 ? "#2ea043" : "#da3633" }}>{t.pnl != null ? Number(t.pnl).toFixed(2) : "-"}</td>
                  <td style={{ color: "#8b949e" }}>{t.reason || "-"}</td>
                  <td>{t.mode || "PAPER"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
