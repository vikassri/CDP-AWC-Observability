import { useState, type ReactNode } from "react"

type CollapsibleSectionProps = {
  title: string
  hint?: string
  defaultCollapsed?: boolean
  children: ReactNode
  className?: string
}

export function CollapsibleSection({
  title,
  hint,
  defaultCollapsed = true,
  children,
  className,
}: CollapsibleSectionProps) {
  const [isCollapsed, setIsCollapsed] = useState(defaultCollapsed)

  return (
    <div className={`panel collapsible-section${className ? ` ${className}` : ""}`}>
      <button
        type="button"
        className="collapsible-section-toggle"
        aria-expanded={!isCollapsed}
        onClick={() => setIsCollapsed((prev) => !prev)}
      >
        <div className="collapsible-section-head-text">
          <h3 className="panel-title collapsible-section-title">{title}</h3>
          {hint && <p className="collapsible-section-hint">{hint}</p>}
        </div>
        <span className="link-btn metrics-chart-action">
          {isCollapsed ? "Expand" : "Minimize"}
        </span>
      </button>
      {!isCollapsed && <div className="collapsible-section-body">{children}</div>}
    </div>
  )
}
