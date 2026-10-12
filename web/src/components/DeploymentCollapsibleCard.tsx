import type { ReactNode } from "react"
import { StatusPill } from "./StatusPill"

export function deploymentStatusVariant(status: string): "ok" | "warn" | "crit" | "unknown" {
  if (status === "healthy") return "ok"
  if (status === "degraded") return "warn"
  if (status === "critical") return "crit"
  return "unknown"
}

export function deploymentStatusLabel(status: string): string {
  if (status === "healthy") return "Healthy"
  if (status === "degraded") return "Degraded"
  if (status === "critical") return "Critical"
  return status
}

export function deploymentStackClass(status: string): string {
  if (status === "healthy") return "healthy"
  if (status === "critical") return "critical"
  return "contributing"
}

type DeploymentCollapsibleCardProps = {
  expanded: boolean
  onToggle: () => void
  status: string
  layerLabel: string
  title: ReactNode
  subtitle?: ReactNode
  logsSource?: string
  body: ReactNode
  logs: ReactNode
}

export function DeploymentCollapsibleCard({
  expanded,
  onToggle,
  status,
  layerLabel,
  title,
  subtitle,
  logsSource,
  body,
  logs,
}: DeploymentCollapsibleCardProps) {
  return (
    <div
      className={`stack-card ${deploymentStackClass(status)}${
        expanded ? "" : " stack-card--minimized"
      }`}
    >
      <button
        type="button"
        className="nifi-stack-toggle"
        onClick={onToggle}
        aria-expanded={expanded}
      >
        <div
          className="stack-card-header"
          style={{ borderBottom: expanded ? undefined : "none" }}
        >
          <div className="stack-card-header-main">
            <div className="stack-layer">{layerLabel}</div>
            <div className="stack-card-title-row">{title}</div>
            {subtitle}
          </div>
          <div className="stack-card-header-meta">
            {logsSource ? <span className="tag tag-sm">{logsSource}</span> : null}
            <StatusPill
              variant={deploymentStatusVariant(status)}
              label={deploymentStatusLabel(status)}
            />
            <span className="stack-card-toggle-label">{expanded ? "Minimize" : "Expand"}</span>
          </div>
        </div>
      </button>
      {expanded ? (
        <>
          <div className="stack-body">{body}</div>
          <div className="stack-logs">{logs}</div>
        </>
      ) : null}
    </div>
  )
}
