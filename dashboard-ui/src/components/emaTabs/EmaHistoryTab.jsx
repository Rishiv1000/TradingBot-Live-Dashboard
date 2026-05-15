import StrategyHistoryTab from "../strategyTabs/StrategyHistoryTab";

export default function EmaHistoryTab() {
  return <StrategyHistoryTab strategy="EMA" endpointPrefix="/api/ema" />;
}
