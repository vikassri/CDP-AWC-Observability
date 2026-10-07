import { useQuery } from "@tanstack/react-query"
import { fetchMetricsCatalog, type Cluster } from "../api"
import { JobStatusPanel } from "./JobStatusPanel"
import { REFETCH_FAST_MS } from "../constants/refetch"
import { MetricsChart } from "./MetricsChart"

type ServiceMetricsBoardProps = {
  clusters: Cluster[]
  product: string
  heading: string
}

export function ServiceMetricsBoard({ clusters, product, heading }: ServiceMetricsBoardProps) {
  const catalog = useQuery({ queryKey: ["metrics-catalog"], queryFn: fetchMetricsCatalog })
  const charts = (catalog.data ?? []).filter((c) => c.product === product)

  if (!clusters.length) return null

  return (
    <section className="service-board">
      <h2 className="service-board-title">{heading}</h2>
      {clusters.map((cluster) => (
        <div key={cluster.id} className="service-board-cluster">
          <h3 className="service-board-cluster-name">
            {cluster.display_name}{" "}
            <span className="mono" style={{ fontWeight: 400, color: "var(--text-muted)" }}>
              {cluster.id}
            </span>
          </h3>
          <JobStatusPanel clusterId={cluster.id} product={product} title="Job & workload status" />
          {charts.map((chart) => (
            <MetricsChart
              key={`${cluster.id}-${chart.query}`}
              title={chart.title}
              query={chart.query}
              clusterId={cluster.id}
              refetchMs={REFETCH_FAST_MS}
              valueDecimals={
                chart.title.includes("%") || chart.query.includes("heap_usage") ? 2 : undefined
              }
            />
          ))}
        </div>
      ))}
    </section>
  )
}
