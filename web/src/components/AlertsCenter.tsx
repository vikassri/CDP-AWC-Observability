import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { useState } from "react"
import {
  createAlertRule,
  fetchAlertRules,
  saveAlertAssignment,
  sendTestEmail,
  type AlertRuleRow,
} from "../api"
import { REFETCH_FAST_MS } from "../constants/refetch"
import { StatusPill } from "./StatusPill"

const PRODUCTS = ["nifi", "spark", "trino", "flink", "airflow"] as const

export function AlertsCenter() {
  const queryClient = useQueryClient()
  const [filter, setFilter] = useState<string>("")
  const [showAdd, setShowAdd] = useState(false)
  const [testEmail, setTestEmail] = useState("")
  const [form, setForm] = useState({
    alert: "",
    expr: "",
    product: "nifi",
    severity: "warning",
    summary: "",
    for_duration: "5m",
    emails: "",
  })

  const rules = useQuery({
    queryKey: ["alert-rules"],
    queryFn: fetchAlertRules,
    refetchInterval: REFETCH_FAST_MS,
    refetchIntervalInBackground: true,
  })

  const saveMutation = useMutation({
    mutationFn: (payload: { ruleId: string; emails: string[]; enabled: boolean }) =>
      saveAlertAssignment(payload.ruleId, {
        emails: payload.emails,
        enabled: payload.enabled,
      }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["alert-rules"] }),
  })

  const createMutation = useMutation({
    mutationFn: () =>
      createAlertRule({
        alert: form.alert,
        expr: form.expr,
        product: form.product,
        severity: form.severity,
        summary: form.summary,
        for_duration: form.for_duration,
        emails: form.emails
          .split(",")
          .map((e) => e.trim())
          .filter(Boolean),
        enabled: true,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["alert-rules"] })
      setShowAdd(false)
      setForm({
        alert: "",
        expr: "",
        product: "nifi",
        severity: "warning",
        summary: "",
        for_duration: "5m",
        emails: "",
      })
    },
  })

  const testMutation = useMutation({
    mutationFn: (to: string) => sendTestEmail(to),
  })

  const visible = (rules.data ?? []).filter((r) => !filter || r.product === filter)
  const firingCount = visible.filter((r) => r.firing).length

  return (
    <div className="panel">
      <div className="panel-header">
        <h2 className="panel-title">Alerts</h2>
        <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
          <StatusPill
            variant={firingCount ? "crit" : "ok"}
            label={firingCount ? `${firingCount} firing` : "Nominal"}
          />
          <button
            type="button"
            className="nav-item active"
            style={{ padding: "0.35rem 0.65rem", fontSize: 12 }}
            onClick={() => setShowAdd((v) => !v)}
          >
            Add alert
          </button>
          <input
            type="email"
            placeholder="test@company.com"
            value={testEmail}
            onChange={(e) => setTestEmail(e.target.value)}
            style={{
              fontSize: 12,
              padding: "0.35rem 0.5rem",
              border: "1px solid var(--border)",
              borderRadius: 4,
            }}
          />
          <button
            type="button"
            className="nav-item"
            style={{ padding: "0.35rem 0.65rem", fontSize: 12 }}
            onClick={() => testEmail && testMutation.mutate(testEmail)}
          >
            Test SMTP
          </button>
        </div>
      </div>

      <div className="tag-list" style={{ padding: "0.5rem 1rem 0" }}>
        <button
          type="button"
          className={`tag ${!filter ? "active" : ""}`}
          onClick={() => setFilter("")}
        >
          All
        </button>
        {PRODUCTS.map((p) => (
          <button
            key={p}
            type="button"
            className={`tag ${filter === p ? "active" : ""}`}
            onClick={() => setFilter(p)}
          >
            {p.toUpperCase()}
          </button>
        ))}
      </div>

      {showAdd && (
        <div className="panel-body" style={{ borderBottom: "1px solid var(--border)" }}>
          <div className="alert-add-grid">
            <label>
              Name
              <input
                value={form.alert}
                onChange={(e) => setForm({ ...form, alert: e.target.value })}
                placeholder="MyCustomAlert"
              />
            </label>
            <label>
              Product
              <select
                value={form.product}
                onChange={(e) => setForm({ ...form, product: e.target.value })}
              >
                {PRODUCTS.map((p) => (
                  <option key={p} value={p}>
                    {p}
                  </option>
                ))}
              </select>
            </label>
            <label className="alert-add-wide">
              PromQL expr
              <input
                value={form.expr}
                onChange={(e) => setForm({ ...form, expr: e.target.value })}
                placeholder='sum(nifi_amount_flowfiles_queued{cluster="cdf"}) > 1000'
              />
            </label>
            <label>
              Severity
              <select
                value={form.severity}
                onChange={(e) => setForm({ ...form, severity: e.target.value })}
              >
                <option value="info">info</option>
                <option value="warning">warning</option>
                <option value="critical">critical</option>
              </select>
            </label>
            <label>
              For
              <input
                value={form.for_duration}
                onChange={(e) => setForm({ ...form, for_duration: e.target.value })}
              />
            </label>
            <label className="alert-add-wide">
              Summary
              <input
                value={form.summary}
                onChange={(e) => setForm({ ...form, summary: e.target.value })}
              />
            </label>
            <label className="alert-add-wide">
              Recipients (comma-separated)
              <input
                value={form.emails}
                onChange={(e) => setForm({ ...form, emails: e.target.value })}
                placeholder="ops@example.com"
              />
            </label>
          </div>
          <button
            type="button"
            className="nav-item active"
            style={{ marginTop: 8, fontSize: 12 }}
            disabled={!form.alert || !form.expr || createMutation.isPending}
            onClick={() => createMutation.mutate()}
          >
            Save alert rule
          </button>
          {createMutation.isError && (
            <p style={{ color: "var(--crit)", fontSize: 12 }}>Failed to create rule.</p>
          )}
        </div>
      )}

      <div className="panel-body">
        <table className="data-table">
          <thead>
            <tr>
              <th>Alert</th>
              <th>Product</th>
              <th>Severity</th>
              <th>State</th>
              <th>Recipients</th>
              <th>On</th>
            </tr>
          </thead>
          <tbody>
            {visible.map((rule) => (
              <AlertRuleRow key={rule.rule_id} rule={rule} onSave={saveMutation.mutate} />
            ))}
          </tbody>
        </table>
        {!visible.length && <div className="empty-state">No alert rules match this filter.</div>}
      </div>
    </div>
  )
}

function AlertRuleRow({
  rule,
  onSave,
}: {
  rule: AlertRuleRow
  onSave: (p: { ruleId: string; emails: string[]; enabled: boolean }) => void
}) {
  const [emails, setEmails] = useState(rule.emails.join(", "))
  const [enabled, setEnabled] = useState(rule.enabled)

  const handleBlur = () => {
    onSave({
      ruleId: rule.rule_id,
      emails: emails
        .split(",")
        .map((e) => e.trim())
        .filter(Boolean),
      enabled,
    })
  }

  return (
    <tr>
      <td>
        <strong>{rule.alert}</strong>
        <div className="mono" style={{ fontSize: 11, color: "var(--text-muted)" }}>
          {rule.summary || rule.expr}
        </div>
      </td>
      <td>
        <span className="tag">{rule.product}</span>
      </td>
      <td>
        <span className="tag">{rule.severity}</span>
      </td>
      <td>
        <StatusPill variant={rule.firing ? "crit" : "ok"} label={rule.firing ? "Firing" : "Normal"} />
      </td>
      <td>
        <input
          value={emails}
          onChange={(e) => setEmails(e.target.value)}
          onBlur={handleBlur}
          style={{ width: "100%", fontSize: 12, padding: "0.25rem 0.35rem" }}
        />
      </td>
      <td>
        <input type="checkbox" checked={enabled} onChange={(e) => setEnabled(e.target.checked)} onBlur={handleBlur} />
      </td>
    </tr>
  )
}
