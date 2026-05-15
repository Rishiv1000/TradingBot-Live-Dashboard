import StrategyBacktestTab from "../strategyTabs/StrategyBacktestTab";

export default function EmaBacktestTab() {
  return <StrategyBacktestTab strategy="EMA" endpointPrefix="/api/ema" />;
}
