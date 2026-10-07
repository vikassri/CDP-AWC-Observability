import type { NifiDeploymentRow } from "../api"
import { ClusterLogsPanel } from "./ClusterLogsPanel"
import type { LogAnalyzeContext } from "./LogAiAnalyze"

type DeploymentLogs = NifiDeploymentRow["logs"]

type DeploymentLogsBlockProps = {
  deploymentName: string
  namespace: string
  logs: DeploymentLogs | undefined
  isLoading?: boolean
  analyze: LogAnalyzeContext
}

function normalizeLogs(logs: DeploymentLogs | undefined): DeploymentLogs {
  return (
    logs ?? {
      source: "pending",
      lines: [],
      flagged: [],
      bulletins: [],
      scanned_pod: null,
    }
  )
}

function emptyAppLogMessage(logs: DeploymentLogs): string {
  if (logs.source === "cached" || logs.source === "skipped") {
    return "Log tail skipped this refresh cycle — will update on the next full scan (~few seconds)."
  }
  if (logs.scanned_pod) {
    return `No recent app-log lines from pod ${logs.scanned_pod}.`
  }
  return "No pod selected for log tail. Discovery may be incomplete (VPN / kubeconfig)."
}

export function DeploymentLogsBlock({
  deploymentName,
  namespace,
  logs: rawLogs,
  isLoading,
  analyze,
}: DeploymentLogsBlockProps) {
  const logs = normalizeLogs(rawLogs)
  const bulletins = logs.bulletins ?? []
  const flagged = logs.flagged
  const previewLines = logs.lines.slice(0, 14)
  const allLines = logs.lines

  const title = `${deploymentName} (${namespace})`
  const sourcesLabel = [
    logs.source,
    logs.scanned_pod ? `pod ${logs.scanned_pod}` : null,
    namespace,
  ]
    .filter(Boolean)
    .join(" · ")

  return (
    <div className="deployment-logs-split">
      <ClusterLogsPanel
        mode="bulletins-only"
        title={title}
        sourcesLabel={`Parsed from app-log · ${namespace}`}
        bulletins={bulletins}
        flagged={[]}
        previewLines={[]}
        allLines={[]}
        emptyMessage="No bulletin lines in recent app-log."
        isLoading={isLoading}
        compact
        analyze={analyze}
      />
      <ClusterLogsPanel
        mode="app-logs-only"
        title={title}
        sourcesLabel={sourcesLabel}
        bulletins={[]}
        flagged={flagged}
        previewLines={previewLines}
        allLines={allLines}
        emptyMessage={emptyAppLogMessage(logs)}
        isLoading={isLoading}
        compact
        analyze={analyze}
      />
    </div>
  )
}
