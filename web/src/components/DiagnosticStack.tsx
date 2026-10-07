import type { Cluster } from "../api"
import { StatusPill } from "./StatusPill"

type DiagnosticStackProps = {
  cluster: Cluster
  healthy: boolean | undefined
  healthMessage: string | undefined
  isLoading: boolean
  collectorErrors: string[]
}

export function DiagnosticStack({
  cluster,
  healthy,
  healthMessage,
  isLoading,
  collectorErrors,
}: DiagnosticStackProps) {
  const apiVariant = isLoading ? "unknown" : healthy ? "healthy" : "critical"
  const apiLabel = isLoading ? "Checking" : healthy ? "Reachable" : "Unreachable"

  const hasCollectorIssue = collectorErrors.length > 0
  const metricsVariant = hasCollectorIssue ? "contributing" : healthy ? "healthy" : "contributing"

  return (
    <div className="panel">
      <div className="panel-header">
        <h2 className="panel-title">
          Diagnostic path — {cluster.display_name}
        </h2>
        <span className="tag">{cluster.product.toUpperCase()}</span>
        <span className="mono">{cluster.id}</span>
      </div>
      <div className="panel-body" style={{ padding: "0.75rem" }}>
        <div className={`stack-card ${apiVariant === "healthy" ? "healthy" : apiVariant === "critical" ? "critical" : "contributing"}`}>
          <div className="stack-card-header">
            <span className="stack-layer">Kubernetes API</span>
            <StatusPill
              variant={isLoading ? "unknown" : healthy ? "ok" : "crit"}
              label={apiLabel}
            />
          </div>
          <div className="stack-body">
            {healthMessage ?? "Awaiting health probe against cluster control plane."}
          </div>
        </div>

        <div className={`stack-card ${metricsVariant === "healthy" ? "healthy" : "contributing"}`}>
          <div className="stack-card-header">
            <span className="stack-layer">Metrics collectors</span>
            <StatusPill
              variant={hasCollectorIssue ? "warn" : healthy ? "ok" : "unknown"}
              label={hasCollectorIssue ? "Degraded" : "Nominal"}
            />
          </div>
          <div className="stack-body">
            {hasCollectorIssue ? (
              <ul style={{ margin: 0, paddingLeft: "1.1rem" }}>
                {collectorErrors.slice(0, 3).map((err) => (
                  <li key={err.slice(0, 40)} className="collector-error">
                    {err.length > 120 ? `${err.slice(0, 120)}…` : err}
                  </li>
                ))}
              </ul>
            ) : (
              <>Hub agents writing Prometheus file_sd for {cluster.product} workloads.</>
            )}
          </div>
        </div>

        <div className="stack-card healthy">
          <div className="stack-card-header">
            <span className="stack-layer">Observability plane</span>
            <StatusPill variant="unknown" label="Hub local" />
          </div>
          <div className="stack-body">
            Control plane API, SQLite audit store, optional Docker hub (Prometheus / Grafana / OTel).
            Enable VPN to lab network for live series and log correlation.
          </div>
        </div>
      </div>
    </div>
  )
}
