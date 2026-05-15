import StrategyTerminalTab from "../strategyTabs/StrategyTerminalTab";

export default function GreenTerminalTab(props) {
  return <StrategyTerminalTab {...props} strategy="GREEN" endpointPrefix="/api/green" />;
}
