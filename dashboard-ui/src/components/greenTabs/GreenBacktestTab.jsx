import StrategyBacktestTab from "../strategyTabs/StrategyBacktestTab";

export default function GreenBacktestTab() {
  return <StrategyBacktestTab strategy="GREEN" endpointPrefix="/api/green" />;
}
