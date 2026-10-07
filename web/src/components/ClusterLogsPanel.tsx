import { useEffect, useMemo, useState } from "react"
import { createPortal } from "react-dom"
import { LogAiAnalyzeResult, useLogAiAnalyze, type LogAnalyzeContext } from "./LogAiAnalyze"

export type ClusterLogsPanelMode = "combined" | "bulletins-only" | "app-logs-only"

function combineLogStream(bulletins: string[], appLines: string[]): string[] {
  const out: string[] = []
  if (bulletins.length) {
    out.push("--- Bulletins (app-log) ---")
    out.push(...bulletins)
  }
  if (appLines.length) {
    if (out.length) out.push("")
    out.push("--- Recent app-log ---")
    out.push(...appLines)
  }
  return out
}

type ClusterLogsPanelProps = {
  title: string
  sourcesLabel: string
  bulletins?: string[]
  flagged: string[]
  previewLines: string[]
  allLines: string[]
  emptyMessage: string
  isLoading?: boolean
  compact?: boolean
  mode?: ClusterLogsPanelMode
  analyze?: LogAnalyzeContext
}

export function ClusterLogsPanel({
  title,
  sourcesLabel,
  bulletins = [],
  flagged,
  previewLines,
  allLines,
  emptyMessage,
  isLoading,
  compact,
  mode = "combined",
  analyze,
}: ClusterLogsPanelProps) {
  const [isMaximized, setIsMaximized] = useState(false)
  const aiAnalyze = useLogAiAnalyze(analyze)

  const showBulletins = mode === "combined" || mode === "bulletins-only"
  const showAppLogs = mode === "combined" || mode === "app-logs-only"

  const appPreview = showAppLogs ? previewLines : []
  const appAll = showAppLogs ? allLines : []

  const boxTitle =
    mode === "bulletins-only"
      ? "Bulletins"
      : mode === "app-logs-only"
        ? "App logs"
        : "Logs & bulletins"

  const previewText = useMemo(() => {
    if (mode === "bulletins-only") {
      if (bulletins.length) return bulletins.join("\n")
      if (isLoading) return "Loading bulletins…"
      return emptyMessage
    }
    if (mode === "app-logs-only") {
      if (appPreview.length) return appPreview.join("\n")
      if (isLoading) return "Loading logs…"
      return emptyMessage
    }
    const combined = combineLogStream(bulletins, previewLines)
    if (combined.length) return combined.join("\n")
    if (isLoading) return "Loading logs…"
    return emptyMessage
  }, [mode, bulletins, appPreview, previewLines, emptyMessage, isLoading])

  const fullText = useMemo(() => {
    if (mode === "bulletins-only") {
      return bulletins.length ? bulletins.join("\n") : previewText
    }
    if (mode === "app-logs-only") {
      return appAll.length ? appAll.join("\n") : previewText
    }
    const combined = combineLogStream(bulletins, allLines)
    if (combined.length) return combined.join("\n")
    return previewText
  }, [mode, bulletins, allLines, appAll, previewText])

  useEffect(() => {
    if (!isMaximized) return
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setIsMaximized(false)
    }
    window.addEventListener("keydown", onKey)
    return () => window.removeEventListener("keydown", onKey)
  }, [isMaximized])

  useEffect(() => {
    if (!isMaximized) return
    const prev = document.body.style.overflow
    document.body.style.overflow = "hidden"
    return () => {
      document.body.style.overflow = prev
    }
  }, [isMaximized])

  const logBlock = (
    <>
      {showBulletins && mode === "combined" && bulletins.length > 0 && (
        <div className="log-scan-flagged log-scan-bulletins">
          <strong>Bulletins (app-log)</strong>
          <ul className="detail-log-list">
            {bulletins.map((line, i) => (
              <li key={`b-${i}`}>{line}</li>
            ))}
          </ul>
        </div>
      )}
      {showAppLogs && flagged.length > 0 && (
        <div className="log-scan-flagged">
          <strong>Errors (app-log)</strong>
          <ul className="detail-log-list detail-log-flagged">
            {flagged.map((line, i) => (
              <li key={`f-${i}`}>{line}</li>
            ))}
          </ul>
        </div>
      )}
      <pre className="nifi-log-pre cluster-detail-log-pre cluster-detail-log-pre-inline">
        {previewText}
      </pre>
    </>
  )

  const logBlockMaximized = (
    <>
      {showBulletins && mode === "combined" && bulletins.length > 0 && (
        <div className="log-scan-flagged log-scan-bulletins">
          <strong>Bulletins (app-log)</strong>
          <ul className="detail-log-list">
            {bulletins.map((line, i) => (
              <li key={`b-max-${i}`}>{line}</li>
            ))}
          </ul>
        </div>
      )}
      {showAppLogs && flagged.length > 0 && (
        <div className="log-scan-flagged">
          <strong>Errors (app-log)</strong>
          <ul className="detail-log-list detail-log-flagged">
            {flagged.map((line, i) => (
              <li key={`f-max-${i}`}>{line}</li>
            ))}
          </ul>
        </div>
      )}
      <pre className="nifi-log-pre cluster-detail-log-pre cluster-detail-log-pre-max">
        {fullText}
      </pre>
    </>
  )

  const maximizeOverlay =
    isMaximized &&
    createPortal(
      <div className="metrics-chart-overlay log-maximize-overlay" role="presentation">
        <button
          type="button"
          className="metrics-chart-overlay-backdrop"
          aria-label="Close maximized view"
          onClick={() => setIsMaximized(false)}
        />
        <div className="panel metrics-chart-overlay-panel cluster-logs-overlay-panel">
          <div className="panel-header">
            <h2 className="panel-title">
              {boxTitle} — {title}
            </h2>
            <button
              type="button"
              className="link-btn metrics-chart-action"
              onClick={() => setIsMaximized(false)}
            >
              Close
            </button>
          </div>
          <div className="panel-body cluster-logs-overlay-body">{logBlockMaximized}</div>
        </div>
      </div>,
      document.body
    )

  const showAiResult =
    analyze && (aiAnalyze.isPending || aiAnalyze.isError || aiAnalyze.data)

  return (
    <section className={`detail-box detail-box-logs${compact ? " detail-box-logs-compact" : ""}`}>
      <div className="detail-box-logs-header">
        <h3 className="detail-box-title">{boxTitle}</h3>
        <div className="detail-box-logs-actions">
          {analyze && (
            <button
              type="button"
              className="link-btn metrics-chart-action log-ai-analyze-btn"
              disabled={aiAnalyze.isPending}
              onClick={() => aiAnalyze.mutate()}
            >
              {aiAnalyze.isPending ? "Analyzing…" : "AI analyze"}
            </button>
          )}
          <button
            type="button"
            className="link-btn metrics-chart-action"
            onClick={() => setIsMaximized(true)}
            aria-label={`Maximize ${boxTitle} for ${title}`}
          >
            Maximize
          </button>
        </div>
      </div>
      {sourcesLabel && (mode === "app-logs-only" || mode === "combined") && (
        <p className="detail-note">{sourcesLabel}</p>
      )}
      {mode === "bulletins-only" && sourcesLabel && (
        <p className="detail-note">{sourcesLabel}</p>
      )}
      {showAiResult && (
        <LogAiAnalyzeResult
          isPending={aiAnalyze.isPending}
          isError={aiAnalyze.isError}
          data={aiAnalyze.data}
        />
      )}
      {logBlock}
      {maximizeOverlay}
    </section>
  )
}
