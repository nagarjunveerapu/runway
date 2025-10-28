// src/components/Common/BottomNav.jsx
import React from "react";

/**
 * Simple mobile bottom nav.
 * Props:
 * - active: 'home'|'reports'|'add'|'settings'
 * - onNavigate(tab)
 * - onOpenAddActions() - called when Add pressed (we show an action sheet)
 */
export default function BottomNav({ active, onNavigate, onOpenAddActions }) {
  const Tab = ({ id, label, svg, onClick }) => (
    <button
      onClick={onClick}
      className={`flex-1 flex flex-col items-center justify-center py-2 text-xs ${
        active === id ? "text-runwayTeal font-semibold" : "text-gray-600"
      }`}
      aria-current={active === id ? "true" : "false"}
    >
      <div className="w-6 h-6 mb-1">{svg}</div>
      <div>{label}</div>
    </button>
  );

  return (
    <nav className="fixed left-0 right-0 bottom-0 bg-white border-t shadow-sm z-50">
      <div className="max-w-3xl mx-auto px-2 flex">
        <Tab
          id="home"
          label="Home"
          onClick={() => onNavigate("home")}
          svg={
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="w-full h-full">
              <path d="M3 11.5L12 4l9 7.5" strokeLinecap="round" strokeLinejoin="round" />
              <path d="M5 21V12h14v9" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          }
        />
        <Tab
          id="reports"
          label="Reports"
          onClick={() => onNavigate("reports")}
          svg={
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="w-full h-full">
              <rect x="3" y="3" width="18" height="18" rx="2" strokeLinecap="round" strokeLinejoin="round"/>
              <path d="M8 14v-4" strokeLinecap="round" strokeLinejoin="round"/>
              <path d="M12 14v-6" strokeLinecap="round" strokeLinejoin="round"/>
              <path d="M16 14v-2" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
          }
        />
        <Tab
          id="add"
          label="Add"
          onClick={() => onOpenAddActions()}
          svg={
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" className="w-full h-full">
              <path d="M12 5v14M5 12h14" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
          }
        />
        <Tab
          id="settings"
          label="Settings"
          onClick={() => onNavigate("settings")}
          svg={
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="w-full h-full">
              <path d="M12 15.5a3.5 3.5 0 100-7 3.5 3.5 0 000 7z" strokeLinecap="round" strokeLinejoin="round"/>
              <path d="M19.4 15a1.65 1.65 0 00.33 1.82l.06.06a2 2 0 01-2.83 2.83l-.06-.06a1.65 1.65 0 00-1.82-.33 1.65 1.65 0 00-1 1.51V21a2 2 0 01-4 0v-.09a1.65 1.65 0 00-1-1.51 1.65 1.65 0 00-1.82.33l-.06.06A2 2 0 015.28 18.9l.06-.06a1.65 1.65 0 00.33-1.82 1.65 1.65 0 00-1.51-1H3a2 2 0 010-4h.09a1.65 1.65 0 001.51-1 1.65 1.65 0 00-.33-1.82L4.18 6.7A2 2 0 016.9 3.9l.06.06a1.65 1.65 0 001.82.33H9a1.65 1.65 0 001-1.51V3a2 2 0 014 0v.09c.07.7.51 1.28 1.2 1.51h.01c.7.23 1.41-.03 1.82-.33l.06-.06A2 2 0 0118.72 5.1l-.06.06c-.25.28-.42.64-.47 1.03-.05.4.03.8.24 1.13.21.33.52.58.89.71.37.14.77.12 1.12-.06.35-.18.63-.48.79-.87.16-.39.17-.82.03-1.22" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
          }
        />
      </div>
    </nav>
  );
}