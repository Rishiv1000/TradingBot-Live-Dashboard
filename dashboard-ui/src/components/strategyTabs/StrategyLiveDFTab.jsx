import { useCallback, useEffect, useState } from "react";
import api from "../../api";

export default function StrategyLiveDFTab({ strategy, color, endpointPrefix, symbols }) {
  const symbolNames = (symbols || []).map((s) => s.symbol);
  const [selectedSymbol, setSelectedSymbol] = useState(symbolNames[0] || "");
  const [dfData, setDfData] = useState(null);
  const [rowsToShow, setRowsToShow] = useState(20);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (symbolNames.length > 0 && !symbolNames.includes(selectedSymbol)) {
      setSelectedSymbol(symbolNames[0]);
    }
  }, [symbolNames.join(","), selectedSymbol]);

  const fetchDF = useCallback(async () => {
    if (!selectedSymbol) return;
    setLoading(true);
    try {
      const res = await api.get(`${endpointPrefix}/df/${selectedSymbol}`);
      setDfData(res.data);
    } catch {
      setDfData(null);
    } finally {
      setLoading(false);
    }
  }, [endpointPrefix, selectedSymbol]);

  useEffect(() => {
    fetchDF();
  }, [fetchDF]);

  return (
    <div className="strategy-section">
      <div className="strategy-section-header" style={{ color }}>{strategy} Live DataFrame</div>

      {symbolNames.length === 0 ? (
        <div style={{ color: "#8b949e" }}>No symbols configured.</div>
      ) : (
        <>
          <div style={{ display: "flex", gap: "12px", alignItems: "flex-end", flexWrap: "wrap", marginBottom: "14px" }}>
            <div>
              <div style={{ fontSize: "11px", color: "#8b949e", marginBottom: "4px" }}>Symbol</div>
              <select value={selectedSymbol} onChange={(e) => setSelectedSymbol(e.target.value)} style={{ width: "200px" }}>
                {symbolNames.map((s) => <option key={s} value={s}>{s}</option>)}
              </select>
            </div>
            <div>
              <div style={{ fontSize: "11px", color: "#8b949e", marginBottom: "4px" }}>Rows: <strong style={{ color: "var(--text-color)" }}>{rowsToShow}</strong></div>
              <input type="range" min={5} max={500} step={5} value={rowsToShow} onChange={(e) => setRowsToShow(Number(e.target.value))} style={{ width: "200px" }} />
            </div>
            <button className="btn-secondary" onClick={fetchDF} disabled={loading}>{loading ? "Loading..." : "Refresh DF"}</button>
          </div>

          {loading ? <div style={{ color: "#8b949e" }}>Loading...</div> : dfData ? (
            <>
              <div style={{ display: "flex", gap: "12px", marginBottom: "16px", flexWrap: "wrap" }}>
                <div className="metric-box"><div className="metric-label">Candles</div><div className="metric-value">{dfData.candle_count || 0}</div></div>
                <div className="metric-box"><div className="metric-label">Last Candle</div><div className="metric-value" style={{ fontSize: "14px" }}>{dfData.last_candle || "-"}</div></div>
                <div className="metric-box"><div className="metric-label">Showing</div><div className="metric-value">{Math.min(rowsToShow, dfData.data?.length || 0)}</div></div>
              </div>
              {dfData.data?.length > 0 ? (
                <div className="table-wrapper">
                  <table>
                    <thead><tr>{dfData.columns.map((c) => <th key={c}>{c}</th>)}</tr></thead>
                    <tbody>
                      {dfData.data.slice(-rowsToShow).map((row, i) => (
                        <tr key={i}>{dfData.columns.map((c) => <td key={c} style={{ whiteSpace: "nowrap" }}>{row[c] != null ? String(row[c]) : "-"}</td>)}</tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : <div style={{ color: "#8b949e" }}>No cache data yet.</div>}
            </>
          ) : <div style={{ color: "#8b949e" }}>No cache data available.</div>}
        </>
      )}
    </div>
  );
}
