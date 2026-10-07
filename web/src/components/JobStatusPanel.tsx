import { useQuery } from "@tanstack/react-query"
import { fetchJobStatus } from "../api"
import { REFETCH_FAST_MS } from "../constants/refetch"
import { JobStatusTiles } from "./JobStatusTiles"
import { PrometheusSourceCaption } from "./PrometheusSourceCaption"

type JobStatusPanelProps = {
  clusterId: string
  product: string
  title?: string
  showSourceCaption?: boolean
}

export function JobStatusPanel({
  clusterId,
  product,
  title,
  showSourceCaption = false,
}: JobStatusPanelProps) {
  const status = useQuery({
    queryKey: ["job-status", clusterId, product],
    queryFn: () => fetchJobStatus(clusterId),
    refetchInterval: REFETCH_FAST_MS,
    refetchIntervalInBackground: true,
  })

  const items = status.data?.items ?? []

  return (
    <div className="panel">
      <div className="panel-header panel-header--stacked">
        <div>
          <h2 className="panel-title">{title ?? "Workloads & jobs"}</h2>
          {showSourceCaption && (
            <PrometheusSourceCaption
              isFetching={status.isFetching}
              dataUpdatedAt={status.dataUpdatedAt}
              prometheusAvailable={status.data?.prometheus_available}
              clusterId={clusterId}
            />
          )}
        </div>
      </div>
      <div className="panel-body" style={{ paddingTop: 0 }}>
        <JobStatusTiles items={items} />
      </div>
    </div>
  )
}
