export default function StrategyCards({ status }) {
  if (!status) return null;

  // trading_enabled is same for all strategies (global flag)
  const tradingEnabled = Object.values(status).some(s => s.trading_enabled);

  return (
    <div>
      {/* Real Trading Status Badge */}
      <div style={{
        display: "inline-flex",
        alignItems: "center",
        gap: "8px",
        padding: "6px 14px",
        borderRadius: "20px",
        background: tradingEnabled ? "#2ea04322" : "#30363d",
        color: tradingEnabled ? "#2ea043" : "#8b949e",
        fontWeight: 700,
        fontSize: "13px",
        marginBottom: "16px",
        border: `1px solid ${tradingEnabled ? "#2ea043" : "#444"}`
      }}>
        <span style={{ width: "8px", height: "8px", borderRadius: "50%", background: tradingEnabled ? "#2ea043" : "#8b949e", boxShadow: tradingEnabled ? "0 0 8px #2ea043" : "none" }}></span>
        {tradingEnabled ? "LIVE TRADING ON" : "NOT LIVE"}
      </div>

      {/* Strategy cards */}
      <div style={{ display: "flex", gap: "16px", marginBottom: "24px", flexWrap: "wrap" }}>
        {Object.entries(status).map(([strategy, info]) => {
          const running = info.running;
          const statusColor = running ? "#2ea043" : "#da3633";
          const statusLabel = running ? "RUNNING" : "STOPPED";
          return (
            <div
              key={strategy}
              className="card"
              style={{
                flex: "1 1 200px",
                borderLeft: `4px solid ${info.color}`,
                minWidth: "180px",
              }}
            >
              <div style={{ fontSize: "18px", fontWeight: 900, color: info.color, marginBottom: "6px" }}>
                {strategy}
              </div>
              <span
                className="pill"
                style={{
                  background: statusColor + "22",
                  color: statusColor,
                  border: `1px solid ${statusColor}`,
                  marginBottom: "10px",
                  display: "inline-block",
                }}
              >
                {statusLabel}
              </span>
              <div style={{ display: "flex", gap: "16px", marginTop: "8px" }}>
                <div>
                  <div style={{ fontSize: "11px", color: "var(--muted-text)", fontWeight: 600 }}>SYMBOLS</div>
                  <div style={{ fontSize: "20px", fontWeight: 700 }}>{info.symbol_count}</div>
                </div>
                <div>
                  <div style={{ fontSize: "11px", color: "var(--muted-text)", fontWeight: 600 }}>OPEN</div>
                  <div style={{ fontSize: "20px", fontWeight: 700 }}>{info.open_count}</div>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
