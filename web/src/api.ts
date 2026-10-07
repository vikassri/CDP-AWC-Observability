import type { LogSearchResponse } from "./utils/logHits"

const base = "/api"

export type { LogSearchResponse }

const apiFetch = (path: string, init?: RequestInit) =>
  fetch(`${base}${path}`, { credentials: "include", ...init })

async function parseApiError(res: Response): Promise<string> {
  const text = await res.text()
  try {
    const body = JSON.parse(text) as { detail?: string | Array<{ msg?: string }> }
    if (typeof body.detail === "string") return body.detail
    if (Array.isArray(body.detail) && body.detail[0]?.msg) return body.detail[0].msg
  } catch {
    /* plain text */
  }
  return text || res.statusText
}

async function get<T>(path: string): Promise<T> {
  const res = await apiFetch(path)
  if (!res.ok) throw new Error(await parseApiError(res))
  return res.json() as Promise<T>
}

export type AuthUser = {
  username: string
  authenticated: boolean
}

export const fetchAuthMe = () => get<AuthUser>("/auth/me")

export async function login(username: string, password: string): Promise<AuthUser> {
  const res = await apiFetch("/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password }),
  })
  if (!res.ok) throw new Error(await parseApiError(res))
  return res.json() as Promise<AuthUser>
}

export async function logout(): Promise<void> {
  const res = await apiFetch("/auth/logout", { method: "POST" })
  if (!res.ok) throw new Error(await parseApiError(res))
}

export type Cluster = {
  id: string
  display_name: string
  product: string
  context: string
  collectors: string[]
  awc_console_url: string | null
  kubeconfig_ref: string
  kubeconfig_present: boolean
  awc_engine_id: string
  services: string[]
}

export type ClusterHealth = {
  id: string
  healthy: boolean
  message: string
}

export type CollectorStatus = {
  name: string
  last_ok_at: string | null
  last_error: string | null
  detail: Record<string, unknown>
}

export type Remediation = {
  id: string
  cluster_id: string
  action_type: string
  status: string
  preview: string
  result_message: string
}

export const fetchClusters = () => get<Cluster[]>("/clusters")
export const fetchClusterHealth = (id: string) => get<ClusterHealth>(`/clusters/${id}/health`)
export const fetchCollectors = () => get<CollectorStatus[]>("/collectors")

export const fetchLogsSearch = (params: {
  cluster: string
  product?: string
  q?: string
  size?: number
}) => {
  const sp = new URLSearchParams()
  sp.set("cluster", params.cluster)
  if (params.product) sp.set("product", params.product)
  sp.set("q", params.q ?? "*")
  sp.set("size", String(params.size ?? 48))
  return get<LogSearchResponse>(`/logs/search?${sp.toString()}`)
}

export type NifiDeploymentRow = {
  name: string
  namespace: string
  status: string
  issues: string[]
  pods_ready?: number
  pods_total?: number
  has_prometheus: boolean
  local_port: number | null
  pods: string[]
  metrics: Record<string, number | null>
  logs: {
    source: string
    lines: string[]
    flagged: string[]
    bulletins?: string[]
    scanned_pod: string | null
  }
}

export type NifiOverview = {
  cluster_id: string
  display_name?: string
  deployment_count: number
  deployment_count_metric: number | null
  deployments: NifiDeploymentRow[]
  error?: string
}

export const fetchNifiOverview = (clusterId: string) =>
  get<NifiOverview>(`/nifi/overview?cluster=${encodeURIComponent(clusterId)}`)

export type ServiceDeploymentRow = {
  name: string
  namespace: string
  status: string
  issues: string[]
  pods_ready?: number
  pods_total?: number
  detail?: Record<string, unknown>
  metrics: Record<string, number | null>
  logs: NifiDeploymentRow["logs"]
}

export type ProductOverview = {
  product: string
  cluster_id: string
  display_name?: string
  deployment_count: number
  deployments: ServiceDeploymentRow[]
  error?: string
}

export const fetchProductOverview = (product: string, clusterId: string) =>
  get<ProductOverview>(
    `/products/${encodeURIComponent(product)}/overview?cluster=${encodeURIComponent(clusterId)}`
  )

export type AlertRuleCreate = {
  alert: string
  expr: string
  product: string
  severity?: string
  summary?: string
  for_duration?: string
  emails?: string[]
  enabled?: boolean
}

export type RecommendationResponse = {
  recommendation: string
  model: string | null
  source: string
  error?: string
}

export async function fetchRecommendation(body: {
  cluster_id: string
  product: string
  name: string
  namespace: string
  status: string
  issues: string[]
  metrics: Record<string, number | null>
  logs: ServiceDeploymentRow["logs"]
}): Promise<RecommendationResponse> {
  const res = await apiFetch("/recommendations", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  })
  if (!res.ok) throw new Error(await parseApiError(res))
  return res.json() as Promise<RecommendationResponse>
}

export async function createAlertRule(body: AlertRuleCreate): Promise<AlertRuleRow> {
  const res = await apiFetch("/alerts/rules", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  })
  if (!res.ok) throw new Error(await parseApiError(res))
  return res.json() as Promise<AlertRuleRow>
}
export const fetchRemediations = () => get<Remediation[]>("/remediations")
export const fetchMetricsCatalog = () => get<Array<{ product: string; query: string; title: string }>>("/metrics/catalog")

export type JobStatusItem = {
  key: string
  label: string
  value: number | null
  unit?: string | null
  error?: string | null
}

export type JobStatusResponse = {
  cluster_id: string
  product: string
  prometheus_available?: boolean
  items: JobStatusItem[]
}

export const fetchJobStatus = (clusterId: string) =>
  get<JobStatusResponse>(`/metrics/job-status?cluster=${encodeURIComponent(clusterId)}`)

export const fetchFleetJobStatus = () => get<{ products: Record<string, JobStatusResponse[]> }>(
  "/metrics/job-status?fleet=true"
)

export type FleetDeploymentSummary = {
  product: string
  cluster_id: string | null
  display_name: string | null
  deployment_count: number
  healthy_count: number
  with_issues_count: number
  error?: string | null
  deployments: Array<{
    name: string
    namespace: string
    status: string
    issue_preview: string | null
  }>
}

export type FleetDeploymentOverview = {
  products: Record<string, FleetDeploymentSummary>
  totals: { deployments: number; with_issues: number }
  refetch_hint_sec: number
}

export const fetchFleetDeploymentOverview = () =>
  get<FleetDeploymentOverview>("/products/fleet/overview")

export async function fetchMetricRange(
  query: string,
  opts?: { cluster?: string; hours?: number }
): Promise<unknown> {
  const res = await apiFetch("/metrics/range", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      query,
      hours: opts?.hours ?? 6,
      cluster: opts?.cluster ?? null,
    }),
  })
  if (!res.ok) throw new Error(await parseApiError(res))
  return res.json()
}

export type AlertRuleRow = {
  rule_id: string
  alert: string
  product: string
  expr: string
  severity: string
  summary: string
  emails: string[]
  enabled: boolean
  firing: boolean
  last_notified: string | null
}

export const fetchAlertRules = () => get<AlertRuleRow[]>("/alerts/rules")

export async function saveAlertAssignment(
  ruleId: string,
  body: { emails: string[]; enabled: boolean; cluster_id?: string; product?: string }
): Promise<void> {
  const res = await apiFetch(`/alerts/assignments/${encodeURIComponent(ruleId)}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  })
  if (!res.ok) throw new Error(await parseApiError(res))
}

export async function sendTestEmail(to: string): Promise<void> {
  const res = await apiFetch(`/alerts/test-email?to=${encodeURIComponent(to)}`, { method: "POST" })
  if (!res.ok) throw new Error(await parseApiError(res))
}

export type AppSettingsSnapshot = {
  env_file: string
  inference: {
    base_url: string
    model: string
    api_key_configured: boolean
    api_key_hint: string
    overview_cache_sec: number
    headroom_proxy_default: string
    notes: string[]
  }
  cloudera: {
    console_base_url: string
    engines_path: string
    fleet_console_url: string
    registered_engines: number
    knox_jwt_configured: boolean
    hadoop_jwt_configured: boolean
    knox_bearer_token_file: string
    knox_scrape_targets: number
    knox_note: string
  }
  telemetry: {
    prometheus_url: string
    scrape_host: string
    grafana_url: string
    otel_logs_endpoint: string
    opensearch_url: string
    collector_interval_sec: number
    file_sd_dir: string
  }
  alerts: {
    smtp_host: string
    smtp_port: number
    smtp_from: string
    smtp_user_configured: boolean
    smtp_password_configured: boolean
    smtp_start_tls: boolean
    smtp_use_tls: boolean
    default_recipients: string
    eval_interval_sec: number
  }
  paths: {
    config_dir: string
    kubeconfig_dir: string
    secrets_dir: string
  }
}

export type SettingsPatch = {
  inference?: {
    base_url?: string
    model?: string
    api_key?: string
    overview_cache_sec?: number
  }
  cloudera?: {
    console_base_url?: string
    engines_path?: string
    knox_jwt?: string
    hadoop_jwt?: string
  }
  telemetry?: {
    prometheus_url?: string
    scrape_host?: string
    grafana_url?: string
    otel_logs_endpoint?: string
    opensearch_url?: string
    collector_interval_sec?: number
  }
  alerts?: {
    smtp_host?: string
    smtp_port?: number
    smtp_from?: string
    smtp_user?: string
    smtp_password?: string
    smtp_start_tls?: boolean
    smtp_use_tls?: boolean
    default_recipients?: string
    eval_interval_sec?: number
  }
}

export type InferenceProbeResult = {
  ok: boolean
  message: string
  model?: string
  sample?: string
}

export const fetchAppSettings = () => get<AppSettingsSnapshot>("/settings")

export async function patchAppSettings(body: SettingsPatch): Promise<AppSettingsSnapshot> {
  const res = await apiFetch("/settings", {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  })
  if (!res.ok) throw new Error(await parseApiError(res))
  return res.json() as Promise<AppSettingsSnapshot>
}

export async function testInferenceEndpoint(): Promise<InferenceProbeResult> {
  const res = await apiFetch("/settings/test-inference", { method: "POST" })
  if (!res.ok) throw new Error(await parseApiError(res))
  return res.json() as Promise<InferenceProbeResult>
}
