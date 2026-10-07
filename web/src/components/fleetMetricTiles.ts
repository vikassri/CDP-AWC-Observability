import type { FleetDeploymentSummary, JobStatusItem } from "../api"

export type JobStatusTileTone = "ok" | "warn" | "crit" | "neutral"

export type JobStatusTileView = JobStatusItem & {
  tone?: JobStatusTileTone
  linkProduct?: string
  linkNamespace?: string
}

export function buildFleetMetricTiles(
  product: string,
  promItems: JobStatusItem[],
  dep?: FleetDeploymentSummary
): JobStatusTileView[] {
  const issueCount = dep?.with_issues_count ?? 0
  const discovery: JobStatusTileView[] = dep
    ? [
        {
          key: "disc_deployments",
          label: "Deployments",
          value: dep.deployment_count ?? 0,
          tone: "neutral",
          linkProduct: product,
        },
        {
          key: "disc_healthy",
          label: "Healthy",
          value: dep.healthy_count ?? 0,
          tone: "ok",
          linkProduct: product,
        },
        {
          key: "disc_issues",
          label: "With issues",
          value: issueCount,
          tone: issueCount > 0 ? "crit" : "ok",
          linkProduct: product,
        },
      ]
    : []

  const promPositive = promItems.filter((item) => (item.value ?? 0) > 0)
  const promRest = promItems.filter((item) => !((item.value ?? 0) > 0))
  const promTail: JobStatusTileView[] = (promPositive.length ? promPositive : promRest.slice(0, 3)).map(
    (item) => ({
      ...item,
      tone: item.key === "failed" && (item.value ?? 0) > 0 ? "crit" : "neutral",
      linkProduct: product,
    })
  )

  return [...discovery, ...promTail]
}
