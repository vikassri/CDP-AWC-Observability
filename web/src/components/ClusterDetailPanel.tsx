import { useQuery } from "@tanstack/react-query"
import { fetchClusterHealth, type Cluster, type CollectorStatus } from "../api"
import { clusterNavLabel, productLabel } from "../constants/products"
import { StatusPill } from "./StatusPill"

type ClusterDetailPanelProps = {
  cluster: Cluster
  collectors: CollectorStatus[]
}

function collectorsForCluster(cluster: Cluster, all: CollectorStatus[]): CollectorStatus[] {
  const names = new Set(cluster.collectors)
  const prefix = cluster.product === "nifi" ? "nifi" : cluster.product
  return all.filter((c) => names.has(c.name) || c.name.startsWith(`${prefix}_`))
}

export function ClusterDetailPanel({ cluster, collectors }: ClusterDetailPanelProps) {
  const health = useQuery({
    queryKey: ["health", cluster.id],
    queryFn: () => fetchClusterHealth(cluster.id),
    refetchInterval: 120_000,
  })

  const clusterCollectors = collectorsForCluster(cluster, collectors)
  const services = cluster.services?.length ? cluster.services : [cluster.product]

  return (
    <div className="cluster-detail">
      <div className="panel cluster-detail-panel">
        <div className="panel-header cluster-detail-panel-header">
          <h2 className="panel-title cluster-detail-title" title={clusterNavLabel(cluster)}>
            {clusterNavLabel(cluster)}
          </h2>
          <StatusPill
            variant={health.isLoading ? "unknown" : health.data?.healthy ? "ok" : "crit"}
            label={
              health.isLoading ? "Checking" : health.data?.healthy ? "API OK" : "Unreachable"
            }
          />
        </div>
        <div className="panel-body cluster-detail-body cluster-detail-scroll">
          <section className="detail-box">
            <h3 className="detail-box-title">Cluster</h3>
            <dl className="detail-dl">
              <div>
                <dt>Cluster ID</dt>
                <dd className="mono detail-break">{cluster.id}</dd>
              </div>
              <div>
                <dt>AWC engine</dt>
                <dd className="mono detail-break">{cluster.awc_engine_id || cluster.id}</dd>
              </div>
              <div>
                <dt>Kube context</dt>
                <dd className="mono detail-break">{cluster.context}</dd>
              </div>
            </dl>
          </section>

          <section className="detail-box">
            <h3 className="detail-box-title">Services</h3>
            <div className="tag-list">
              {services.map((svc) => (
                <span key={svc} className="tag">
                  {productLabel(svc)}
                </span>
              ))}
            </div>
          </section>

          <section className="detail-box">
            <h3 className="detail-box-title">Kubeconfig</h3>
            <dl className="detail-dl">
              <div>
                <dt>Path (repo)</dt>
                <dd className="mono detail-break">{cluster.kubeconfig_ref || "—"}</dd>
              </div>
              <div>
                <dt>On hub host</dt>
                <dd>
                  {cluster.kubeconfig_present ? (
                    <span className="detail-ok">File present</span>
                  ) : (
                    <span className="detail-warn">Missing — copy from uob_poc / VPN</span>
                  )}
                </dd>
              </div>
            </dl>
          </section>

          <section className="detail-box">
            <h3 className="detail-box-title">Control plane</h3>
            <p className="detail-message detail-break">{health.data?.message ?? "Probing Kubernetes API…"}</p>
          </section>

          <section className="detail-box">
            <h3 className="detail-box-title">Hub collectors</h3>
            {cluster.collectors.length === 0 && (
              <p className="detail-note">No collectors enabled for this cluster.</p>
            )}
            <ul className="detail-collector-list">
              {cluster.collectors.map((name) => {
                const live = clusterCollectors.find((c) => c.name === name)
                return (
                  <li key={name} className="detail-collector-row">
                    <span className="mono detail-collector-name">{name}</span>
                    <StatusPill
                      variant={live?.last_error ? "crit" : live ? "ok" : "unknown"}
                      label={live?.last_error ? "Fault" : live ? "OK" : "Idle"}
                    />
                  </li>
                )
              })}
            </ul>
            {clusterCollectors.some((c) => c.last_error) && (
              <ul className="detail-errors">
                {clusterCollectors
                  .filter((c) => c.last_error)
                  .map((c) => (
                    <li key={c.name} className="detail-break">
                      {c.last_error}
                    </li>
                  ))}
              </ul>
            )}
          </section>

          <section className="detail-box">
            <h3 className="detail-box-title">AWC console</h3>
            {cluster.awc_console_url ? (
              <a
                className="link-btn detail-break"
                href={cluster.awc_console_url}
                target="_blank"
                rel="noreferrer"
              >
                Open {productLabel(cluster.product)} in AWC →
              </a>
            ) : (
              <p className="detail-note">No AWC deep link configured.</p>
            )}
          </section>

          <p className="detail-note" style={{ margin: 0 }}>
            Logs and AI analysis are on each deployment in the main view.
          </p>
        </div>
      </div>
    </div>
  )
}
