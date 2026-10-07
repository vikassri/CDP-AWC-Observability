import type { JobStatusItem } from "../api"
import { formatPercent } from "../utils/formatMetrics"
import type { JobStatusTileTone, JobStatusTileView } from "./fleetMetricTiles"

export function formatJobStatusValue(
  value: number | null | undefined,
  unit?: string | null
): string {
  if (value === null || value === undefined) return "—"
  if (unit === "percent") return formatPercent(value, 2)
  if (unit === "bytes") {
    const gib = value / 1024 ** 3
    if (gib >= 1) return `${gib.toFixed(2)} GiB`
    return `${(value / (1024 * 1024)).toFixed(0)} MiB`
  }
  return Number.isInteger(value) ? String(value) : value.toFixed(1)
}

type JobStatusTilesProps = {
  items: JobStatusItem[] | JobStatusTileView[]
  emptyMessage?: string
  compact?: boolean
  onTileNavigate?: (product: string, namespace?: string) => void
}

function isTileView(item: JobStatusItem | JobStatusTileView): item is JobStatusTileView {
  return "tone" in item || "linkProduct" in item
}

export function JobStatusTiles({
  items,
  emptyMessage = "No job status metrics yet. Start Prometheus hub and status exporters (API restart).",
  compact = false,
  onTileNavigate,
}: JobStatusTilesProps) {
  return (
    <div className={`job-status-grid${compact ? " job-status-grid--compact" : ""}`}>
      {items.map((item) => {
        const view = isTileView(item) ? item : undefined
        const tone: JobStatusTileTone = view?.tone ?? "neutral"
        const canLink = Boolean(view?.linkProduct && onTileNavigate)
        const className = `job-status-tile job-status-tile--${tone}${canLink ? " job-status-tile--link" : ""}`

        const inner = (
          <>
            <div className="job-status-value">{formatJobStatusValue(item.value, item.unit)}</div>
            <div className="job-status-label">{item.label}</div>
            {item.error ? (
              <div className="job-status-error" title={item.error}>
                Prom query failed
              </div>
            ) : null}
          </>
        )

        if (canLink && view?.linkProduct) {
          return (
            <button
              key={item.key}
              type="button"
              className={className}
              onClick={() => onTileNavigate!(view.linkProduct!, view.linkNamespace)}
              aria-label={`Open ${view.linkProduct} — ${item.label}`}
            >
              {inner}
            </button>
          )
        }

        return (
          <div key={item.key} className={className}>
            {inner}
          </div>
        )
      })}
      {!items.length && (
        <div className="empty-state" style={{ gridColumn: "1 / -1" }}>
          {emptyMessage}
        </div>
      )}
    </div>
  )
}
