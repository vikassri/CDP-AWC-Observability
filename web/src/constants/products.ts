export const OBSERVABLE_PRODUCTS = ["nifi", "spark", "trino", "flink", "airflow"] as const

export type ObservableProduct = (typeof OBSERVABLE_PRODUCTS)[number]

export const PRODUCT_LABELS: Record<string, string> = {
  nifi: "NiFi",
  spark: "Spark",
  trino: "Trino",
  flink: "Flink",
  airflow: "Airflow",
  cai: "CAI",
  polaris: "Polaris",
}

export function isObservableProduct(product: string): product is ObservableProduct {
  return (OBSERVABLE_PRODUCTS as readonly string[]).includes(product)
}

export function productLabel(product: string): string {
  return PRODUCT_LABELS[product] ?? product.toUpperCase()
}

/** Left nav: `NiFi (CDF NiFi)` — primary service + cluster display name */
export function clusterNavLabel(cluster: {
  product: string
  display_name: string
  id: string
  services?: string[]
}): string {
  const primary = cluster.services?.[0] ?? cluster.product
  const clusterName = cluster.display_name.trim() || cluster.id
  return `${productLabel(primary)} (${clusterName})`
}
