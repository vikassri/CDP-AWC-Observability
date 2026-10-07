export type NifiChartDef = {
  title: string
  query: string
  valueDecimals?: number
}

/** Cluster-wide PromQL ($cluster substituted by API). */
export const NIFI_CLUSTER_CHARTS: NifiChartDef[] = [
  {
    title: "Backpressure — max % (object count)",
    query: 'max(nifi_percent_used_count{cluster="$cluster"}) * 100',
    valueDecimals: 2,
  },
  {
    title: "Backpressure — max % (bytes)",
    query: 'max(nifi_percent_used_bytes{cluster="$cluster"}) * 100',
    valueDecimals: 2,
  },
  {
    title: "Queued content (bytes)",
    query: 'sum(nifi_size_content_queued_total{cluster="$cluster"})',
  },
  {
    title: "Total content input (bytes)",
    query: 'sum(nifi_size_content_input_total{cluster="$cluster"})',
  },
  {
    title: "Total content output (bytes)",
    query: 'sum(nifi_size_content_output_total{cluster="$cluster"})',
  },
  {
    title: "FlowFiles received",
    query: 'sum(nifi_amount_flowfiles_received{cluster="$cluster"})',
  },
  {
    title: "FlowFiles transferred",
    query: 'sum(nifi_amount_flowfiles_transferred{cluster="$cluster"})',
  },
  {
    title: "FlowFiles sent",
    query: 'sum(nifi_amount_flowfiles_sent{cluster="$cluster"})',
  },
  {
    title: "Items queued",
    query: 'sum(nifi_amount_items_queued{cluster="$cluster"})',
  },
  {
    title: "JVM heap usage (%)",
    query: 'avg(nifi_jvm_heap_usage{cluster="$cluster"}) * 100',
    valueDecimals: 2,
  },
]

export function nifiNamespaceCharts(namespace: string): NifiChartDef[] {
  const ns = namespace.replace(/"/g, '\\"')
  return NIFI_CLUSTER_CHARTS.map((chart) => ({
    ...chart,
    title: chart.title,
    query: chart.query.replace(
      '{cluster="$cluster"}',
      `{cluster="$cluster", nifi_namespace="${ns}"}`
    ),
  }))
}
