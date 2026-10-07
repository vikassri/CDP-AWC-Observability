import { useMutation } from "@tanstack/react-query"
import { fetchRecommendation, type ServiceDeploymentRow } from "../api"

export type LogAnalyzeContext = {
  clusterId: string
  product: string
  name: string
  namespace: string
  status?: string
  issues?: string[]
  metrics?: Record<string, number | null>
  logs: ServiceDeploymentRow["logs"]
}

export function buildLogAnalyzeContext(
  clusterId: string,
  product: string,
  deployment: Pick<
    ServiceDeploymentRow,
    "name" | "namespace" | "status" | "issues" | "metrics" | "logs"
  >
): LogAnalyzeContext {
  return {
    clusterId,
    product,
    name: deployment.name,
    namespace: deployment.namespace,
    status: deployment.status,
    issues: deployment.issues,
    metrics: deployment.metrics,
    logs: deployment.logs ?? {
      source: "none",
      lines: [],
      flagged: [],
      scanned_pod: null,
    },
  }
}

export function useLogAiAnalyze(context: LogAnalyzeContext | undefined) {
  return useMutation({
    mutationFn: () => {
      if (!context) throw new Error("missing context")
      return fetchRecommendation({
        cluster_id: context.clusterId,
        product: context.product,
        name: context.name,
        namespace: context.namespace,
        status: context.status ?? "unknown",
        issues: context.issues ?? [],
        metrics: context.metrics ?? {},
        logs: context.logs,
      })
    },
  })
}

type LogAiAnalyzeResultProps = {
  isPending: boolean
  isError: boolean
  data?: {
    recommendation: string
    source: string
    model: string | null
  }
}

export function LogAiAnalyzeResult({ isPending, isError, data }: LogAiAnalyzeResultProps) {
  if (isPending) {
    return <p className="log-ai-analyze-status">Running AI analysis…</p>
  }
  if (isError) {
    return <p className="log-ai-analyze-err">Analysis failed — check inference settings.</p>
  }
  if (!data) return null
  return (
    <div className="recommendation-body log-ai-analyze-result">
      <div className="tag tag-sm log-ai-analyze-tag">
        {data.source === "llm" ? "LLM" : "Rules"}
        {data.model ? ` · ${data.model}` : ""}
      </div>
      <pre className="recommendation-text">{data.recommendation}</pre>
    </div>
  )
}
