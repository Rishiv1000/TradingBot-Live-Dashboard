import StrategyLiveDFTab from "../strategyTabs/StrategyLiveDFTab";

export default function EmaLiveDFTab(props) {
  return <StrategyLiveDFTab {...props} strategy="EMA" endpointPrefix="/api/ema" />;
}
