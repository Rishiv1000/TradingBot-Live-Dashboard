import { useState } from "react";
import GeneralDatabaseTab from "../components/generalTabs/GeneralDatabaseTab";
import GeneralTerminalTab from "../components/generalTabs/GeneralTerminalTab";

const TABS = [
  { id: "database", label: "Infrastructure" },
  { id: "terminal", label: "Terminal Logs" },
];

export default function GeneralPage() {
  const [activeTab, setActiveTab] = useState("database");

  return (
    <div>
      <div className="tab-bar">
        {TABS.map((tab) => <button key={tab.id} className={`tab-btn${activeTab === tab.id ? " active" : ""}`} onClick={() => setActiveTab(tab.id)}>{tab.label}</button>)}
      </div>
      <div style={{ display: activeTab === "database" ? "block" : "none" }}><GeneralDatabaseTab /></div>
      <div style={{ display: activeTab === "terminal" ? "block" : "none" }}><GeneralTerminalTab /></div>
    </div>
  );
}
