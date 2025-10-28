// src/RunwayApp.jsx
import React, { useMemo, useState } from "react";
import ModernHome from "./components/Modern/ModernHome";
import ModernReports from "./components/Modern/ModernReports";
import ModernProfile from "./components/Modern/ModernProfile";
import ModernAssetsLiabilities from "./components/Modern/ModernAssetsLiabilities";
import ModernAccounts from "./components/Modern/ModernAccounts";
import ModernOptimize from "./components/Modern/ModernOptimize";
import ModernWealth from "./components/Modern/ModernWealth";
import SalarySweepPage from "./components/Modern/SalarySweepPage";
import LoanPrepaymentPage from "./components/Modern/LoanPrepaymentPage";
import InvestmentPage from "./components/Modern/InvestmentPage";
import BottomNav from "./components/Modern/BottomNav";
import PageTransition from "./components/Modern/PageTransition";
import AddPage from "./components/Add/AddPage";
import SettingsPage from "./components/Settings/SettingsPage";
import CSVUpload from "./components/Upload/CSVUpload";
import { useApp } from "./context/AppContext";
import "./App.css";

export default function RunwayApp() {
  const [route, setRoute] = useState("home"); // "home" | "reports" | "add" | "assets" | "profile"
  const app = useApp() || {};
  const transactions = app.transactions || [];

  const kpiSummary = useMemo(() => {
    return {};
  }, [transactions]);

  function renderMain() {
    switch (route) {
      case "wealth":
        return <ModernWealth onNavigate={setRoute} />;
      case "reports":
        return <ModernReports onNavigate={setRoute} />;
      case "optimize":
        return <ModernOptimize onNavigate={setRoute} />;
      case "salary-sweep":
        return <SalarySweepPage onNavigate={setRoute} />;
      case "loan-prepayment":
        return <LoanPrepaymentPage onNavigate={setRoute} />;
      case "investment-rebalancer":
        return <InvestmentPage onNavigate={setRoute} />;
      case "accounts":
        return <ModernAccounts onNavigate={setRoute} />;
      case "add":
        return <AddPage defaultTab="transaction" onNavigate={setRoute} />;
      case "assets":
      case "liabilities":
        return <ModernAssetsLiabilities onNavigate={setRoute} />;
      case "profile":
        return <ModernProfile onNavigate={setRoute} />;
      case "categories":
      case "settings":
        return <SettingsPage />;
      case "upload":
        return <CSVUpload onUploadComplete={() => window.location.reload()} />;
      case "home":
      default:
        return <ModernHome onNavigate={setRoute} />;
    }
  }

  return (
    <div className="min-h-screen bg-white flex flex-col">
      <main className="flex-1 w-full overflow-y-auto">
        <PageTransition pageKey={route}>
          {renderMain()}
        </PageTransition>
      </main>

      {/* Modern Bottom Navigation */}
      <BottomNav currentRoute={route} onNavigate={setRoute} />
    </div>
  );
}