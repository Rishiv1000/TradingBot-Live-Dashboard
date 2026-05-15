import { useCallback, useEffect, useRef, useState } from "react";
import { CandlestickSeries, LineSeries, createChart } from "lightweight-charts";
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
  const ema9SeriesRef = useRef(null);
  const ema20SeriesRef = useRef(null);
  const [showChart, setShowChart] = useState(true);
  const [countdown, setCountdown] = useState(0);
  const [lastFetchedAt, setLastFetchedAt] = useState(null);

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
      setLastFetchedAt(new Date().toLocaleTimeString());
      if (res.data.next_candle_sec) setCountdown(res.data.next_candle_sec);
    } catch {
      setDfData(null);
    } finally {
      setLoading(false);
    }
  }, [endpointPrefix, selectedSymbol]);

  useEffect(() => {
    fetchDF();
  }, [fetchDF]);

  // Countdown: ticks down every second — display only, no auto-reload
  useEffect(() => {
    if (countdown <= 0) return;
    const t = setInterval(() => setCountdown(prev => Math.max(0, prev - 1)), 1000);
    return () => clearInterval(t);
  }, [countdown]);

  useEffect(() => {
    if (!chartContainerRef.current || !showChart) return;
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

    // Optional EMA lines
    ema9SeriesRef.current = chart.addSeries(LineSeries, {
      color: "#ffeb3b",
      lineWidth: 1.5,
      priceLineVisible: false,
      lastValueVisible: false,
      title: "EMA 9",
    });
    ema20SeriesRef.current = chart.addSeries(LineSeries, {
      color: "#2196f3",
      lineWidth: 1.5,
      priceLineVisible: false,
      lastValueVisible: false,
      title: "EMA 20",
    });

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
      ema9SeriesRef.current = null;
      ema20SeriesRef.current = null;
    };
  }, [color, showChart]);

  useEffect(() => {
    if (!candlestickSeriesRef.current || !chartRef.current) return;
    const candles = buildCandles(dfData?.data);
    if (candles.length > 0) {
      candlestickSeriesRef.current.setData(candles);
      
      // Update EMA 9 (support both lowercase and uppercase)
      const ema9Col = dfData?.columns?.find(c => c.toLowerCase() === "ema9" || c === "EMA_9");
      if (ema9Col) {
        const ema9Data = (dfData.data || [])
          .map(row => ({ time: toChartTime(row.date || row.time || row.datetime), value: Number(row[ema9Col]) }))
          .filter(d => d.time && !Number.isNaN(d.value))
          .sort((a, b) => a.time - b.time);
        ema9SeriesRef.current.setData(ema9Data);
      } else {
        ema9SeriesRef.current.setData([]);
      }

      // Update EMA 20 (support both lowercase and uppercase)
      const ema20Col = dfData?.columns?.find(c => c.toLowerCase() === "ema20" || c === "EMA_20");
      if (ema20Col) {
        const ema20Data = (dfData.data || [])
          .map(row => ({ time: toChartTime(row.date || row.time || row.datetime), value: Number(row[ema20Col]) }))
          .filter(d => d.time && !Number.isNaN(d.value))
          .sort((a, b) => a.time - b.time);
        ema20SeriesRef.current.setData(ema20Data);
      } else {
        ema20SeriesRef.current.setData([]);
      }

      chartRef.current.timeScale().fitContent();
    }
  }, [dfData]);

  return (
    <div className="strategy-section">
      <div className="strategy-section-header" style={{ color, display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <span>{strategy} Live DataFrame</span>
        <div style={{ display: "flex", gap: "10px", alignItems: "center" }}>
          <button 
            className="btn-sm btn-secondary" 
            onClick={() => setShowChart(!showChart)}
            style={{ fontSize: "11px", padding: "4px 10px" }}
          >
            {showChart ? "Hide Chart" : "Show Chart"}
          </button>
        </div>
      </div>

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

          {showChart && (
            <div 
              ref={chartContainerRef} 
              style={{ 
                width: "100%", 
                height: "300px", 
                marginBottom: "20px", 
                background: "#0d1117", 
                borderRadius: "8px", 
                border: "1px solid #30363d", 
                overflow: "hidden" 
              }} 
            />
          )}

          {loading ? <div style={{ color: "#8b949e" }}>Loading...</div> : dfData ? (
            <>
              <div style={{ display: "flex", gap: "12px", marginBottom: "16px", flexWrap: "wrap" }}>
                <div className="metric-box"><div className="metric-label">Candles</div><div className="metric-value">{dfData.candle_count || 0}</div></div>
                <div className="metric-box"><div className="metric-label">Last Candle</div><div className="metric-value" style={{ fontSize: "14px" }}>{dfData.last_candle || "-"}</div></div>
                <div className="metric-box">
                  <div className="metric-label">Next Candle</div>
                  <div className="metric-value" style={{ color: countdown <= 10 ? "#ff7b72" : countdown <= 30 ? "#e3b341" : "#a5d6ff" }}>
                    {countdown > 0 ? `${countdown}s` : "🕐 Now"}
                  </div>
                </div>
                <div className="metric-box"><div className="metric-label">Last Loaded</div><div className="metric-value" style={{ fontSize: "13px" }}>{lastFetchedAt || "-"}</div></div>
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
