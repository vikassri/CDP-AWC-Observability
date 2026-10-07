import { useQueries, useQuery } from "@tanstack/react-query"
import {
  fetchClusterHealth,
  fetchFleetDeploymentOverview,
  fetchFleetJobStatus,
  type Cluster,
} from "../api"
import { REFETCH_FAST_MS, REFETCH_OVERVIEW_DEPLOY_MS } from "../constants/refetch"
import { isObservableProduct } from "../constants/products"
import { buildServiceNavGroups } from "../utils/serviceNavGroups"
import { FleetClusterOverviewCard } from "./FleetClusterOverviewCard"
import { PrometheusSourceCaption } from "./PrometheusSourceCaption"
import { StatusPill } from "./StatusPill"

type FleetJobOverviewProps = {
  clusters: Cluster[]
  onNavigateProduct?: (product: string, namespace?: string) => void
  onSelectCluster?: (clusterId: string) => void
}

export function FleetJobOverview({
  clusters,
  onNavigateProduct,
  onSelectCluster,
}: FleetJobOverviewProps) {
  const openCluster = (cluster: Cluster, serviceId: string, namespace?: string) => {
    onSelectCluster?.(cluster.id)
    const dashProduct = isObservableProduct(cluster.product) ? cluster.product : serviceId
    if (isObservableProduct(dashProduct)) {
      onNavigateProduct?.(dashProduct, namespace)
    }
  }

  const fleet = useQuery({
    queryKey: ["job-status-fleet"],
    queryFn: fetchFleetJobStatus,
    refetchInterval: REFETCH_FAST_MS,
    refetchIntervalInBackground: true,
    staleTime: 2_000,
  })

  const deployments = useQuery({
    queryKey: ["fleet-deployment-overview"],
    queryFn: fetchFleetDeploymentOverview,
    refetchInterval: REFETCH_OVERVIEW_DEPLOY_MS,
    refetchIntervalInBackground: true,
  })

  const healthQueries = useQueries({
    queries: clusters.map((c) => ({
      queryKey: ["health", c.id],
      queryFn: () => fetchClusterHealth(c.id),
      refetchInterval: 120_000,
      staleTime: 60_000,
    })),
  })

  const healthByClusterId = Object.fromEntries(
    clusters.map((c, index) => [c.id, healthQueries[index]])
  )

  const products = fleet.data?.products ?? {}
  const promOk = Object.values(products)
    .flat()
    .every((snap) => snap.prometheus_available !== false)

  const depByProduct = deployments.data?.products ?? {}
  const totals = deployments.data?.totals
  const serviceGroups = buildServiceNavGroups(clusters)

  return (
    <div className="panel fleet-overview-panel">
      <div className="panel-header panel-header--stacked">
        <div>
          <h2 className="panel-title">Fleet overview</h2>
          <PrometheusSourceCaption
            isFetching={fleet.isFetching || deployments.isFetching}
            dataUpdatedAt={deployments.dataUpdatedAt || fleet.dataUpdatedAt}
            prometheusAvailable={fleet.data ? promOk : undefined}
          />
        </div>
        {totals && (
          <div className="fleet-overview-totals">
            <StatusPill variant={totals.with_issues ? "warn" : "ok"} label={`${totals.deployments} deployments`} />
            {totals.with_issues > 0 && (
              <StatusPill variant="warn" label={`${totals.with_issues} with issues`} />
            )}
          </div>
        )}
      </div>

      <div className="panel-body fleet-overview-body">
        {!clusters.length && (
          <div className="empty-state" style={{ padding: "1rem" }}>
            No clusters in registry — check config/clusters.yaml.
          </div>
        )}

        <div className="fleet-hierarchy">
          {serviceGroups.map((group) => (
            <section key={group.serviceId} className="fleet-service-box">
              <header className="fleet-service-head">
                <h3 className="fleet-service-title">{group.serviceLabel}</h3>
                <span className="tag">{group.clusters.length} cluster(s)</span>
              </header>

              {group.clusters.map((cluster) => {
                const jobSnapshot =
                  (products[group.serviceId] ?? []).find((s) => s.cluster_id === cluster.id) ??
                  (cluster.product === group.serviceId
                    ? (products[group.serviceId] ?? [])[0]
                    : undefined)

                const depSummary = depByProduct[group.serviceId]
                const depForCluster =
                  depSummary?.cluster_id === cluster.id ? depSummary : undefined

                const hq = healthByClusterId[cluster.id]

                return (
                  <FleetClusterOverviewCard
                    key={`${group.serviceId}-${cluster.id}`}
                    cluster={cluster}
                    serviceId={group.serviceId}
                    jobSnapshot={jobSnapshot}
                    depSummary={depForCluster}
                    healthy={hq?.data?.healthy}
                    healthMessage={hq?.data?.message}
                    healthLoading={hq?.isLoading}
                    onOpenCluster={() => openCluster(cluster, group.serviceId)}
                    onNavigateDeployment={(namespace) =>
                      openCluster(cluster, group.serviceId, namespace)
                    }
                  />
                )
              })}
            </section>
          ))}
        </div>

        {deployments.isLoading && clusters.length > 0 && (
          <div className="empty-state" style={{ padding: "0.75rem 0", fontSize: 12 }}>
            Refreshing deployment discovery…
          </div>
        )}
        {deployments.isError && (
          <div className="empty-state" style={{ padding: "0.75rem 0", fontSize: 12 }}>
            Could not load fleet deployment overview.
          </div>
        )}
        {fleet.isError && (
          <div className="empty-state" style={{ padding: "0.75rem 0", fontSize: 12 }}>
            Prometheus job-status unavailable — check hub Prometheus and exporters.
          </div>
        )}
      </div>
    </div>
  )
}
