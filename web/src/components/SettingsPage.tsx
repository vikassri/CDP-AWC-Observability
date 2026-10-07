import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { useEffect, useState, type ReactNode } from "react"
import {
  fetchAppSettings,
  patchAppSettings,
  testInferenceEndpoint,
  type AppSettingsSnapshot,
  type SettingsPatch,
} from "../api"
import { StatusPill } from "./StatusPill"

type FormState = {
  inferenceBaseUrl: string
  inferenceModel: string
  inferenceApiKey: string
  overviewCacheSec: string
  awcConsoleUrl: string
  awcEnginesPath: string
  knoxJwt: string
  hadoopJwt: string
  prometheusUrl: string
  scrapeHost: string
  grafanaUrl: string
  otelEndpoint: string
  opensearchUrl: string
  collectorInterval: string
  smtpHost: string
  smtpPort: string
  smtpFrom: string
  smtpUser: string
  smtpPassword: string
  smtpStartTls: boolean
  smtpUseTls: boolean
  alertRecipients: string
  alertEvalSec: string
}

function snapshotToForm(data: AppSettingsSnapshot): FormState {
  return {
    inferenceBaseUrl: data.inference.base_url,
    inferenceModel: data.inference.model,
    inferenceApiKey: "",
    overviewCacheSec: String(data.inference.overview_cache_sec),
    awcConsoleUrl: data.cloudera.console_base_url,
    awcEnginesPath: data.cloudera.engines_path,
    knoxJwt: "",
    hadoopJwt: "",
    prometheusUrl: data.telemetry.prometheus_url,
    scrapeHost: data.telemetry.scrape_host,
    grafanaUrl: data.telemetry.grafana_url,
    otelEndpoint: data.telemetry.otel_logs_endpoint,
    opensearchUrl: data.telemetry.opensearch_url,
    collectorInterval: String(data.telemetry.collector_interval_sec),
    smtpHost: data.alerts.smtp_host,
    smtpPort: String(data.alerts.smtp_port),
    smtpFrom: data.alerts.smtp_from,
    smtpUser: "",
    smtpPassword: "",
    smtpStartTls: data.alerts.smtp_start_tls,
    smtpUseTls: data.alerts.smtp_use_tls,
    alertRecipients: data.alerts.default_recipients,
    alertEvalSec: String(data.alerts.eval_interval_sec),
  }
}

function formToPatch(form: FormState): SettingsPatch {
  return {
    inference: {
      base_url: form.inferenceBaseUrl.trim(),
      model: form.inferenceModel.trim(),
      overview_cache_sec: Number(form.overviewCacheSec) || undefined,
      ...(form.inferenceApiKey.trim() ? { api_key: form.inferenceApiKey.trim() } : {}),
    },
    cloudera: {
      console_base_url: form.awcConsoleUrl.trim(),
      engines_path: form.awcEnginesPath.trim(),
      ...(form.knoxJwt.trim() ? { knox_jwt: form.knoxJwt.trim() } : {}),
      ...(form.hadoopJwt.trim() ? { hadoop_jwt: form.hadoopJwt.trim() } : {}),
    },
    telemetry: {
      prometheus_url: form.prometheusUrl.trim(),
      scrape_host: form.scrapeHost.trim(),
      grafana_url: form.grafanaUrl.trim(),
      otel_logs_endpoint: form.otelEndpoint.trim(),
      opensearch_url: form.opensearchUrl.trim(),
      collector_interval_sec: Number(form.collectorInterval) || undefined,
    },
    alerts: {
      smtp_host: form.smtpHost.trim(),
      smtp_port: Number(form.smtpPort) || undefined,
      smtp_from: form.smtpFrom.trim(),
      smtp_start_tls: form.smtpStartTls,
      smtp_use_tls: form.smtpUseTls,
      default_recipients: form.alertRecipients.trim(),
      eval_interval_sec: Number(form.alertEvalSec) || undefined,
      ...(form.smtpUser.trim() ? { smtp_user: form.smtpUser.trim() } : {}),
      ...(form.smtpPassword.trim() ? { smtp_password: form.smtpPassword.trim() } : {}),
    },
  }
}

function shortPath(path: string): string {
  const parts = path.split("/").filter(Boolean)
  if (parts.length <= 3) return path
  return `…/${parts.slice(-3).join("/")}`
}

function SettingsField({
  label,
  hint,
  wide,
  children,
}: {
  label: string
  hint?: string
  wide?: boolean
  children: ReactNode
}) {
  return (
    <label className={`settings-field${wide ? " settings-field--wide" : ""}`}>
      <span className="settings-label">{label}</span>
      {children}
      {hint ? <span className="settings-hint">{hint}</span> : null}
    </label>
  )
}

function SettingsSection({
  title,
  actions,
  children,
  footer,
}: {
  title: string
  actions?: ReactNode
  children: ReactNode
  footer?: ReactNode
}) {
  return (
    <div className="panel settings-section">
      <div className="panel-header">
        <h3 className="panel-title">{title}</h3>
        {actions ? <div className="settings-section-actions">{actions}</div> : null}
      </div>
      <div className="settings-panel-body">{children}</div>
      {footer ? <div className="settings-section-footer">{footer}</div> : null}
    </div>
  )
}

export function SettingsPage() {
  const queryClient = useQueryClient()
  const settings = useQuery({
    queryKey: ["app-settings"],
    queryFn: fetchAppSettings,
  })

  const [form, setForm] = useState<FormState | null>(null)
  const [saveMessage, setSaveMessage] = useState<string | null>(null)

  useEffect(() => {
    if (settings.data && !form) {
      setForm(snapshotToForm(settings.data))
    }
  }, [settings.data, form])

  const save = useMutation({
    mutationFn: () => patchAppSettings(formToPatch(form!)),
    onSuccess: (data) => {
      queryClient.setQueryData(["app-settings"], data)
      setForm(snapshotToForm(data))
      setSaveMessage("Settings saved.")
    },
  })

  const probe = useMutation({
    mutationFn: testInferenceEndpoint,
  })

  const handleChange = <K extends keyof FormState>(key: K, value: FormState[K]) => {
    setForm((prev) => (prev ? { ...prev, [key]: value } : prev))
    setSaveMessage(null)
  }

  if (settings.isLoading || !form) {
    return (
      <div className="panel">
        <div className="empty-state">Loading settings…</div>
      </div>
    )
  }

  if (settings.isError) {
    return (
      <div className="panel">
        <div className="empty-state">Could not load settings from the API.</div>
      </div>
    )
  }

  const snap = settings.data!

  return (
    <section className="settings-page">
      <div className="panel settings-hero">
        <div className="settings-hero-inner">
          <div>
            <h2 className="settings-hero-title">Platform settings</h2>
            <p className="settings-intro">
              Cloudera AWC, Knox JWT, Prometheus hub, SMTP alerts, and OmniRoute LLM inference.
              Changes write to{" "}
              <code className="settings-path mono" title={snap.env_file}>
                {shortPath(snap.env_file)}
              </code>{" "}
              and{" "}
              <code className="settings-path mono">config/awc.yaml</code>.
            </p>
          </div>
          <div className="settings-hero-actions">
            <StatusPill variant="unknown" label="Local control plane" />
            <button
              type="button"
              className="cpw-btn cpw-btn--primary"
              disabled={save.isPending}
              onClick={() => save.mutate()}
            >
              {save.isPending ? "Saving…" : "Save all"}
            </button>
          </div>
        </div>
        {(saveMessage || save.isError || probe.data) && (
          <div className="settings-banner">
            {saveMessage && <span className="settings-ok">{saveMessage}</span>}
            {save.isError && <span className="settings-err">Save failed — check API logs.</span>}
            {probe.data && (
              <span className={probe.data.ok ? "settings-ok" : "settings-err"}>
                Inference: {probe.data.message}
                {probe.data.sample ? ` (“${probe.data.sample}”)` : ""}
              </span>
            )}
          </div>
        )}
      </div>

      <SettingsSection
        title="AI inference & recommendations"
        actions={
          <>
            <StatusPill
              variant={snap.inference.api_key_configured ? "ok" : "warn"}
              label={snap.inference.api_key_configured ? "API key set" : "No API key"}
            />
            <button
              type="button"
              className="cpw-btn cpw-btn--secondary"
              disabled={probe.isPending}
              onClick={() => probe.mutate()}
            >
              {probe.isPending ? "Testing…" : "Test inference"}
            </button>
          </>
        }
        footer={
          <ul className="settings-notes">
            {snap.inference.notes.map((note) => (
              <li key={note}>{note}</li>
            ))}
          </ul>
        }
      >
        <div className="settings-grid">
          <SettingsField
            label="LLM base URL"
            wide
            hint={`Example gateway: ${snap.inference.gateway_example}`}
          >
            <input
              className="settings-input"
              value={form.inferenceBaseUrl}
              onChange={(e) => handleChange("inferenceBaseUrl", e.target.value)}
            />
          </SettingsField>
          <SettingsField label="Model">
            <input
              className="settings-input"
              value={form.inferenceModel}
              onChange={(e) => handleChange("inferenceModel", e.target.value)}
            />
          </SettingsField>
          <SettingsField label="Overview cache (sec)">
            <input
              className="settings-input"
              inputMode="decimal"
              value={form.overviewCacheSec}
              onChange={(e) => handleChange("overviewCacheSec", e.target.value)}
            />
          </SettingsField>
          <SettingsField
            label="API key"
            wide
            hint={
              snap.inference.api_key_configured
                ? `Configured (${snap.inference.api_key_hint}). Leave blank to keep.`
                : "Required for most OpenAI-compatible providers."
            }
          >
            <input
              className="settings-input"
              type="password"
              autoComplete="off"
              placeholder={snap.inference.api_key_configured ? "••••••••" : ""}
              value={form.inferenceApiKey}
              onChange={(e) => handleChange("inferenceApiKey", e.target.value)}
            />
          </SettingsField>
        </div>
      </SettingsSection>

      <SettingsSection
        title="Cloudera AWC & Knox"
        actions={
          <a className="link-btn" href={snap.cloudera.fleet_console_url} target="_blank" rel="noreferrer">
            Fleet console →
          </a>
        }
        footer={
          <p className="settings-meta">
            {snap.cloudera.registered_engines} engines ·{" "}
            <span className="mono">{snap.paths.config_dir}/clusters.yaml</span>
          </p>
        }
      >
        <div className="settings-grid">
          <SettingsField label="AWC console base URL" wide>
            <input
              className="settings-input"
              value={form.awcConsoleUrl}
              onChange={(e) => handleChange("awcConsoleUrl", e.target.value)}
            />
          </SettingsField>
          <SettingsField label="Engines path" wide>
            <input
              className="settings-input"
              value={form.awcEnginesPath}
              onChange={(e) => handleChange("awcEnginesPath", e.target.value)}
            />
          </SettingsField>
          <SettingsField
            label="Knox JWT"
            wide
            hint={
              snap.cloudera.knox_jwt_configured
                ? "Configured — paste to rotate."
                : "Optional HTTPS NiFi scrape via Knox."
            }
          >
            <input
              className="settings-input"
              type="password"
              autoComplete="off"
              value={form.knoxJwt}
              onChange={(e) => handleChange("knoxJwt", e.target.value)}
            />
          </SettingsField>
          <SettingsField
            label="Hadoop JWT"
            hint={snap.cloudera.hadoop_jwt_configured ? "Configured" : "Optional"}
          >
            <input
              className="settings-input"
              type="password"
              autoComplete="off"
              value={form.hadoopJwt}
              onChange={(e) => handleChange("hadoopJwt", e.target.value)}
            />
          </SettingsField>
        </div>
        <div className="settings-callout">
          {snap.cloudera.knox_note} Knox targets: {snap.cloudera.knox_scrape_targets}. Token file:{" "}
          <span className="mono" title={snap.cloudera.knox_bearer_token_file}>
            {shortPath(snap.cloudera.knox_bearer_token_file)}
          </span>
        </div>
      </SettingsSection>

      <SettingsSection
        title="Telemetry hub"
        footer={
          <p className="settings-meta mono" title={snap.telemetry.file_sd_dir}>
            file_sd: {shortPath(snap.telemetry.file_sd_dir)}
          </p>
        }
      >
        <div className="settings-grid">
          <SettingsField label="Prometheus URL" wide>
            <input
              className="settings-input"
              value={form.prometheusUrl}
              onChange={(e) => handleChange("prometheusUrl", e.target.value)}
            />
          </SettingsField>
          <SettingsField
            label="Scrape host"
            hint="host.docker.internal on Mac when Prom runs in Docker"
          >
            <input
              className="settings-input"
              value={form.scrapeHost}
              onChange={(e) => handleChange("scrapeHost", e.target.value)}
            />
          </SettingsField>
          <SettingsField label="Grafana URL" wide>
            <input
              className="settings-input"
              value={form.grafanaUrl}
              onChange={(e) => handleChange("grafanaUrl", e.target.value)}
            />
          </SettingsField>
          <SettingsField label="OTel logs endpoint" wide>
            <input
              className="settings-input"
              value={form.otelEndpoint}
              onChange={(e) => handleChange("otelEndpoint", e.target.value)}
            />
          </SettingsField>
          <SettingsField label="OpenSearch URL" wide>
            <input
              className="settings-input"
              value={form.opensearchUrl}
              onChange={(e) => handleChange("opensearchUrl", e.target.value)}
            />
          </SettingsField>
          <SettingsField label="Collector interval (sec)">
            <input
              className="settings-input"
              inputMode="numeric"
              value={form.collectorInterval}
              onChange={(e) => handleChange("collectorInterval", e.target.value)}
            />
          </SettingsField>
        </div>
      </SettingsSection>

      <SettingsSection title="Alert email (SMTP)">
        <div className="settings-grid">
          <SettingsField label="SMTP host">
            <input
              className="settings-input"
              value={form.smtpHost}
              onChange={(e) => handleChange("smtpHost", e.target.value)}
            />
          </SettingsField>
          <SettingsField label="Port">
            <input
              className="settings-input"
              inputMode="numeric"
              value={form.smtpPort}
              onChange={(e) => handleChange("smtpPort", e.target.value)}
            />
          </SettingsField>
          <SettingsField label="From address" wide>
            <input
              className="settings-input"
              value={form.smtpFrom}
              onChange={(e) => handleChange("smtpFrom", e.target.value)}
            />
          </SettingsField>
          <SettingsField
            label="SMTP user"
            hint={snap.alerts.smtp_user_configured ? "Leave blank to keep current." : undefined}
          >
            <input
              className="settings-input"
              value={form.smtpUser}
              onChange={(e) => handleChange("smtpUser", e.target.value)}
            />
          </SettingsField>
          <SettingsField
            label="SMTP password"
            hint={snap.alerts.smtp_password_configured ? "Leave blank to keep current." : undefined}
          >
            <input
              className="settings-input"
              type="password"
              autoComplete="off"
              value={form.smtpPassword}
              onChange={(e) => handleChange("smtpPassword", e.target.value)}
            />
          </SettingsField>
          <SettingsField label="Default recipients" wide>
            <input
              className="settings-input"
              value={form.alertRecipients}
              onChange={(e) => handleChange("alertRecipients", e.target.value)}
              placeholder="ops@example.com, sre@example.com"
            />
          </SettingsField>
          <SettingsField label="Eval interval (sec)">
            <input
              className="settings-input"
              inputMode="numeric"
              value={form.alertEvalSec}
              onChange={(e) => handleChange("alertEvalSec", e.target.value)}
            />
          </SettingsField>
          <div className="settings-check-row">
            <label className="settings-check">
              <input
                type="checkbox"
                checked={form.smtpStartTls}
                onChange={(e) => handleChange("smtpStartTls", e.target.checked)}
              />
              STARTTLS
            </label>
            <label className="settings-check">
              <input
                type="checkbox"
                checked={form.smtpUseTls}
                onChange={(e) => handleChange("smtpUseTls", e.target.checked)}
              />
              Use TLS
            </label>
          </div>
        </div>
      </SettingsSection>

      <p className="settings-footnote">
        Kubeconfigs: <span className="mono">{shortPath(snap.paths.kubeconfig_dir)}</span> · Secrets:{" "}
        <span className="mono">{shortPath(snap.paths.secrets_dir)}</span>
      </p>
    </section>
  )
}
