import { useQuery } from "@tanstack/react-query"
import { useEffect, useMemo, useState } from "react"
import { useAuthSession } from "./auth/useAuthSession"
import { fetchClusters, fetchCollectors } from "./api"
import { LoginPage } from "./components/LoginPage"
import { AlertsCenter } from "./components/AlertsCenter"
import { ClusterDetailPanel } from "./components/ClusterDetailPanel"
import { ClusterSidebarNav } from "./components/ClusterSidebarNav"
import { FleetJobOverview } from "./components/FleetJobOverview"
import { NiFiDeploymentsDashboard } from "./components/NiFiDeploymentsDashboard"
import { ServiceDeploymentsDashboard } from "./components/ServiceDeploymentsDashboard"
import { SettingsPage } from "./components/SettingsPage"
import { PRODUCT_CLUSTER } from "./constants/clusters"
import { isObservableProduct, productLabel } from "./constants/products"
import { REFETCH_FAST_MS, REFETCH_MEDIUM_MS } from "./constants/refetch"

type View = "fleet" | "cluster" | "alerts" | "settings"

type ObservabilityShellProps = {
  username: string
  onLogout: () => Promise<void>
}

function ObservabilityShell({ username, onLogout }: ObservabilityShellProps) {
  const [view, setView] = useState<View>("fleet")
  const [activeClusterId, setActiveClusterId] = useState<string | null>(null)
  const [deploymentFocus, setDeploymentFocus] = useState<{
    product: string
    namespace: string
  } | null>(null)

  const clusters = useQuery({
    queryKey: ["clusters"],
    queryFn: fetchClusters,
    refetchInterval: REFETCH_MEDIUM_MS,
    refetchIntervalInBackground: true,
  })
  const collectors = useQuery({
    queryKey: ["collectors"],
    queryFn: fetchCollectors,
    refetchInterval: REFETCH_FAST_MS,
    refetchIntervalInBackground: true,
  })

  useEffect(() => {
    if (!clusters.data?.length) return
    const exists = activeClusterId && clusters.data.some((c) => c.id === activeClusterId)
    if (!exists) {
      setActiveClusterId(clusters.data[0].id)
    }
  }, [clusters.data, activeClusterId])

  const activeCluster = useMemo(() => {
    if (!clusters.data?.length) return undefined
    if (activeClusterId) {
      return clusters.data.find((c) => c.id === activeClusterId) ?? clusters.data[0]
    }
    return clusters.data[0]
  }, [clusters.data, activeClusterId])

  const handleSelectCluster = (clusterId: string) => {
    setActiveClusterId(clusterId)
    setView("cluster")
  }

  const handleFleetNavigate = (product: string, namespace?: string) => {
    const match =
      clusters.data?.find((c) => c.product === product) ??
      (PRODUCT_CLUSTER[product]
        ? clusters.data?.find((c) => c.id === PRODUCT_CLUSTER[product])
        : undefined)
    if (match) {
      setActiveClusterId(match.id)
      setView("cluster")
      if (namespace) {
        setDeploymentFocus({ product, namespace })
      }
    }
  }

  const clusterProduct = activeCluster?.product ?? "nifi"
  const showServiceDashboard = view === "cluster" && activeCluster && isObservableProduct(clusterProduct)

  return (
    <div className="app-shell">
      <header className="topbar">
        <div className="topbar-brand">
          <div className="topbar-logo" aria-hidden>
            CAO
          </div>
          <div>
            <div className="topbar-title">CDP AWC Observability</div>
            <div className="topbar-sub">Multi-cluster AWC observability control plane</div>
          </div>
        </div>
        <div className="topbar-meta">
          <span className="env-badge">AWC Lab</span>
          <span className="topbar-user">{username}</span>
          <button type="button" className="link-btn topbar-logout" onClick={() => void onLogout()}>
            Sign out
          </button>
          <a
            className="link-btn"
            href="https://console.awc.spoc.cloudera-labs.com/deployed-experiences?view=engines"
            target="_blank"
            rel="noreferrer"
            style={{ color: "#94a3b8" }}
          >
            AWC fleet catalog →
          </a>
        </div>
      </header>

      <div className="shell-body">
        <nav className="sidebar" aria-label="Primary">
          <div className="sidebar-section">Operations</div>
          <button
            type="button"
            className={`nav-item ${view === "fleet" ? "active" : ""}`}
            onClick={() => setView("fleet")}
          >
            Fleet overview
          </button>

          <ClusterSidebarNav
            clusters={clusters.data ?? []}
            activeClusterId={view === "cluster" ? activeClusterId : null}
            onSelectCluster={handleSelectCluster}
            isLoading={clusters.isLoading}
          />

          <div className="sidebar-section">Alerting</div>
          <button
            type="button"
            className={`nav-item ${view === "alerts" ? "active" : ""}`}
            onClick={() => setView("alerts")}
          >
            Alerts
          </button>
          <div className="sidebar-section">Administration</div>
          <button
            type="button"
            className={`nav-item ${view === "settings" ? "active" : ""}`}
            onClick={() => setView("settings")}
          >
            Settings
          </button>
        </nav>

        <div className="main-workspace">
          <div className="main-primary">
            {view === "alerts" && <AlertsCenter />}
            {view === "settings" && <SettingsPage />}

            {view === "fleet" && (
              <FleetJobOverview
                clusters={clusters.data ?? []}
                onNavigateProduct={handleFleetNavigate}
                onSelectCluster={(clusterId) => {
                  setActiveClusterId(clusterId)
                  setView("cluster")
                }}
              />
            )}

            {view === "cluster" && showServiceDashboard && clusterProduct === "nifi" && activeCluster && (
              <NiFiDeploymentsDashboard
                clusterId={activeCluster.id}
                focusNamespace={
                  deploymentFocus?.product === "nifi" ? deploymentFocus.namespace : undefined
                }
                onFocusApplied={() => setDeploymentFocus(null)}
              />
            )}

            {view === "cluster" &&
              showServiceDashboard &&
              clusterProduct !== "nifi" &&
              activeCluster && (
                <ServiceDeploymentsDashboard
                  product={clusterProduct}
                  clusterId={activeCluster.id}
                  focusNamespace={
                    deploymentFocus?.product === clusterProduct
                      ? deploymentFocus.namespace
                      : undefined
                  }
                  onFocusApplied={() => setDeploymentFocus(null)}
                />
              )}

            {view === "cluster" && activeCluster && !isObservableProduct(clusterProduct) && (
              <div className="panel">
                <div className="panel-header">
                  <h2 className="panel-title">{activeCluster.display_name}</h2>
                  <span className="tag">{productLabel(clusterProduct)}</span>
                </div>
                <div className="panel-body">
                  <p className="detail-note">
                    This cluster is registered for AWC identity and kubeconfig access. Product-specific
                    deployment dashboards apply to NiFi, Spark, Trino, Flink, and Airflow. Use the
                    cluster panel on the right for connectivity and collector status.
                  </p>
                </div>
              </div>
            )}
          </div>

          {view === "cluster" && activeCluster && (
            <aside className="main-aside">
              <ClusterDetailPanel
                cluster={activeCluster}
                collectors={collectors.data ?? []}
              />
            </aside>
          )}
        </div>
      </div>
    </div>
  )
}

export function App() {
  const { state: authState, login, logout } = useAuthSession()

  if (authState.status === "loading") {
    return (
      <div className="login-screen">
        <p className="login-sub">Loading…</p>
      </div>
    )
  }

  if (authState.status === "anonymous") {
    return <LoginPage error={authState.error} onLogin={login} />
  }

  return <ObservabilityShell username={authState.username} onLogout={logout} />
}
