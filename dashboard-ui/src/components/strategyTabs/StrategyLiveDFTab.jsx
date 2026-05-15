import { useCallback, useEffect, useRef, useState } from "react";
import { CandlestickSeries, createChart } from "lightweight-charts";
import api from "../../api";

function toChartTime(value) {
  if (!value) return null;
  if (typeof value === "number") return value > 1000000000000 ? Math.floor(value / 1000) : value;
  const clean = String(value).replace("T", " ").split(".")[0].split("+")[0].split("Z")[0];
  const parsed = Date.parse(`${clean}Z`);
  return Number.isNaN(parsed) ? null : Math.floor(parsed / 1000);
}

function buildCandles(rows) {
  const seen = new Set();
  return (rows || [])
    .map((row) => {
      const time = toChartTime(row.date || row.time || row.datetime);
      const open = Number(row.open);
      const high = Number(row.high);
      const low = Number(row.low);
      const close = Number(row.close);
      if (!time || [open, high, low, close].some(Number.isNaN)) return null;
      return { time, open, high, low, close };
    })
    .filter(Boolean)
    .sort((a, b) => a.time - b.time)
    .filter((row) => {
      if (seen.has(row.time)) return false;
      seen.add(row.time);
      return true;
    });
}

export default function StrategyLiveDFTab({ strategy, color, endpointPrefix, symbols }) {
  const symbolNames = (symbols || []).map((s) => s.symbol);
  const [selectedSymbol, setSelectedSymbol] = useState(symbolNames[0] || "");
  const [dfData, setDfData] = useState(null);
  const [rowsToShow, setRowsToShow] = useState(20);
  const [loading, setLoading] = useState(false);
  const chartContainerRef = useRef(null);
  const chartRef = useRef(null);
  const candlestickSeriesRef = useRef(null);

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

  useEffect(() => {
    if (!chartContainerRef.current) return;
    const chart = createChart(chartContainerRef.current, {
      width: chartContainerRef.current.clientWidth,
      height: 300,
      layout: { background: { color: "#0d1117" }, textColor: "#d1d4dc" },
      grid: { vertLines: { color: "#21262d" }, horzLines: { color: "#21262d" } },
      rightPriceScale: { borderColor: "#30363d" },
      timeScale: { borderColor: "#30363d", timeVisible: true, secondsVisible: false },
    });
    const series = chart.addSeries(CandlestickSeries, {
      upColor: color || "#26a69a",
      downColor: "#ef5350",
      borderUpColor: color || "#26a69a",
      borderDownColor: "#ef5350",
      wickUpColor: color || "#26a69a",
      wickDownColor: "#ef5350",
    });
    chartRef.current = chart;
    candlestickSeriesRef.current = series;

    const handleResize = () => {
      if (chartContainerRef.current) {
        chart.applyOptions({ width: chartContainerRef.current.clientWidth });
      }
    };
    window.addEventListener("resize", handleResize);
    return () => {
      window.removeEventListener("resize", handleResize);
      chart.remove();
      chartRef.current = null;
      candlestickSeriesRef.current = null;
    };
  }, [color]);

  useEffect(() => {
    if (!candlestickSeriesRef.current || !chartRef.current) return;
    const candles = buildCandles(dfData?.data);
    if (candles.length > 0) {
      candlestickSeriesRef.current.setData(candles);
      chartRef.current.timeScale().fitContent();
    }
  }, [dfData]);

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

          <div ref={chartContainerRef} style={{ width: "100%", height: "300px", marginBottom: "20px", background: "#0d1117", borderRadius: "8px", border: "1px solid #30363d", overflow: "hidden" }} />

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
