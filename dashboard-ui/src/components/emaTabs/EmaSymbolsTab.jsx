import StrategySymbolsTab from "../strategyTabs/StrategySymbolsTab";

export default function EmaSymbolsTab(props) {
  return <StrategySymbolsTab {...props} strategy="EMA" endpointPrefix="/api/ema" showTargetPrice />;
}
