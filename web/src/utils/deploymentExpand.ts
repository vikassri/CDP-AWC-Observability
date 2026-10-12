import { deploymentKey } from "./deploymentKey"

type DeploymentRow = {
  name: string
  namespace: string
  status: string
}

/** Default expanded key: single deployment, focus, or first deployment with issues. */
export function pickDefaultExpandedDeploymentKey(
  deployments: DeploymentRow[],
  focusNamespace?: string
): string | null {
  if (!deployments.length) return null
  if (focusNamespace) {
    const match = deployments.find((d) => d.namespace === focusNamespace)
    return match ? deploymentKey(match.namespace, match.name) : focusNamespace
  }
  if (deployments.length === 1) {
    const d = deployments[0]
    return deploymentKey(d.namespace, d.name)
  }
  const withIssues = deployments.find((d) => d.status !== "healthy")
  if (withIssues) {
    return deploymentKey(withIssues.namespace, withIssues.name)
  }
  return null
}
