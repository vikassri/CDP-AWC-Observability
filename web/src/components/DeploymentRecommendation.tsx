import { useMutation } from "@tanstack/react-query"
import { fetchRecommendation, type ServiceDeploymentRow } from "../api"

type DeploymentRecommendationProps = {
  clusterId: string
  product: string
  deployment: ServiceDeploymentRow
}

export function DeploymentRecommendation({
  clusterId,
  product,
  deployment,
}: DeploymentRecommendationProps) {
  const recommend = useMutation({
    mutationFn: () =>
      fetchRecommendation({
        cluster_id: clusterId,
        product,
        name: deployment.name,
        namespace: deployment.namespace,
        status: deployment.status,
        issues: deployment.issues,
        metrics: deployment.metrics,
        logs: deployment.logs,
      }),
  })

  return (
    <div className="recommendation-panel">
      <button
        type="button"
        className="nav-item active"
        style={{ fontSize: 12, padding: "0.35rem 0.65rem", marginBottom: "0.5rem" }}
        disabled={recommend.isPending}
        onClick={() => recommend.mutate()}
      >
        {recommend.isPending ? "Analyzing…" : "Get AI recommendation"}
      </button>
      {recommend.data && (
        <div className="recommendation-body">
          <div className="tag" style={{ marginBottom: 6 }}>
            {recommend.data.source === "llm" ? "LLM" : "Rules"}
            {recommend.data.model ? ` · ${recommend.data.model}` : ""}
          </div>
          <pre className="recommendation-text">{recommend.data.recommendation}</pre>
        </div>
      )}
      {recommend.isError && (
        <p style={{ color: "var(--crit)", fontSize: 12 }}>Recommendation request failed.</p>
      )}
    </div>
  )
}
