import type { Cluster } from "../api"
import { buildServiceNavGroups, clusterDisplayName } from "../utils/serviceNavGroups"

type ClusterSidebarNavProps = {
  clusters: Cluster[]
  activeClusterId: string | null
  onSelectCluster: (clusterId: string) => void
  isLoading?: boolean
}

export function ClusterSidebarNav({
  clusters,
  activeClusterId,
  onSelectCluster,
  isLoading,
}: ClusterSidebarNavProps) {
  const groups = buildServiceNavGroups(clusters)

  return (
    <>
      <div className="sidebar-section">Services</div>
      {isLoading && <p className="sidebar-hint">Loading registry…</p>}
      {!isLoading && !groups.length && (
        <p className="sidebar-hint">No clusters in config/clusters.yaml</p>
      )}
      {groups.map((group) => (
        <div key={group.serviceId} className="nav-service-group">
          <div className="nav-service-heading">{group.serviceLabel}</div>
          {group.clusters.map((cluster) => {
            const isActive = cluster.id === activeClusterId
            const name = clusterDisplayName(cluster)
            const title = cluster.kubeconfig_present
              ? `${group.serviceLabel} · ${name} (${cluster.id})`
              : `${name} — kubeconfig missing on hub`
            return (
              <button
                key={`${group.serviceId}-${cluster.id}`}
                type="button"
                className={`nav-item nav-item-cluster-child${isActive ? " active" : ""}${
                  !cluster.kubeconfig_present ? " nav-item-warn" : ""
                }`}
                title={title}
                onClick={() => onSelectCluster(cluster.id)}
              >
                <span className="nav-item-cluster-child-name">{name}</span>
                {!cluster.kubeconfig_present && (
                  <span className="nav-item-cluster-child-badge" aria-hidden>
                    !
                  </span>
                )}
              </button>
            )
          })}
        </div>
      ))}
    </>
  )
}
