import { useQuery } from "@tanstack/react-query"
import { useEffect, useMemo, useRef, useState } from "react"
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts"
import { fetchProductOverview, type ServiceDeploymentRow } from "../api"
import { REFETCH_FAST_MS } from "../constants/refetch"
import { buildLogAnalyzeContext } from "./LogAiAnalyze"
import { JobStatusPanel } from "./JobStatusPanel"
import { MetricsChart } from "./MetricsChart"
import { DeploymentLogsBlock } from "./DeploymentLogsBlock"
import { StatusPill } from "./StatusPill"
import { DeploymentCollapsibleCard } from "./DeploymentCollapsibleCard"
import { DeploymentSearchList } from "./DeploymentSearchList"
import { deploymentKey } from "../utils/deploymentKey"
import { pickDefaultExpandedDeploymentKey } from "../utils/deploymentExpand"

const CHART_BY_PRODUCT: Record<string, { title: string; query: string }> = {
  nifi: {
    title: "NiFi JVM heap usage (%)",
    query: 'avg(nifi_jvm_heap_usage{cluster="$cluster"}) * 100',
  },
  spark: {
    title: "Spark apps by state",
    query: 'sum by (state) (spark_applications_total{cluster="$cluster"})',
  },
  trino: {
    title: "Trino engine ready",
    query: 'max(trino_engine_ready{cluster="$cluster"})',
  },
  flink: {
    title: "Flink jobs by state",
    query: 'sum by (job_state) (flink_deployments_total{cluster="$cluster"})',
  },
  airflow: {
    title: "DAG runs by state",
    query: 'sum by (state) (airflow_dagrun_finished_total{cluster="$cluster"})',
  },
}

type ServiceDeploymentsDashboardProps = {
  product: string
  clusterId: string
  heading?: string
  focusNamespace?: string
  onFocusApplied?: () => void
}

export function ServiceDeploymentsDashboard({
  product,
  clusterId,
  heading,
  focusNamespace,
  onFocusApplied,
}: ServiceDeploymentsDashboardProps) {
  const [history, setHistory] = useState<Array<{ t: string; count: number }>>([])
  const [expandedKey, setExpandedKey] = useState<string | null>(null)
  const expandInitRef = useRef(false)

  const overview = useQuery({
    queryKey: ["product-overview", product, clusterId],
    queryFn: () => fetchProductOverview(product, clusterId),
    refetchInterval: REFETCH_FAST_MS,
    refetchIntervalInBackground: true,
  })

  const data = overview.data
  const deployments = data?.deployments ?? []
  const issueCount = useMemo(
    () => deployments.filter((d) => d.status !== "healthy").length,
    [deployments]
  )

  useEffect(() => {
    if (!data) return
    const label = new Date().toLocaleTimeString([], {
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
    })
    setHistory((prev) => {
      const next = [...prev, { t: label, count: data.deployment_count }]
      return next.length > 40 ? next.slice(-40) : next
    })
  }, [data?.deployment_count, overview.dataUpdatedAt])

  const multipleDeployments = deployments.length > 1

  useEffect(() => {
    expandInitRef.current = false
  }, [clusterId, product])

  useEffect(() => {
    if (focusNamespace) {
      setExpandedKey(pickDefaultExpandedDeploymentKey(deployments, focusNamespace))
      onFocusApplied?.()
      return
    }
    if (expandInitRef.current || !deployments.length) return
    expandInitRef.current = true
    setExpandedKey(pickDefaultExpandedDeploymentKey(deployments))
  }, [deployments, focusNamespace, onFocusApplied, clusterId, product])

  const chart = CHART_BY_PRODUCT[product]
  const title = heading ?? `${product.toUpperCase()} deployments`

  return (
    <section className="nifi-dashboard">
      <JobStatusPanel
        clusterId={clusterId}
        product={product}
        title="Prometheus & exporter metrics"
        showSourceCaption
      />
      <div className="panel">
        <div className="panel-header">
          <h2 className="panel-title">
            {title} — {data?.display_name ?? clusterId}
          </h2>
          <div className="panel-header-actions">
            {multipleDeployments ? (
              <button
                type="button"
                className="link-btn"
                onClick={() => setExpandedKey(null)}
              >
                Collapse all
              </button>
            ) : null}
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
        </div>
        <div className="panel-body" style={{ paddingTop: 0 }}>
          <DeploymentSearchList
            rows={deployments}
            selectedKey={expandedKey}
            onSelect={setExpandedKey}
            deploymentKey={(dep) => deploymentKey(dep.namespace, dep.name)}
          />
          {!deployments.length && !overview.isLoading && (
            <div className="empty-state">No deployments found (VPN / kubeconfig).</div>
          )}
        </div>
      </div>

      {chart && (
        <MetricsChart
          title={chart.title}
          query={chart.query}
          clusterId={clusterId}
          hours={3}
          refetchMs={REFETCH_FAST_MS}
          valueDecimals={
            chart.title.includes("%") || chart.query.includes("heap_usage") ? 2 : undefined
          }
        />
      )}

      {deployments.map((dep) => {
        const key = deploymentKey(dep.namespace, dep.name)
        return (
          <DeploymentStackCard
            key={key}
            product={product}
            clusterId={clusterId}
            deployment={dep}
            expanded={expandedKey === key}
            onToggle={() => setExpandedKey((cur) => (cur === key ? null : key))}
            isOverviewLoading={overview.isLoading}
          />
        )
      })}

      <div className="panel">
        <div className="panel-header">
          <h3 className="panel-title">Deployment count (live)</h3>
        </div>
        <div style={{ height: 140, padding: "0.5rem 1rem 1rem" }}>
          {history.length > 1 ? (
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={history}>
                <CartesianGrid stroke="#e2e8f0" strokeDasharray="3 3" />
                <XAxis dataKey="t" tick={{ fontSize: 10 }} stroke="#94a3b8" />
                <YAxis allowDecimals={false} tick={{ fontSize: 10 }} stroke="#94a3b8" width={32} />
                <Tooltip contentStyle={{ fontSize: 12 }} />
                <Line type="monotone" dataKey="count" stroke="#0050a0" strokeWidth={2} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          ) : (
            <div className="empty-state">Collecting samples…</div>
          )}
        </div>
      </div>
    </section>
  )
}

function DeploymentStackCard({
  product,
  clusterId,
  deployment,
  expanded,
  onToggle,
  isOverviewLoading,
}: {
  product: string
  clusterId: string
  deployment: ServiceDeploymentRow
  expanded: boolean
  onToggle: () => void
  isOverviewLoading?: boolean
}) {
  return (
    <DeploymentCollapsibleCard
      expanded={expanded}
      onToggle={onToggle}
      status={deployment.status}
      layerLabel={`${product.toUpperCase()} deployment`}
      title={<strong style={{ fontSize: 14 }}>{deployment.name}</strong>}
      subtitle={
        <div className="mono" style={{ fontSize: 11, color: "var(--text-muted)" }}>
          {deployment.namespace}
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
          {deployment.detail ? (
            <pre className="nifi-log-pre" style={{ maxHeight: 80 }}>
              {JSON.stringify(deployment.detail, null, 2)}
            </pre>
          ) : null}
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
          analyze={buildLogAnalyzeContext(clusterId, product, deployment)}
        />
      }
    />
  )
}
