import { useEffect, useState } from "react";
import api from "../../api";

export default function StrategyPositionsTab({ strategy, endpointPrefix }) {
  const [positions, setPositions] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchPositions = async () => {
      try {
        const res = await api.get(`${endpointPrefix}/positions`);
        setPositions(res.data);
      } catch {
        setPositions([]);
      } finally {
        setLoading(false);
      }
    };
    fetchPositions();
    const id = setInterval(fetchPositions, 5000);
    return () => clearInterval(id);
  }, [endpointPrefix]);

  return (
    <div>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "16px" }}>
        <div className="section-title">{strategy} Open Positions</div>
        <div className="metric-box" style={{ minWidth: "auto", padding: "8px 16px" }}>Total: <strong>{positions.length}</strong></div>
      </div>
      {loading ? <div style={{ color: "#8b949e" }}>Loading...</div> : positions.length === 0 ? <div style={{ color: "#8b949e" }}>No open positions.</div> : (
        <div className="table-wrapper">
          <table>
            <thead><tr><th>Symbol</th><th>Buy Price</th><th>Buy Time</th><th>Product</th><th>Mode</th></tr></thead>
            <tbody>
              {positions.map((p, i) => (
                <tr key={i}>
                  <td style={{ fontWeight: 600 }}>{p.symbol}</td>
                  <td>{p.buyprice != null ? Number(p.buyprice).toFixed(2) : "-"}</td>
                  <td style={{ color: "#8b949e" }}>{p.buytime || "-"}</td>
                  <td>{p.product || "-"}</td>
                  <td>{p.mode || "PAPER"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
