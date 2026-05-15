import { useState } from "react";
import GreenLiveDFTab from "../components/greenTabs/GreenLiveDFTab";
import GreenSymbolsTab from "../components/greenTabs/GreenSymbolsTab";
import GreenBacktestTab from "../components/greenTabs/GreenBacktestTab";
import GreenPositionsTab from "../components/greenTabs/GreenPositionsTab";
import GreenHistoryTab from "../components/greenTabs/GreenHistoryTab";
import GreenTerminalTab from "../components/greenTabs/GreenTerminalTab";

const TABS = [
  { id: "livedf", label: "Live DF" },
  { id: "symbols", label: "Symbols" },
  { id: "backtest", label: "Backtest" },
  { id: "positions", label: "Positions" },
  { id: "history", label: "History" },
  { id: "terminal", label: "Terminal" },
];

export default function GreenStrategyPage({ status, symbols, onRefreshSymbols }) {
  const [activeTab, setActiveTab] = useState("livedf");
  const color = status?.GREEN?.color || "#2ea043";

  return (
    <div>
      <div className="tab-bar">
        {TABS.map((tab) => <button key={tab.id} className={`tab-btn${activeTab === tab.id ? " active" : ""}`} onClick={() => setActiveTab(tab.id)}>{tab.label}</button>)}
      </div>
      <div style={{ display: activeTab === "livedf" ? "block" : "none" }}><GreenLiveDFTab color={color} symbols={symbols} /></div>
      <div style={{ display: activeTab === "symbols" ? "block" : "none" }}><GreenSymbolsTab color={color} symbols={symbols} onRefreshSymbols={onRefreshSymbols} /></div>
      <div style={{ display: activeTab === "backtest" ? "block" : "none" }}><GreenBacktestTab /></div>
      <div style={{ display: activeTab === "positions" ? "block" : "none" }}><GreenPositionsTab /></div>
      <div style={{ display: activeTab === "history" ? "block" : "none" }}><GreenHistoryTab /></div>
      <div style={{ display: activeTab === "terminal" ? "block" : "none" }}><GreenTerminalTab color={color} /></div>
    </div>
  );
}
