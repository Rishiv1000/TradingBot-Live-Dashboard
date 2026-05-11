import { useState, useEffect, useCallback, useRef } from "react";
import { createChart, CandlestickSeries } from "lightweight-charts";
import api from "../../api";

// ── Countdown to next 1-minute candle boundary ────────────────────────────────
function useNextCandleCountdown() {
  const [countdown, setCountdown] = useState(0);
  useEffect(() => {
    const tick = () => setCountdown(60 - new Date().getSeconds());
    tick();
    const id = setInterval(tick, 1000);
    return () => clearInterval(id);
  }, []);
  return countdown;
}

// ── Candlestick chart using lightweight-charts ────────────────────────────────
function CandleChart({ data, columns, color }) {
  const containerRef = useRef(null);
  const chartRef     = useRef(null);
  const seriesRef    = useRef(null);

  // Build chart once on mount
  useEffect(() => {
    if (!containerRef.current) return;

    const chart = createChart(containerRef.current, {
      width:  containerRef.current.clientWidth,
      height: 320,
      layout: {
        background: { color: "#0d1117" },
        textColor:  "#8b949e",
      },
      grid: {
        vertLines: { color: "#21262d" },
        horzLines: { color: "#21262d" },
      },
      crosshair: { mode: 1 },
      rightPriceScale: { borderColor: "#30363d" },
      timeScale: {
        borderColor:     "#30363d",
        timeVisible:     true,
        secondsVisible:  false,
      },
    });

    const series = chart.addSeries(CandlestickSeries, {
      upColor:        color || "#2ea043",
      downColor:      "#da3633",
      borderUpColor:  color || "#2ea043",
      borderDownColor:"#da3633",
      wickUpColor:    color || "#2ea043",
      wickDownColor:  "#da3633",
    });

    chartRef.current  = chart;
    seriesRef.current = series;

    // Resize chart when window resizes
    const onResize = () => {
      if (containerRef.current) {
        chart.applyOptions({ width: containerRef.current.clientWidth });
      }
    };
    window.addEventListener("resize", onResize);
    return () => {
      window.removeEventListener("resize", onResize);
      chart.remove();
    };
  }, [color]);

  // Update data whenever df rows change
  useEffect(() => {
    if (!seriesRef.current || !data || data.length === 0) return;

    // Map df columns to lightweight-charts format
    // Expects: date, open, high, low, close columns
    const dateCol  = columns.find((c) => c === "date");
    const openCol  = columns.find((c) => c === "open");
    const highCol  = columns.find((c) => c === "high");
    const lowCol   = columns.find((c) => c === "low");
    const closeCol = columns.find((c) => c === "close");

    if (!dateCol || !openCol || !highCol || !lowCol || !closeCol) return;

    const candles = data
      .map((row) => {
        // Convert "2024-01-15 09:15:00" → Unix timestamp (seconds)
        const ts = Math.floor(new Date(row[dateCol]).getTime() / 1000);
        return {
          time:  ts,
          open:  parseFloat(row[openCol]),
          high:  parseFloat(row[highCol]),
          low:   parseFloat(row[lowCol]),
          close: parseFloat(row[closeCol]),
        };
      })
      .filter((c) => !isNaN(c.time) && !isNaN(c.open))
      // lightweight-charts requires ascending time, no duplicates
      .sort((a, b) => a.time - b.time)
      .filter((c, i, arr) => i === 0 || c.time !== arr[i - 1].time);

    if (candles.length === 0) return;

    seriesRef.current.setData(candles);
    chartRef.current.timeScale().fitContent();
  }, [data, columns]);

  return (
    <div
      ref={containerRef}
      style={{
        width:        "100%",
        height:       "320px",
        borderRadius: "8px",
        overflow:     "hidden",
        border:       "1px solid #21262d",
        marginBottom: "16px",
      }}
    />
  );
}

// ── Per-strategy section ──────────────────────────────────────────────────────
function StrategyLiveDF({ strategy, color, symbols }) {
  const symNames = (symbols || []).map((s) => s.symbol);
  const [selectedSymbol, setSelectedSymbol] = useState(symNames[0] || "");
  const [dfData,    setDfData]    = useState(null);
  const [loading,   setLoading]   = useState(false);
  const [rowsToShow, setRowsToShow] = useState(20);
  const [showChart,  setShowChart]  = useState(true);
  const countdown = useNextCandleCountdown();

  // Keep selected symbol valid when symbol list changes
  useEffect(() => {
    if (symNames.length > 0 && !symNames.includes(selectedSymbol)) {
      setSelectedSymbol(symNames[0]);
    }
  }, [symNames.join(",")]);

  const fetchDF = useCallback(() => {
    if (!selectedSymbol) return;
    setLoading(true);
    api.get(`/api/df/${strategy}/${selectedSymbol}`)
      .then((res) => setDfData(res.data))
      .catch(() => setDfData(null))
      .finally(() => setLoading(false));
  }, [strategy, selectedSymbol]);

  // Fetch on symbol change
  useEffect(() => { fetchDF(); }, [fetchDF]);

  // Auto-refresh when countdown hits 1 (candle just closed)
  useEffect(() => {
    if (countdown === 1) fetchDF();
  }, [countdown]);

  return (
    <div className="strategy-section">
      <div className="strategy-section-header" style={{ color }}>
        ● {strategy} — Live DataFrame Cache
      </div>

      {symNames.length === 0 ? (
        <div style={{ color: "#8b949e", padding: "12px 0" }}>No symbols configured.</div>
      ) : (
        <>
          {/* Controls row */}
          <div style={{ display: "flex", gap: "16px", alignItems: "flex-end", flexWrap: "wrap", marginBottom: "14px" }}>
            <div>
              <div style={{ fontSize: "11px", color: "#8b949e", marginBottom: "4px" }}>Symbol</div>
              <select
                value={selectedSymbol}
                onChange={(e) => setSelectedSymbol(e.target.value)}
                style={{ width: "200px" }}
              >
                {symNames.map((s) => <option key={s} value={s}>{s}</option>)}
              </select>
            </div>
            <div>
              <div style={{ fontSize: "11px", color: "#8b949e", marginBottom: "4px" }}>
                Rows: <strong style={{ color: "#f0f6fc" }}>{rowsToShow}</strong>
              </div>
              <input
                type="range" min={5} max={500} step={5}
                value={rowsToShow}
                onChange={(e) => setRowsToShow(Number(e.target.value))}
                style={{ width: "160px", padding: 0, border: "none", background: "transparent", cursor: "pointer" }}
              />
            </div>
            <button
              className="btn-secondary btn-sm"
              onClick={fetchDF}
              disabled={loading}
              style={{ alignSelf: "flex-end" }}
            >
              {loading ? "⏳" : "🔄 Reload DF"}
            </button>
            <button
              className="btn-secondary btn-sm"
              onClick={() => setShowChart((v) => !v)}
              style={{ alignSelf: "flex-end" }}
            >
              {showChart ? "📉 Hide Chart" : "📈 Show Chart"}
            </button>
          </div>

          {loading ? (
            <div style={{ color: "#8b949e" }}>Loading...</div>
          ) : dfData ? (
            <>
              {/* Metrics row */}
              <div style={{ display: "flex", gap: "12px", marginBottom: "16px", flexWrap: "wrap" }}>
                <div className="metric-box">
                  <div className="metric-label">Total Candles</div>
                  <div className="metric-value">{dfData.candle_count}</div>
                </div>
                <div className="metric-box">
                  <div className="metric-label">Last Candle</div>
                  <div className="metric-value" style={{ fontSize: "14px", paddingTop: "4px" }}>
                    {dfData.last_candle || "—"}
                  </div>
                </div>
                <div className="metric-box">
                  <div className="metric-label">Showing</div>
                  <div className="metric-value">{Math.min(rowsToShow, dfData.data?.length || 0)}</div>
                </div>
                {/* Countdown — turns yellow in last 5 seconds */}
                <div className="metric-box" style={{ borderColor: countdown <= 5 ? "#e3b341" : "#30363d" }}>
                  <div className="metric-label" style={{ color: countdown <= 5 ? "#e3b341" : "#8b949e" }}>
                    Next Candle In
                  </div>
                  <div className="metric-value" style={{ color: countdown <= 5 ? "#e3b341" : "#f0f6fc", fontVariantNumeric: "tabular-nums" }}>
                    {countdown}s
                  </div>
                </div>
              </div>

              {/* Candlestick chart */}
              {showChart && dfData.data && dfData.data.length > 0 && (
                <CandleChart
                  data={dfData.data}
                  columns={dfData.columns}
                  color={color}
                />
              )}

              {/* Data table */}
              {dfData.data && dfData.data.length > 0 ? (
                <div className="table-wrapper">
                  <table>
                    <thead>
                      <tr>{dfData.columns.map((col) => <th key={col}>{col}</th>)}</tr>
                    </thead>
                    <tbody>
                      {dfData.data.slice(-rowsToShow).map((row, i) => (
                        <tr key={i}>
                          {dfData.columns.map((col) => (
                            <td key={col} style={{ whiteSpace: "nowrap" }}>
                              {row[col] !== undefined && row[col] !== null ? String(row[col]) : "—"}
                            </td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <div style={{ color: "#8b949e" }}>No cache data yet. Start the strategy to populate data.</div>
              )}
            </>
          ) : (
            <div style={{ color: "#8b949e" }}>No cache data available.</div>
          )}
        </>
      )}
    </div>
  );
}

// ── Main export ───────────────────────────────────────────────────────────────
export default function LiveDFTab({ symbolsCache, status }) {
  const strategies = status ? Object.entries(status) : [];
  return (
    <div>
      {strategies.map(([strategy, info]) => (
        <StrategyLiveDF
          key={strategy}
          strategy={strategy}
          color={info.color}
          symbols={symbolsCache[strategy] || []}
        />
      ))}
    </div>
  );
}
