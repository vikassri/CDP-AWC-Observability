import { useQueries } from "@tanstack/react-query"
import { fetchClusterHealth, type Cluster } from "../api"
import { clusterNavLabel } from "../constants/products"
import { StatusPill } from "./StatusPill"

type FleetSummaryAsideProps = {
  clusters: Cluster[]
}

export function FleetSummaryAside({ clusters }: FleetSummaryAsideProps) {
  const healthQueries = useQueries({
    queries: clusters.map((c) => ({
      queryKey: ["health", c.id],
      queryFn: () => fetchClusterHealth(c.id),
      refetchInterval: 120_000,
      staleTime: 60_000,
    })),
  })

  const reachable = healthQueries.filter((q) => q.data?.healthy).length

  return (
    <div className="panel">
      <div className="panel-header">
        <h2 className="panel-title">Fleet registry</h2>
        <span className="tag">{clusters.length} clusters</span>
      </div>
      <div className="panel-body cluster-detail-body">
        <p className="detail-note">
          {reachable} of {clusters.length} clusters reachable via kubeconfig. Select a cluster on
          the left to open its service dashboard.
        </p>
        <ul className="fleet-aside-list">
          {clusters.map((cluster, index) => {
            const hq = healthQueries[index]
            return (
              <li key={cluster.id} className="fleet-aside-row">
                <strong className="fleet-aside-label">{clusterNavLabel(cluster)}</strong>
                <StatusPill
                  variant={
                    hq.isLoading ? "unknown" : hq.data?.healthy ? "ok" : "crit"
                  }
                  label={hq.isLoading ? "…" : hq.data?.healthy ? "OK" : "Down"}
                />
              </li>
            )
          })}
        </ul>
      </div>
    </div>
  )
}
