export type DeploymentSearchRow = {
  name: string
  namespace: string
  status: string
  issues: string[]
}

export function filterDeployments<T extends DeploymentSearchRow>(
  rows: T[],
  query: string
): T[] {
  const q = query.trim().toLowerCase()
  if (!q) return rows
  return rows.filter(
    (row) =>
      row.name.toLowerCase().includes(q) ||
      row.namespace.toLowerCase().includes(q) ||
      row.issues.some((issue) => issue.toLowerCase().includes(q))
  )
}

export function groupDeploymentsByNamespace<T extends DeploymentSearchRow>(
  rows: T[]
): Array<{ namespace: string; deployments: T[] }> {
  const byNs = new Map<string, T[]>()
  for (const row of rows) {
    const list = byNs.get(row.namespace) ?? []
    list.push(row)
    byNs.set(row.namespace, list)
  }
  return [...byNs.entries()]
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([namespace, deployments]) => ({
      namespace,
      deployments: [...deployments].sort((a, b) => a.name.localeCompare(b.name)),
    }))
}
