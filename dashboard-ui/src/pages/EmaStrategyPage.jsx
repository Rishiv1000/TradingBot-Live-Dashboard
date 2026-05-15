import { useState } from "react";
import EmaLiveDFTab from "../components/emaTabs/EmaLiveDFTab";
import EmaSymbolsTab from "../components/emaTabs/EmaSymbolsTab";
import EmaBacktestTab from "../components/emaTabs/EmaBacktestTab";
import EmaPositionsTab from "../components/emaTabs/EmaPositionsTab";
import EmaHistoryTab from "../components/emaTabs/EmaHistoryTab";
import EmaTerminalTab from "../components/emaTabs/EmaTerminalTab";

const TABS = [
  { id: "livedf", label: "Live DF" },
  { id: "symbols", label: "Symbols" },
  { id: "backtest", label: "Backtest" },
  { id: "positions", label: "Positions" },
  { id: "history", label: "History" },
  { id: "terminal", label: "Terminal" },
];

export default function EmaStrategyPage({ status, symbols, onRefreshSymbols }) {
  const [activeTab, setActiveTab] = useState("livedf");
  const color = status?.EMA?.color || "#ff9800";

  return (
    <div>
      <div className="tab-bar">
        {TABS.map((tab) => <button key={tab.id} className={`tab-btn${activeTab === tab.id ? " active" : ""}`} onClick={() => setActiveTab(tab.id)}>{tab.label}</button>)}
      </div>
      <div style={{ display: activeTab === "livedf" ? "block" : "none" }}><EmaLiveDFTab color={color} symbols={symbols} /></div>
      <div style={{ display: activeTab === "symbols" ? "block" : "none" }}><EmaSymbolsTab color={color} symbols={symbols} onRefreshSymbols={onRefreshSymbols} /></div>
      <div style={{ display: activeTab === "backtest" ? "block" : "none" }}><EmaBacktestTab /></div>
      <div style={{ display: activeTab === "positions" ? "block" : "none" }}><EmaPositionsTab /></div>
      <div style={{ display: activeTab === "history" ? "block" : "none" }}><EmaHistoryTab /></div>
      <div style={{ display: activeTab === "terminal" ? "block" : "none" }}><EmaTerminalTab color={color} /></div>
    </div>
  );
}
