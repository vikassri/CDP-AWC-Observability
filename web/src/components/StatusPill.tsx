type StatusPillProps = {
  variant: "ok" | "crit" | "warn" | "unknown"
  label: string
}

export function StatusPill({ variant, label }: StatusPillProps) {
  return <span className={`status-pill status-${variant}`}>{label}</span>
}
