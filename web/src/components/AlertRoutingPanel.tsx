import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { useState } from "react"
import {
  fetchAlertRules,
  saveAlertAssignment,
  sendTestEmail,
  type AlertRuleRow,
} from "../api"
import { StatusPill } from "./StatusPill"

export function AlertRoutingPanel({ productFilter }: { productFilter?: string }) {
  const queryClient = useQueryClient()
  const [testEmail, setTestEmail] = useState("")
  const rules = useQuery({ queryKey: ["alert-rules"], queryFn: fetchAlertRules, refetchInterval: 30_000 })

  const saveMutation = useMutation({
    mutationFn: (payload: { ruleId: string; emails: string[]; enabled: boolean }) =>
      saveAlertAssignment(payload.ruleId, {
        emails: payload.emails,
        enabled: payload.enabled,
      }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["alert-rules"] }),
  })

  const testMutation = useMutation({
    mutationFn: (to: string) => sendTestEmail(to),
  })

  const visible = (rules.data ?? []).filter(
    (r) => !productFilter || r.product === productFilter
  )

  return (
    <div className="panel">
      <div className="panel-header">
        <h2 className="panel-title">Alert routing (SMTP)</h2>
        <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
          <input
            type="email"
            placeholder="test@company.com"
            value={testEmail}
            onChange={(e) => setTestEmail(e.target.value)}
            style={{ fontSize: 12, padding: "0.35rem 0.5rem", border: "1px solid var(--border)", borderRadius: 4 }}
          />
          <button
            type="button"
            className="nav-item active"
            style={{ padding: "0.35rem 0.65rem", fontSize: 12 }}
            onClick={() => testEmail && testMutation.mutate(testEmail)}
          >
            Test SMTP
          </button>
        </div>
      </div>
      <div className="panel-body">
        <table className="data-table">
          <thead>
            <tr>
              <th>Alert</th>
              <th>Severity</th>
              <th>State</th>
              <th>Recipients</th>
              <th>Enabled</th>
            </tr>
          </thead>
          <tbody>
            {visible.map((rule) => (
              <AlertRuleRow key={rule.rule_id} rule={rule} onSave={saveMutation.mutate} />
            ))}
          </tbody>
        </table>
        {!visible.length && (
          <div className="empty-state">No alert rules for this product.</div>
        )}
        {testMutation.isSuccess && (
          <p style={{ padding: "0.5rem 1rem", fontSize: 12, color: "var(--ok)" }}>
            Test message queued to SMTP.
          </p>
        )}
        {testMutation.isError && (
          <p style={{ padding: "0.5rem 1rem", fontSize: 12, color: "var(--crit)" }}>
            SMTP failed — check Mailpit or SMTP_* in .env
          </p>
        )}
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
    const list = emails
      .split(",")
      .map((e) => e.trim())
      .filter(Boolean)
    onSave({ ruleId: rule.rule_id, emails: list, enabled })
  }

  return (
    <tr>
      <td>
        <strong>{rule.alert}</strong>
        <div className="mono" style={{ fontSize: 11, color: "var(--text-muted)" }}>
          {rule.expr}
        </div>
      </td>
      <td>
        <span className="tag">{rule.severity}</span>
      </td>
      <td>
        <StatusPill variant={rule.firing ? "crit" : "ok"} label={rule.firing ? "Firing" : "Normal"} />
      </td>
      <td>
        <input
          type="text"
          value={emails}
          onChange={(e) => setEmails(e.target.value)}
          onBlur={handleBlur}
          placeholder="ops@company.com, oncall@company.com"
          style={{
            width: "100%",
            fontSize: 12,
            padding: "0.35rem 0.5rem",
            border: "1px solid var(--border)",
            borderRadius: 4,
          }}
        />
      </td>
      <td>
        <input
          type="checkbox"
          checked={enabled}
          onChange={(e) => {
            setEnabled(e.target.checked)
            const list = emails
              .split(",")
              .map((x) => x.trim())
              .filter(Boolean)
            onSave({ ruleId: rule.rule_id, emails: list, enabled: e.target.checked })
          }}
          aria-label={`Enable ${rule.alert}`}
        />
      </td>
    </tr>
  )
}
