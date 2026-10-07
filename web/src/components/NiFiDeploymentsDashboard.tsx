import { useQuery } from "@tanstack/react-query"
import { useEffect, useMemo, useState } from "react"
import { fetchNifiOverview, type NifiDeploymentRow } from "../api"
import { REFETCH_FAST_MS } from "../constants/refetch"
import { NIFI_CLUSTER_CHARTS, nifiNamespaceCharts } from "../constants/nifiCharts"
import { JobStatusPanel } from "./JobStatusPanel"
import { MetricsChart } from "./MetricsChart"
import { formatPercent } from "../utils/formatMetrics"
import { CollapsibleSection } from "./CollapsibleSection"
import { ClusterLogsPanel } from "./ClusterLogsPanel"
import { DeploymentLogsBlock } from "./DeploymentLogsBlock"
import { StatusPill } from "./StatusPill"
import { deploymentKey } from "../utils/deploymentKey"
import { buildLogAnalyzeContext } from "./LogAiAnalyze"
import { aggregateDeploymentLogs } from "../utils/logHits"

type NiFiDeploymentsDashboardProps = {
  clusterId?: string
  focusNamespace?: string
  onFocusApplied?: () => void
}

function statusVariant(status: string): "ok" | "warn" | "crit" | "unknown" {
  if (status === "healthy") return "ok"
  if (status === "degraded") return "warn"
  if (status === "critical") return "crit"
  return "unknown"
}

function statusLabel(status: string): string {
  if (status === "healthy") return "Healthy"
  if (status === "degraded") return "Degraded"
  if (status === "critical") return "Critical"
  return status
}

function stackClass(status: string): string {
  if (status === "healthy") return "healthy"
  if (status === "critical") return "critical"
  return "contributing"
}

export function NiFiDeploymentsDashboard({
  clusterId = "cdf",
  focusNamespace,
  onFocusApplied,
}: NiFiDeploymentsDashboardProps) {
  const [expandedNs, setExpandedNs] = useState<string | null>(null)

  const overview = useQuery({
    queryKey: ["nifi-overview", clusterId],
    queryFn: () => fetchNifiOverview(clusterId),
    refetchInterval: REFETCH_FAST_MS,
    refetchIntervalInBackground: true,
  })

  const data = overview.data
  const issueCount = useMemo(
    () => (data?.deployments ?? []).filter((d) => d.status !== "healthy").length,
    [data]
  )

  const clusterLogs = useMemo(
    () => aggregateDeploymentLogs(data?.deployments ?? []),
    [data?.deployments]
  )
  const clusterLogPreview = useMemo(() => clusterLogs.lines.slice(0, 24), [clusterLogs.lines])
  const clusterLogAll = useMemo(() => clusterLogs.lines, [clusterLogs.lines])

  const clusterAnalyze = useMemo(() => {
    const issues = (data?.deployments ?? []).flatMap((d) => d.issues)
    return {
      clusterId,
      product: "nifi",
      name: clusterId,
      namespace: "all-nifi-namespaces",
      status: issueCount ? "degraded" : "healthy",
      issues,
      metrics: {},
      logs: {
        source: clusterLogs.sources.join(", ") || "kubectl",
        lines: clusterLogAll,
        flagged: clusterLogs.flagged,
        bulletins: clusterLogs.bulletins,
        scanned_pod: null,
      },
    }
  }, [clusterId, clusterLogAll, clusterLogs, data?.deployments, issueCount])

  useEffect(() => {
    if (focusNamespace) {
      const match = data?.deployments?.find((d) => d.namespace === focusNamespace)
      setExpandedNs(
        match ? deploymentKey(match.namespace, match.name) : focusNamespace
      )
      onFocusApplied?.()
      return
    }
    const first = data?.deployments?.[0]
    if (first && !expandedNs) {
      setExpandedNs(deploymentKey(first.namespace, first.name))
    }
  }, [data?.deployments, expandedNs, focusNamespace, onFocusApplied])

  return (
    <section className="nifi-dashboard">
      <JobStatusPanel
        clusterId={clusterId}
        product="nifi"
        title="NiFi summary metrics"
        showSourceCaption
      />
      <div className="panel">
        <div className="panel-header">
          <h2 className="panel-title">NiFi deployments — {data?.display_name ?? clusterId}</h2>
          <StatusPill
            variant={overview.isFetching ? "warn" : issueCount ? "warn" : "ok"}
            label={
              overview.isFetching
                ? "Syncing…"
                : issueCount
                  ? `${issueCount} with issues · ${REFETCH_FAST_MS / 1000}s`
                  : `Live · ${REFETCH_FAST_MS / 1000}s`
            }
          />
        </div>

        <div className="panel-body" style={{ paddingTop: 0 }}>
          <table className="data-table nifi-dep-table">
            <thead>
              <tr>
                <th>Deployment</th>
                <th>Status</th>
                <th>Pods</th>
                <th>Issues</th>
              </tr>
            </thead>
            <tbody>
              {(data?.deployments ?? []).map((dep) => {
                const key = deploymentKey(dep.namespace, dep.name)
                return (
                <tr
                  key={key}
                  className={expandedNs === key ? "selected" : ""}
                  onClick={() => setExpandedNs(key)}
                >
                  <td>
                    <strong className="mono">{dep.namespace}</strong>
                  </td>
                  <td>
                    <StatusPill variant={statusVariant(dep.status)} label={statusLabel(dep.status)} />
                  </td>
                  <td className="mono">
                    {dep.pods_ready ?? "—"}/{dep.pods_total ?? "—"}
                  </td>
                  <td>
                    {dep.issues.length ? (
                      <span className="nifi-issue-summary">{dep.issues[0]}</span>
                    ) : (
                      <span style={{ color: "var(--text-muted)" }}>No issues detected</span>
                    )}
                    {dep.issues.length > 1 && (
                      <span className="nifi-issue-more"> +{dep.issues.length - 1} more</span>
                    )}
                  </td>
                </tr>
              )})}
            </tbody>
          </table>
          {!data?.deployments?.length && !overview.isLoading && (
            <div className="empty-state">No NiFi deployments found (VPN / kubeconfig).</div>
          )}
        </div>
      </div>

      <CollapsibleSection
        title={`Cluster-wide flow metrics (${clusterId.toUpperCase()})`}
        hint="Sum/max across all NiFi namespaces on this cluster — federated Prometheus (dfx-nifi-web), last 2h."
        defaultCollapsed
      >
        <div className="nifi-metrics-chart-grid">
          {NIFI_CLUSTER_CHARTS.map((chart) => (
            <MetricsChart
              key={chart.title}
              title={chart.title}
              query={chart.query}
              clusterId={clusterId}
              hours={2}
              refetchMs={REFETCH_FAST_MS}
              valueDecimals={chart.valueDecimals}
              defaultCollapsed
            />
          ))}
        </div>
      </CollapsibleSection>

      {(data?.deployments ?? []).map((dep) => {
        const key = deploymentKey(dep.namespace, dep.name)
        return (
          <DeploymentStackCard
            key={key}
            clusterId={clusterId}
            deployment={dep}
            expanded={expandedNs === key}
            onToggle={() => setExpandedNs((cur) => (cur === key ? null : key))}
            isOverviewLoading={overview.isLoading}
          />
        )
      })}

      <CollapsibleSection
        title={`Cluster logs — ${data?.display_name ?? clusterId}`}
        hint="App-log tails from all NiFi namespaces on this cluster (kubectl / OTel)."
        defaultCollapsed={false}
      >
        <ClusterLogsPanel
          title={`NiFi ${data?.display_name ?? clusterId}`}
          sourcesLabel={`${clusterLogs.sources.join(", ") || "kubectl / OTel"} · cluster ${clusterId}`}
          bulletins={clusterLogs.bulletins}
          flagged={clusterLogs.flagged}
          previewLines={clusterLogPreview}
          allLines={clusterLogAll}
          emptyMessage="No recent log lines. Connect VPN and ensure kubectl collectors run."
          isLoading={overview.isLoading}
          analyze={clusterAnalyze}
        />
      </CollapsibleSection>
    </section>
  )
}

function DeploymentStackCard({
  clusterId,
  deployment,
  expanded,
  onToggle,
  isOverviewLoading,
}: {
  clusterId: string
  deployment: NifiDeploymentRow
  expanded: boolean
  onToggle: () => void
  isOverviewLoading?: boolean
}) {
  const ns = deployment.namespace
  return (
    <div className={`stack-card ${stackClass(deployment.status)}`}>
      <button type="button" className="nifi-stack-toggle" onClick={onToggle}>
        <div className="stack-card-header" style={{ borderBottom: expanded ? undefined : "none" }}>
          <div>
            <div className="stack-layer">NiFi data flow (namespace)</div>
            <strong className="mono" style={{ fontSize: 13 }}>
              {ns}
            </strong>
          </div>
          <div className="stack-card-header-meta">
            <span className="tag tag-sm">{deployment.logs?.source ?? "logs"}</span>
            <StatusPill
              variant={statusVariant(deployment.status)}
              label={statusLabel(deployment.status)}
            />
          </div>
        </div>
      </button>

      {expanded && (
        <div className="stack-body">
          {deployment.issues.length > 0 ? (
            <ul className="nifi-issue-list">
              {deployment.issues.map((issue) => (
                <li key={issue}>{issue}</li>
              ))}
            </ul>
          ) : (
            <p style={{ margin: "0 0 0.75rem" }}>No issues detected for this deployment.</p>
          )}

          <div className="job-status-grid" style={{ padding: 0, marginBottom: "0.75rem" }}>
            {Object.entries(deployment.metrics).map(([key, value]) => {
              const label =
                key === "deployed_flows"
                  ? "Deployed flows"
                  : key === "memory_usage_pct"
                    ? "Memory usage"
                    : key.replace(/_/g, " ")
              const display =
                key === "memory_usage_pct" && value != null
                  ? formatPercent(Number(value), 2)
                  : value ?? "—"
              return (
                <div key={key} className="job-status-tile">
                  <div className="job-status-value">{display}</div>
                  <div className="job-status-label">{label}</div>
                </div>
              )
            })}
          </div>

          <CollapsibleSection
            className="collapsible-section--nested"
            title={`Flow metrics — ${ns}`}
            hint="Same metrics as cluster-wide, scoped to this namespace only."
            defaultCollapsed
          >
            <div className="nifi-metrics-chart-grid">
              {nifiNamespaceCharts(ns).map((chart) => (
                <MetricsChart
                  key={`${ns}-${chart.title}`}
                  title={chart.title}
                  query={chart.query}
                  clusterId={clusterId}
                  hours={2}
                  refetchMs={REFETCH_FAST_MS}
                  valueDecimals={chart.valueDecimals}
                  defaultCollapsed
                />
              ))}
            </div>
          </CollapsibleSection>
        </div>
      )}

      <div className="stack-logs">
        <DeploymentLogsBlock
          deploymentName={deployment.namespace}
          namespace={deployment.namespace}
          logs={deployment.logs}
          isLoading={isOverviewLoading}
          analyze={buildLogAnalyzeContext(clusterId, "nifi", deployment)}
        />
      </div>
    </div>
  )
}
