import type { Cluster, FleetDeploymentSummary, JobStatusResponse } from "../api"
import { isObservableProduct, productLabel } from "../constants/products"
import { clusterDisplayName } from "../utils/serviceNavGroups"
import { buildFleetMetricTiles } from "./fleetMetricTiles"
import { JobStatusTiles } from "./JobStatusTiles"
import { StatusPill } from "./StatusPill"

type FleetClusterOverviewCardProps = {
  cluster: Cluster
  serviceId: string
  jobSnapshot?: JobStatusResponse
  depSummary?: FleetDeploymentSummary
  healthy?: boolean
  healthMessage?: string
  healthLoading?: boolean
  onOpenCluster: () => void
  onNavigateDeployment: (namespace?: string) => void
}

function statusVariant(status: string): "ok" | "warn" | "crit" | "unknown" {
  if (status === "healthy") return "ok"
  if (status === "degraded") return "warn"
  if (status === "critical") return "crit"
  return "unknown"
}

export function FleetClusterOverviewCard({
  cluster,
  serviceId,
  jobSnapshot,
  depSummary,
  healthy,
  healthMessage,
  healthLoading,
  onOpenCluster,
  onNavigateDeployment,
}: FleetClusterOverviewCardProps) {
  const name = clusterDisplayName(cluster)
  const deployments = depSummary?.deployments ?? []
  const showWorkload =
    isObservableProduct(serviceId) &&
    cluster.product === serviceId &&
    depSummary?.cluster_id === cluster.id

  return (
    <div className="fleet-cluster-box">
      <div className="fleet-cluster-head">
        <div className="fleet-cluster-head-main">
          <button type="button" className="fleet-cluster-name-btn" onClick={onOpenCluster}>
            {name}
          </button>
          <div className="mono fleet-cluster-id">{cluster.id}</div>
        </div>
        <div className="fleet-cluster-head-meta">
          {!cluster.kubeconfig_present && (
            <span className="tag tag-sm tag-warn" title="Kubeconfig missing on hub">
              no kc
            </span>
          )}
          <StatusPill
            variant={healthLoading ? "unknown" : healthy ? "ok" : "crit"}
            label={healthLoading ? "API…" : healthy ? "API OK" : "Unreachable"}
          />
          <button type="button" className="link-btn metrics-chart-action" onClick={onOpenCluster}>
            Open →
          </button>
        </div>
      </div>

      <div className="fleet-cluster-details">
        <dl className="fleet-cluster-dl">
          <div>
            <dt>Context</dt>
            <dd className="mono detail-break">{cluster.context}</dd>
          </div>
          <div>
            <dt>Kubeconfig</dt>
            <dd className="detail-break">
              {cluster.kubeconfig_present ? (
                <span className="detail-ok">Present</span>
              ) : (
                <span className="detail-warn">Missing on hub</span>
              )}
            </dd>
          </div>
          <div>
            <dt>Control plane</dt>
            <dd className="detail-break">{healthMessage ?? "—"}</dd>
          </div>
        </dl>

        {jobSnapshot && (
          <div className="fleet-cluster-metrics">
            <div className="fleet-cluster-subtitle">Prometheus & exporter metrics</div>
            <JobStatusTiles
              items={buildFleetMetricTiles(serviceId, jobSnapshot.items, depSummary)}
              compact
              emptyMessage="No metrics yet."
              onTileNavigate={() => onNavigateDeployment()}
            />
          </div>
        )}

        {showWorkload ? (
          <div className="fleet-cluster-workloads">
            <div className="fleet-cluster-subtitle">
              Deployments
              {depSummary && (
                <span className="fleet-cluster-dep-count">
                  {depSummary.deployment_count} total · {depSummary.healthy_count} healthy
                  {(depSummary.with_issues_count ?? 0) > 0 &&
                    ` · ${depSummary.with_issues_count} with issues`}
                </span>
              )}
            </div>
            {depSummary?.error && !depSummary.deployment_count && (
              <p className="detail-note detail-break">{depSummary.error}</p>
            )}
            {deployments.length > 0 ? (
              <ul className="fleet-dep-detail-list fleet-dep-detail-list--nested">
                {deployments.map((dep) => {
                  const hasIssue = dep.status !== "healthy" || Boolean(dep.issue_preview)
                  return (
                    <li
                      key={`${dep.namespace}-${dep.name}`}
                      className={hasIssue ? "fleet-dep-row--issue" : "fleet-dep-row--ok"}
                    >
                      <button
                        type="button"
                        className="fleet-dep-name-link"
                        onClick={() => onNavigateDeployment(dep.namespace)}
                      >
                        {dep.name}
                      </button>
                      <span className="mono" style={{ fontSize: 10, color: "var(--text-muted)" }}>
                        {dep.namespace}
                      </span>
                      <StatusPill
                        variant={statusVariant(dep.status ?? "unknown")}
                        label={dep.status ?? "?"}
                      />
                      {dep.issue_preview ? (
                        <button
                          type="button"
                          className="fleet-issue-preview fleet-issue-text--issue"
                          onClick={() => onNavigateDeployment(dep.namespace)}
                        >
                          {dep.issue_preview}
                        </button>
                      ) : (
                        <span className="fleet-issue-preview fleet-issue-text--ok">
                          No issues detected
                        </span>
                      )}
                    </li>
                  )
                })}
              </ul>
            ) : (
              !depSummary?.error && (
                <p className="detail-note">No deployments discovered (VPN / kubeconfig).</p>
              )
            )}
          </div>
        ) : (
          <p className="detail-note">
            {productLabel(serviceId)} observability applies when this cluster is registered as the
            primary engine for {serviceId}.
          </p>
        )}

        {cluster.awc_console_url && (
          <a
            className="link-btn fleet-cluster-awc"
            href={cluster.awc_console_url}
            target="_blank"
            rel="noreferrer"
          >
            AWC console — {productLabel(cluster.product)} →
          </a>
        )}
      </div>
    </div>
  )
}
