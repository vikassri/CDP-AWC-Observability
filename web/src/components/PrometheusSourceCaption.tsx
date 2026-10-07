import { REFETCH_FAST_MS } from "../constants/refetch"
import { StatusPill } from "./StatusPill"

type PrometheusSourceCaptionProps = {
  isFetching: boolean
  dataUpdatedAt?: number
  prometheusAvailable?: boolean
  clusterId?: string
}

export function PrometheusSourceCaption({
  isFetching,
  dataUpdatedAt,
  prometheusAvailable,
  clusterId,
}: PrometheusSourceCaptionProps) {
  const updated =
    dataUpdatedAt && !isFetching
      ? new Date(dataUpdatedAt).toLocaleTimeString([], {
          hour: "2-digit",
          minute: "2-digit",
          second: "2-digit",
        })
      : null

  return (
    <div className="prom-source-caption">
      <span>From Prometheus + status exporters</span>
      <span className="prom-source-meta">
        {clusterId ? (
          <>
            <span className="mono">{clusterId}</span>
            <span aria-hidden> · </span>
          </>
        ) : null}
        {isFetching ? (
          <span>Syncing…</span>
        ) : updated ? (
          <span>Updated {updated}</span>
        ) : (
          <span>Every {REFETCH_FAST_MS / 1000}s</span>
        )}
        {prometheusAvailable === false ? (
          <>
            <span aria-hidden> · </span>
            <StatusPill variant="warn" label="Prom unreachable" />
          </>
        ) : prometheusAvailable === true ? (
          <>
            <span aria-hidden> · </span>
            <StatusPill variant="ok" label="Prom OK" />
          </>
        ) : null}
      </span>
    </div>
  )
}
