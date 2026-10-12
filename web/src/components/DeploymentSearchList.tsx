import { useMemo, useState, type ReactNode } from "react"
import { StatusPill } from "./StatusPill"
import {
  deploymentStatusLabel,
  deploymentStatusVariant,
} from "./DeploymentCollapsibleCard"
import type { DeploymentSearchRow } from "../utils/filterDeployments"
import { filterDeployments } from "../utils/filterDeployments"

const SCROLL_ROW_THRESHOLD = 8
const SCROLL_MAX_HEIGHT_PX = 360

type DeploymentSearchListProps<T extends DeploymentSearchRow> = {
  rows: T[]
  selectedKey: string | null
  onSelect: (key: string) => void
  deploymentKey: (row: T) => string
  renderName?: (row: T) => ReactNode
  emptyMessage?: string
  searchPlaceholder?: string
  showSearch?: boolean
  extraHeader?: string
  renderExtraCell?: (row: T) => ReactNode
}

export function DeploymentSearchList<T extends DeploymentSearchRow>({
  rows,
  selectedKey,
  onSelect,
  deploymentKey,
  renderName,
  emptyMessage = "No deployments match your search.",
  searchPlaceholder = "Search by name, namespace, or issue…",
  showSearch = true,
  extraHeader,
  renderExtraCell,
}: DeploymentSearchListProps<T>) {
  const [query, setQuery] = useState("")

  const filtered = useMemo(() => filterDeployments(rows, query), [rows, query])
  const isScrollable = filtered.length > SCROLL_ROW_THRESHOLD

  return (
    <div className="deployment-search-list">
      {showSearch && rows.length > 3 ? (
        <label className="deployment-search-field">
          <span className="visually-hidden">Search deployments</span>
          <input
            type="search"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder={searchPlaceholder}
            className="deployment-search-input"
          />
        </label>
      ) : null}

      <div
        className={`deployment-table-wrap${isScrollable ? " deployment-table-wrap--scroll" : ""}`}
        style={isScrollable ? { maxHeight: SCROLL_MAX_HEIGHT_PX } : undefined}
      >
        <table className="data-table nifi-dep-table">
          <thead>
            <tr>
              <th>Deployment</th>
              <th>Status</th>
              {extraHeader ? <th>{extraHeader}</th> : null}
              <th>Issues</th>
            </tr>
          </thead>
          <tbody>
            {filtered.map((dep) => {
              const key = deploymentKey(dep)
              return (
                <tr
                  key={key}
                  className={selectedKey === key ? "selected" : ""}
                  onClick={() => onSelect(key)}
                >
                  <td>
                    {renderName ? (
                      renderName(dep)
                    ) : (
                      <>
                        <strong>{dep.name}</strong>
                        <div className="mono" style={{ color: "var(--text-muted)", marginTop: 2 }}>
                          {dep.namespace}
                        </div>
                      </>
                    )}
                  </td>
                  <td>
                    <StatusPill
                      variant={deploymentStatusVariant(dep.status)}
                      label={deploymentStatusLabel(dep.status)}
                    />
                  </td>
                  {renderExtraCell ? <td>{renderExtraCell(dep)}</td> : null}
                  <td>
                    {dep.issues.length ? (
                      <span className="nifi-issue-summary">{dep.issues[0]}</span>
                    ) : (
                      <span style={{ color: "var(--text-muted)" }}>No issues detected</span>
                    )}
                    {dep.issues.length > 1 ? (
                      <span className="nifi-issue-more"> +{dep.issues.length - 1} more</span>
                    ) : null}
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
        {!filtered.length ? (
          <div className="empty-state deployment-search-empty">{emptyMessage}</div>
        ) : null}
      </div>
      {query.trim() && filtered.length ? (
        <p className="deployment-search-count">
          Showing {filtered.length} of {rows.length}
        </p>
      ) : null}
    </div>
  )
}
