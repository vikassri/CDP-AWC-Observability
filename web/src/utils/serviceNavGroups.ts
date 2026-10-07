import type { Cluster } from "../api"
import { OBSERVABLE_PRODUCTS, productLabel } from "../constants/products"

export type ServiceNavGroup = {
  serviceId: string
  serviceLabel: string
  clusters: Cluster[]
}

const SERVICE_ORDER = [...OBSERVABLE_PRODUCTS, "cai", "polaris"] as const

function serviceSortIndex(serviceId: string): number {
  const idx = SERVICE_ORDER.indexOf(serviceId as (typeof SERVICE_ORDER)[number])
  return idx === -1 ? 999 : idx
}

/** Group registry rows by CDP service; multiple clusters stack under the same service. */
export function buildServiceNavGroups(clusters: Cluster[]): ServiceNavGroup[] {
  const byService = new Map<string, Cluster[]>()

  for (const cluster of clusters) {
    const services = cluster.services?.length ? cluster.services : [cluster.product]
    for (const serviceId of services) {
      const list = byService.get(serviceId) ?? []
      if (!list.some((c) => c.id === cluster.id)) {
        list.push(cluster)
      }
      byService.set(serviceId, list)
    }
  }

  return [...byService.entries()]
    .sort(([a], [b]) => {
      const diff = serviceSortIndex(a) - serviceSortIndex(b)
      if (diff !== 0) return diff
      return productLabel(a).localeCompare(productLabel(b))
    })
    .map(([serviceId, groupClusters]) => ({
      serviceId,
      serviceLabel: productLabel(serviceId),
      clusters: [...groupClusters].sort((a, b) =>
        (a.display_name || a.id).localeCompare(b.display_name || b.id)
      ),
    }))
}

export function clusterDisplayName(cluster: Cluster): string {
  return cluster.display_name.trim() || cluster.id
}
