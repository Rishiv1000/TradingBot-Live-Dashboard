import StrategySymbolsTab from "../strategyTabs/StrategySymbolsTab";

export default function GreenSymbolsTab(props) {
  return <StrategySymbolsTab {...props} strategy="GREEN" endpointPrefix="/api/green" showTargetPrice={false} />;
}
