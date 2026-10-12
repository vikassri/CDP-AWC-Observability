import { useQuery } from "@tanstack/react-query"
import { useEffect, useMemo, useRef, useState } from "react"
import { fetchJobStatus, fetchProductOverview, type ServiceDeploymentRow } from "../api"
import { REFETCH_FAST_MS } from "../constants/refetch"
import { buildLogAnalyzeContext } from "./LogAiAnalyze"
import { CollapsibleSection } from "./CollapsibleSection"
import { DeploymentCollapsibleCard } from "./DeploymentCollapsibleCard"
import { DeploymentLogsBlock } from "./DeploymentLogsBlock"
import { DeploymentSearchList } from "./DeploymentSearchList"
import { JobStatusTiles } from "./JobStatusTiles"
import { MetricsChart } from "./MetricsChart"
import { PrometheusSourceCaption } from "./PrometheusSourceCaption"
import { StatusPill } from "./StatusPill"
import { deploymentKey } from "../utils/deploymentKey"
import { pickDefaultExpandedDeploymentKey } from "../utils/deploymentExpand"
import { filterDeployments, groupDeploymentsByNamespace } from "../utils/filterDeployments"

type SparkDeploymentsDashboardProps = {
  clusterId: string
  focusNamespace?: string
  onFocusApplied?: () => void
}

export function SparkDeploymentsDashboard({
  clusterId,
  focusNamespace,
  onFocusApplied,
}: SparkDeploymentsDashboardProps) {
  const [searchQuery, setSearchQuery] = useState("")
  const [expandedKey, setExpandedKey] = useState<string | null>(null)
  const expandInitRef = useRef(false)

  const overview = useQuery({
    queryKey: ["product-overview", "spark", clusterId],
    queryFn: () => fetchProductOverview("spark", clusterId),
    refetchInterval: REFETCH_FAST_MS,
    refetchIntervalInBackground: true,
  })

  const jobStatus = useQuery({
    queryKey: ["job-status", clusterId, "spark"],
    queryFn: () => fetchJobStatus(clusterId),
    refetchInterval: REFETCH_FAST_MS,
    refetchIntervalInBackground: true,
  })

  const data = overview.data
  const deployments = data?.deployments ?? []
  const displayName = data?.display_name ?? clusterId

  const issueCount = useMemo(
    () => deployments.filter((d) => d.status !== "healthy").length,
    [deployments]
  )

  const filtered = useMemo(
    () => filterDeployments(deployments, searchQuery),
    [deployments, searchQuery]
  )
  const workspaceGroups = useMemo(
    () => groupDeploymentsByNamespace(filtered),
    [filtered]
  )

  const multipleDeployments = deployments.length > 1

  useEffect(() => {
    expandInitRef.current = false
  }, [clusterId])

  useEffect(() => {
    if (focusNamespace) {
      setExpandedKey(pickDefaultExpandedDeploymentKey(deployments, focusNamespace))
      onFocusApplied?.()
      return
    }
    if (expandInitRef.current || !deployments.length) return
    expandInitRef.current = true
    setExpandedKey(pickDefaultExpandedDeploymentKey(deployments))
  }, [deployments, focusNamespace, onFocusApplied, clusterId])

  const visibleDeployments = searchQuery.trim() ? filtered : deployments

  return (
    <section className="nifi-dashboard spark-dashboard">
      <div className="panel spark-deployments-panel">
        <div className="panel-header panel-header--stacked">
          <div>
            <h2 className="panel-title">{displayName}</h2>
            <p className="panel-subtitle">
              Spark workspaces &amp; applications — one view for CDE deploys and running apps
            </p>
            <PrometheusSourceCaption
              isFetching={jobStatus.isFetching || overview.isFetching}
              dataUpdatedAt={overview.dataUpdatedAt || jobStatus.dataUpdatedAt}
              prometheusAvailable={jobStatus.data?.prometheus_available}
              clusterId={clusterId}
            />
          </div>
          <div className="panel-header-actions">
            {multipleDeployments ? (
              <button type="button" className="link-btn" onClick={() => setExpandedKey(null)}>
                Collapse all
              </button>
            ) : null}
            <StatusPill
              variant={overview.isFetching ? "warn" : issueCount ? "warn" : "ok"}
              label={
                overview.isFetching
                  ? "Syncing…"
                  : issueCount
                    ? `${issueCount} with issues · ${deployments.length} apps`
                    : `${deployments.length} apps · Live`
              }
            />
          </div>
        </div>

        <div className="panel-body spark-panel-body">
          <div className="spark-metrics-strip">
            <JobStatusTiles
              items={jobStatus.data?.items ?? []}
              compact
              emptyMessage="No Prometheus metrics yet."
            />
          </div>

          {deployments.length > 3 ? (
            <label className="deployment-search-field">
              <span className="visually-hidden">Search Spark applications</span>
              <input
                type="search"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search workspace, application, or issue…"
                className="deployment-search-input"
              />
            </label>
          ) : null}

          <div
            className={`spark-workspace-list${
              workspaceGroups.length > 6 ? " spark-workspace-list--scroll" : ""
            }`}
          >
            {workspaceGroups.map((group) => {
              const groupIssues = group.deployments.filter((d) => d.status !== "healthy").length
              return (
                <CollapsibleSection
                  key={group.namespace}
                  className="collapsible-section--nested spark-workspace-group"
                  title={group.namespace}
                  hint={`${group.deployments.length} application(s)${
                    groupIssues ? ` · ${groupIssues} with issues` : ""
                  }`}
                  defaultCollapsed={workspaceGroups.length > 5 && !focusNamespace}
                >
                  <DeploymentSearchList
                    rows={group.deployments}
                    selectedKey={expandedKey}
                    onSelect={setExpandedKey}
                    deploymentKey={(row) => deploymentKey(row.namespace, row.name)}
                    renderName={(dep) => (
                      <>
                        <strong>{dep.name}</strong>
                        {dep.detail && typeof dep.detail === "object" && "state" in dep.detail ? (
                          <div className="mono spark-app-state">
                            {String((dep.detail as { state?: string }).state ?? "")}
                          </div>
                        ) : null}
                      </>
                    )}
                    emptyMessage="No applications in this workspace."
                    showSearch={false}
                  />
                </CollapsibleSection>
              )
            })}
          </div>

          {!deployments.length && !overview.isLoading ? (
            <div className="empty-state">No Spark applications found (VPN / kubeconfig).</div>
          ) : null}
          {!workspaceGroups.length && deployments.length > 0 ? (
            <div className="empty-state">No applications match your search.</div>
          ) : null}
          {searchQuery.trim() && filtered.length ? (
            <p className="deployment-search-count">
              Showing {filtered.length} of {deployments.length} applications
            </p>
          ) : null}
        </div>
      </div>

      <MetricsChart
        title="Spark apps by state"
        query='sum by (state) (spark_applications_total{cluster="$cluster"})'
        clusterId={clusterId}
        hours={3}
        refetchMs={REFETCH_FAST_MS}
      />

      {visibleDeployments.map((dep) => {
        const key = deploymentKey(dep.namespace, dep.name)
        return (
          <SparkApplicationCard
            key={key}
            clusterId={clusterId}
            deployment={dep}
            expanded={expandedKey === key}
            onToggle={() => setExpandedKey((cur) => (cur === key ? null : key))}
            isOverviewLoading={overview.isLoading}
          />
        )
      })}
    </section>
  )
}

function SparkApplicationCard({
  clusterId,
  deployment,
  expanded,
  onToggle,
  isOverviewLoading,
}: {
  clusterId: string
  deployment: ServiceDeploymentRow
  expanded: boolean
  onToggle: () => void
  isOverviewLoading?: boolean
}) {
  const state =
    deployment.detail && typeof deployment.detail === "object" && "state" in deployment.detail
      ? String((deployment.detail as { state?: string }).state ?? "")
      : null

  return (
    <DeploymentCollapsibleCard
      expanded={expanded}
      onToggle={onToggle}
      status={deployment.status}
      layerLabel="Spark application"
      title={<strong style={{ fontSize: 14 }}>{deployment.name}</strong>}
      subtitle={
        <div className="mono" style={{ fontSize: 11, color: "var(--text-muted)" }}>
          {deployment.namespace}
          {state ? ` · ${state}` : ""}
        </div>
      }
      logsSource={deployment.logs?.source ?? "logs"}
      body={
        <>
          {deployment.issues.length > 0 ? (
            <ul className="nifi-issue-list">
              {deployment.issues.map((issue) => (
                <li key={issue}>{issue}</li>
              ))}
            </ul>
          ) : (
            <p style={{ margin: "0 0 0.75rem" }}>No issues detected.</p>
          )}
          <div className="job-status-grid job-status-grid--stack">
            {Object.entries(deployment.metrics).map(([key, value]) => (
              <div key={key} className="job-status-tile">
                <div className="job-status-value">{value ?? "—"}</div>
                <div className="job-status-label">{key.replace(/_/g, " ")}</div>
              </div>
            ))}
          </div>
        </>
      }
      logs={
        <DeploymentLogsBlock
          deploymentName={deployment.name}
          namespace={deployment.namespace}
          logs={deployment.logs}
          isLoading={isOverviewLoading}
          analyze={buildLogAnalyzeContext(clusterId, "spark", deployment)}
        />
      }
    />
  )
}
