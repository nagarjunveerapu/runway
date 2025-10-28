// src/components/Inline/InlineAddCard.jsx
import React from "react";

export default function InlineAddCard({
  title,
  subtitle,
  children,
  onSubmitLabel = "Add",
  onSubmit,
  className = ""
}) {
  return (
    <div className={`bg-white p-3 rounded border ${className}`}>
      <div className="mb-3">
        <div className="text-sm font-semibold">{title}</div>
        {subtitle && <div className="text-xs text-gray-500">{subtitle}</div>}
      </div>

      <div className="mb-3">
        {children}
      </div>

      <div className="flex justify-end">
        <button
          type="button"
          onClick={onSubmit}
          className="px-4 py-2 bg-runwayTeal text-white rounded"
        >
          {onSubmitLabel}
        </button>
      </div>
    </div>
  );
}