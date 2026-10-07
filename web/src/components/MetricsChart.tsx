import { useQuery } from "@tanstack/react-query"
import { useCallback, useEffect, useId, useState, type KeyboardEvent } from "react"
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts"
import { fetchMetricRange } from "../api"

type MetricsChartProps = {
  title: string
  query: string
  clusterId?: string
  hours?: number
  refetchMs?: number
  valueDecimals?: number
  /** When true, chart body starts collapsed (click header to expand). */
  defaultCollapsed?: boolean
}

function parseSeries(data: unknown, valueDecimals?: number): Array<{ t: string; v: number }> {
  const payload = data as {
    data?: { result?: Array<{ values?: Array<[number, string]> }> }
  }
  const values = payload.data?.result?.[0]?.values ?? []
  return values.map(([ts, val]) => {
    let v = Number.parseFloat(val)
    if (valueDecimals != null && Number.isFinite(v)) {
      const factor = 10 ** valueDecimals
      v = Math.round(v * factor) / factor
    }
    return {
      t: new Date(ts * 1000).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
      v,
    }
  })
}

type ChartBodyProps = {
  points: Array<{ t: string; v: number }>
  formatTick: (n: number) => string
  height: number
  isError: boolean
  isLoading: boolean
  hasData: boolean
}

function ChartBody({
  points,
  formatTick,
  height,
  isError,
  isLoading,
  hasData,
}: ChartBodyProps) {
  return (
    <div style={{ height, padding: "0.5rem 0.75rem 1rem" }}>
      {isError && (
        <div className="empty-state" style={{ padding: "2rem 0" }}>
          Prometheus unavailable — start Docker hub or check CPW_PROMETHEUS_URL.
        </div>
      )}
      {!isError && !hasData && !isLoading && (
        <div className="empty-state" style={{ padding: "2rem 0" }}>
          No series yet (collectors / VPN may be required).
        </div>
      )}
      {hasData && (
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={points}>
            <CartesianGrid stroke="#e2e8f0" strokeDasharray="3 3" />
            <XAxis dataKey="t" tick={{ fontSize: 10 }} stroke="#94a3b8" />
            <YAxis
              tick={{ fontSize: 10 }}
              stroke="#94a3b8"
              width={48}
              tickFormatter={formatTick}
            />
            <Tooltip contentStyle={{ fontSize: 12 }} formatter={(v: number) => formatTick(v)} />
            <Line type="monotone" dataKey="v" stroke="#0050a0" strokeWidth={2} dot={false} />
          </LineChart>
        </ResponsiveContainer>
      )}
    </div>
  )
}

export function MetricsChart({
  title,
  query: initialQuery,
  clusterId,
  hours = 6,
  refetchMs = 5_000,
  valueDecimals,
  defaultCollapsed = false,
}: MetricsChartProps) {
  const [activeQuery, setActiveQuery] = useState(initialQuery)
  const [isEditing, setIsEditing] = useState(false)
  const [isMaximized, setIsMaximized] = useState(false)
  const [isCollapsed, setIsCollapsed] = useState(defaultCollapsed)
  const [draftQuery, setDraftQuery] = useState(initialQuery)
  const editFieldId = useId()

  useEffect(() => {
    setActiveQuery(initialQuery)
    setDraftQuery(initialQuery)
  }, [initialQuery])

  useEffect(() => {
    if (!isMaximized) return
    const prev = document.body.style.overflow
    document.body.style.overflow = "hidden"
    return () => {
      document.body.style.overflow = prev
    }
  }, [isMaximized])

  const range = useQuery({
    queryKey: ["metrics-range", activeQuery, clusterId, hours],
    queryFn: () => fetchMetricRange(activeQuery, { cluster: clusterId, hours }),
    refetchInterval: refetchMs,
    refetchIntervalInBackground: true,
    retry: 1,
  })

  const points = range.data ? parseSeries(range.data, valueDecimals) : []
  const formatTick = (n: number) =>
    valueDecimals != null && Number.isFinite(n) ? n.toFixed(valueDecimals) : String(n)
  const hasData = points.length > 0
  const latestValue = hasData ? points[points.length - 1]?.v : null

  const handleApplyQuery = useCallback(() => {
    setActiveQuery(draftQuery.trim() || initialQuery)
    setIsEditing(false)
  }, [draftQuery, initialQuery])

  const handleCancelEdit = useCallback(() => {
    setDraftQuery(activeQuery)
    setIsEditing(false)
  }, [activeQuery])

  const handleKeyDown = useCallback(
    (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        if (isEditing) handleCancelEdit()
        else setIsMaximized(false)
      }
    },
    [handleCancelEdit, isEditing]
  )

  const handleToggleCollapsed = useCallback(() => {
    setIsCollapsed((prev) => {
      const next = !prev
      if (next) setIsEditing(false)
      return next
    })
  }, [])

  const toolbar = (
    <div className="metrics-chart-toolbar" onClick={(e) => e.stopPropagation()}>
      {!isCollapsed && (
        <>
          <button
            type="button"
            className="link-btn metrics-chart-action"
            onClick={() => setIsMaximized(true)}
            aria-label={`Maximize chart ${title}`}
          >
            Maximize
          </button>
          <button
            type="button"
            className={`link-btn metrics-chart-action${isEditing ? " metrics-chart-action--active" : ""}`}
            onClick={() => {
              setDraftQuery(activeQuery)
              setIsEditing((v) => !v)
            }}
            aria-expanded={isEditing}
            aria-controls={editFieldId}
          >
            {isEditing ? "Hide formula" : "Edit"}
          </button>
        </>
      )}
      <button
        type="button"
        className="link-btn metrics-chart-action"
        onClick={handleToggleCollapsed}
        aria-expanded={!isCollapsed}
        aria-label={isCollapsed ? `Expand chart ${title}` : `Collapse chart ${title}`}
      >
        {isCollapsed ? "Expand" : "Collapse"}
      </button>
    </div>
  )

  const formulaBlock = isEditing ? (
    <div className="metrics-chart-formula" id={editFieldId}>
      <label className="metrics-chart-formula-label" htmlFor={`${editFieldId}-input`}>
        PromQL
      </label>
      <textarea
        id={`${editFieldId}-input`}
        className="metrics-chart-formula-input mono"
        value={draftQuery}
        rows={3}
        onChange={(e) => setDraftQuery(e.target.value)}
        spellCheck={false}
      />
      <div className="metrics-chart-formula-actions">
        <button type="button" className="link-btn" onClick={handleApplyQuery}>
          Apply
        </button>
        <button type="button" className="link-btn" onClick={handleCancelEdit}>
          Cancel
        </button>
      </div>
    </div>
  ) : null

  const header = (
    <div className="panel-header metrics-chart-header">
      <button
        type="button"
        className="metrics-chart-header-toggle"
        onClick={handleToggleCollapsed}
        aria-expanded={!isCollapsed}
      >
        <span className="metrics-chart-chevron" aria-hidden>
          {isCollapsed ? "▸" : "▾"}
        </span>
        <h3 className="panel-title metrics-chart-title">{title}</h3>
        {isCollapsed && latestValue != null && Number.isFinite(latestValue) && (
          <span className="metrics-chart-latest">{formatTick(latestValue)}</span>
        )}
        {isCollapsed && range.isLoading && (
          <span className="metrics-chart-latest metrics-chart-latest--muted">Loading…</span>
        )}
      </button>
      {toolbar}
    </div>
  )

  const chartPanel = (compact: boolean) => (
    <>
      {header}
      {!isCollapsed && formulaBlock}
      {!isCollapsed && (
        <ChartBody
          points={points}
          formatTick={formatTick}
          height={compact ? 220 : 420}
          isError={range.isError}
          isLoading={range.isLoading}
          hasData={hasData}
        />
      )}
    </>
  )

  return (
    <>
      <div
        className={`panel metrics-chart-panel${isCollapsed ? " metrics-chart-panel--collapsed" : ""}`}
        style={{ marginBottom: "0.75rem" }}
      >
        {chartPanel(true)}
      </div>

      {isMaximized && (
        <div
          className="metrics-chart-overlay"
          role="dialog"
          aria-modal="true"
          aria-label={`${title} chart`}
          onKeyDown={handleKeyDown}
        >
          <button
            type="button"
            className="metrics-chart-overlay-backdrop"
            aria-label="Close maximized chart"
            onClick={() => setIsMaximized(false)}
          />
          <div className="panel metrics-chart-overlay-panel">
            <div className="panel-header metrics-chart-header">
              <h3 className="panel-title">{title}</h3>
              <div className="metrics-chart-toolbar">
                <button
                  type="button"
                  className="link-btn metrics-chart-action"
                  onClick={() => {
                    setDraftQuery(activeQuery)
                    setIsEditing(true)
                  }}
                >
                  Edit formula
                </button>
                <button
                  type="button"
                  className="link-btn metrics-chart-action"
                  onClick={() => setIsMaximized(false)}
                >
                  Close
                </button>
              </div>
            </div>
            {formulaBlock ?? (
              <p className="metrics-chart-formula-hint">
                Use <strong>Edit formula</strong> to view or change PromQL for this chart.
              </p>
            )}
            <ChartBody
              points={points}
              formatTick={formatTick}
              height={480}
              isError={range.isError}
              isLoading={range.isLoading}
              hasData={hasData}
            />
          </div>
        </div>
      )}
    </>
  )
}
