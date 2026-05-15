import StrategyPositionsTab from "../strategyTabs/StrategyPositionsTab";

export default function EmaPositionsTab() {
  return <StrategyPositionsTab strategy="EMA" endpointPrefix="/api/ema" />;
}
