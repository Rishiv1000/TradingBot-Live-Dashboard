import { useState } from "react";
import api from "../../api";

export default function StrategySymbolsTab({ strategy, color, endpointPrefix, symbols, onRefreshSymbols, showTargetPrice }) {
  const [symbolInput, setSymbolInput] = useState("");
  const [exchangeInput, setExchangeInput] = useState("NSE");
  const [targetPriceInput, setTargetPriceInput] = useState(0);
  const [deleteTarget, setDeleteTarget] = useState("");
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);

  const refresh = () => onRefreshSymbols(strategy);

  const reloadCache = async () => {
    await api.post(`${endpointPrefix}/symbols/reload-cache`).catch(() => {});
  };

  const handleAdd = async () => {
    if (!symbolInput.trim()) {
      setMessage("Enter a symbol first.");
      return;
    }
    setLoading(true);
    setMessage("");
    try {
      const payload = {
        symbol: symbolInput.trim().toUpperCase(),
        exchange: exchangeInput.trim().toUpperCase(),
      };
      if (showTargetPrice) {
        payload.target_price = parseFloat(targetPriceInput) || 0;
      }
      const res = await api.post(`${endpointPrefix}/symbols`, payload);
      if (res.data.success) {
        setMessage(`Added ${payload.symbol}`);
        setSymbolInput("");
        setTargetPriceInput(0);
        refresh();
        await reloadCache();
      } else {
        setMessage(res.data.error || "Add failed.");
      }
    } catch (e) {
      setMessage(e.response?.data?.detail || e.message);
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async () => {
    if (!deleteTarget) return;
    setLoading(true);
    setMessage("");
    try {
      await api.delete(`${endpointPrefix}/symbols/${deleteTarget}`);
      setDeleteTarget("");
      refresh();
      await reloadCache();
      setMessage(`Deleted ${deleteTarget}`);
    } catch (e) {
      setMessage(e.response?.data?.detail || e.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="strategy-section">
      <div className="strategy-section-header" style={{ color }}>{strategy} Symbols</div>

      <div className="table-wrapper" style={{ marginBottom: "14px" }}>
        <table>
          <thead>
            <tr>
              <th>Executed</th>
              <th>Symbol</th>
              <th>Exchange</th>
              {showTargetPrice && <th>Target Price</th>}
              <th>Token</th>
            </tr>
          </thead>
          <tbody>
            {!symbols || symbols.length === 0 ? (
              <tr>
                <td colSpan={showTargetPrice ? 5 : 4} style={{ color: "#8b949e", textAlign: "center", padding: "20px" }}>
                  No symbols yet.
                </td>
              </tr>
            ) : symbols.map((row) => (
              <tr key={row.symbol}>
                <td>
                  <span className="pill" style={row.isExecuted ? { background: "#2ea04322", color: "#2ea043", border: "1px solid #2ea043" } : { background: "#30363d", color: "#8b949e", border: "1px solid #30363d" }}>
                    {row.isExecuted ? "Yes" : "No"}
                  </span>
                </td>
                <td style={{ fontWeight: 600 }}>{row.symbol}</td>
                <td>{row.exchange}</td>
                {showTargetPrice && <td style={{ fontWeight: 700 }}>{row.target_price || 0}</td>}
                <td style={{ color: "#8b949e" }}>{row.instrument_token}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div style={{ display: "flex", gap: "8px", alignItems: "flex-end", flexWrap: "wrap", marginBottom: "10px" }}>
        <div>
          <div style={{ fontSize: "11px", color: "#8b949e", marginBottom: "4px" }}>Symbol</div>
          <input type="text" placeholder="RELIANCE" value={symbolInput} onChange={(e) => setSymbolInput(e.target.value)} onKeyDown={(e) => e.key === "Enter" && handleAdd()} style={{ width: "160px" }} />
        </div>
        <div>
          <div style={{ fontSize: "11px", color: "#8b949e", marginBottom: "4px" }}>Exchange</div>
          <input type="text" value={exchangeInput} onChange={(e) => setExchangeInput(e.target.value)} style={{ width: "90px" }} />
        </div>
        {showTargetPrice && (
          <div>
            <div style={{ fontSize: "11px", color: "#8b949e", marginBottom: "4px" }}>Target Price</div>
            <input type="number" value={targetPriceInput} onChange={(e) => setTargetPriceInput(e.target.value)} style={{ width: "120px" }} />
          </div>
        )}
        <button className="btn-primary" onClick={handleAdd} disabled={loading}>{loading ? "Working..." : "Add"}</button>
      </div>

      <div style={{ display: "flex", gap: "8px", alignItems: "flex-end", flexWrap: "wrap" }}>
        <div>
          <div style={{ fontSize: "11px", color: "#8b949e", marginBottom: "4px" }}>Delete Symbol</div>
          <select value={deleteTarget} onChange={(e) => setDeleteTarget(e.target.value)} style={{ width: "200px" }}>
            <option value="">select symbol</option>
            {(symbols || []).map((s) => <option key={s.symbol} value={s.symbol}>{s.symbol}</option>)}
          </select>
        </div>
        <button className="btn-danger" onClick={handleDelete} disabled={!deleteTarget || loading}>Delete</button>
        <button className="btn-secondary" onClick={reloadCache} disabled={loading}>Reload Cache</button>
      </div>

      {message && <div style={{ fontSize: "12px", marginTop: "10px", color: message.includes("failed") || message.includes("Error") ? "#da3633" : "#2ea043" }}>{message}</div>}
    </div>
  );
}
