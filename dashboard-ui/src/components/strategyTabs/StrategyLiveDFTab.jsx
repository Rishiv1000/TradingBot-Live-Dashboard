import { useCallback, useEffect, useState, useRef } from "react";
import { createChart } from "lightweight-charts";
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

  const chartContainerRef = useRef(null);
  const chartRef = useRef(null);
  const candlestickSeriesRef = useRef(null);

  useEffect(() => {
    if (!chartContainerRef.current) return;

    const chart = createChart(chartContainerRef.current, {
      layout: {
        background: { color: "transparent" },
        textColor: "#d1d4dc",
      },
      grid: {
        vertLines: { color: "#334155" },
        horzLines: { color: "#334155" },
      },
      width: chartContainerRef.current.clientWidth,
      height: 300,
      timeScale: {
        timeVisible: true,
        secondsVisible: false,
      },
    });

    const candlestickSeries = chart.addCandlestickSeries({
      upColor: "#26a69a",
      downColor: "#ef5350",
      borderVisible: false,
      wickUpColor: "#26a69a",
      wickDownColor: "#ef5350",
    });

    chartRef.current = chart;
    candlestickSeriesRef.current = candlestickSeries;

    const handleResize = () => {
      chart.applyOptions({ width: chartContainerRef.current.clientWidth });
    };

    window.addEventListener("resize", handleResize);

    return () => {
      window.removeEventListener("resize", handleResize);
      chart.remove();
    };
  }, []);

  useEffect(() => {
    if (!candlestickSeriesRef.current || !dfData?.data) return;

    try {
      // Lightweight charts expects time to be a string or number (unix timestamp)
      // date column might be "2023-05-15 09:15:00"
      const formattedData = dfData.data.map((d) => {
        // Ensure we have required fields
        const timeVal = d.date || d.time || d.datetime;
        if (!timeVal) return null;

        // Try to parse time if it's a string like "2023-05-15 09:15:00"
        let time;
        if (typeof timeVal === 'string') {
          // If it has a space, lightweight charts might not like it directly for all scales
          // but usually string dates work. Let's try to convert to unix if possible.
          time = Math.floor(new Date(timeVal).getTime() / 1000);
        } else {
          time = timeVal;
        }

        if (isNaN(time)) return null;

        return {
          time: time,
          open: parseFloat(d.open),
          high: parseFloat(d.high),
          low: parseFloat(d.low),
          close: parseFloat(d.close),
        };
      }).filter(d => d !== null);

      // Sort by time just in case
      formattedData.sort((a, b) => a.time - b.time);

      // Remove duplicates by time (Lightweight charts throws error on duplicate time)
      const uniqueData = [];
      const seenTimes = new Set();
      for (const d of formattedData) {
        if (!seenTimes.has(d.time)) {
          uniqueData.push(d);
          seenTimes.add(d.time);
        }
      }

      if (uniqueData.length > 0) {
        candlestickSeriesRef.current.setData(uniqueData);
        chartRef.current.timeScale().fitContent();
      }
    } catch (e) {
      console.error("Chart data error:", e);
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
