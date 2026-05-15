import StrategyTerminalTab from "../strategyTabs/StrategyTerminalTab";

export default function EmaTerminalTab(props) {
  return <StrategyTerminalTab {...props} strategy="EMA" endpointPrefix="/api/ema" />;
}
