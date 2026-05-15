import StrategyLiveDFTab from "../strategyTabs/StrategyLiveDFTab";

export default function GreenLiveDFTab(props) {
  return <StrategyLiveDFTab {...props} strategy="GREEN" endpointPrefix="/api/green" />;
}
