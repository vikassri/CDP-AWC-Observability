export type LogSearchResponse = {
  hits?:
    | { hits?: Array<{ _source?: Record<string, unknown> }> }
    | Array<{ _source?: Record<string, unknown> }>
  message?: string
}

export function linesFromLogSearch(data: LogSearchResponse | undefined): string[] {
  if (!data) return []
  let hits: Array<{ _source?: Record<string, unknown> }> = []
  const raw = data.hits
  if (Array.isArray(raw)) {
    hits = raw
  } else if (raw && typeof raw === "object" && Array.isArray(raw.hits)) {
    hits = raw.hits
  }
  return hits.map((hit) => {
    const src = hit._source ?? {}
    const body = src.body ?? src.log ?? src.message
    if (typeof body === "string") return body
    return JSON.stringify(src).slice(0, 240)
  })
}

export type WorkloadLogs = {
  source: string
  lines: string[]
  flagged: string[]
  bulletins?: string[]
  scanned_pod: string | null
}

export function aggregateDeploymentLogs(
  deployments: Array<{ name: string; namespace: string; logs?: WorkloadLogs }>
): { flagged: string[]; bulletins: string[]; lines: string[]; sources: string[] } {
  const flagged: string[] = []
  const bulletins: string[] = []
  const lines: string[] = []
  const sources = new Set<string>()
  for (const dep of deployments) {
    const logs = dep.logs
    if (!logs) continue
    sources.add(logs.source)
    const depRef = dep.namespace || dep.name
    for (const line of logs.flagged ?? []) {
      flagged.push(`[${depRef}] ${line}`)
    }
    for (const line of logs.bulletins ?? []) {
      bulletins.push(`[${depRef}] ${line}`)
    }
    for (const line of (logs.lines ?? []).slice(0, 6)) {
      lines.push(`[${depRef}] ${line}`)
    }
  }
  return { flagged, bulletins, lines, sources: [...sources] }
}
