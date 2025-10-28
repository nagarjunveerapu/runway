// src/components/Dashboard/DashboardHeader.jsx
import React, { useMemo } from "react";
import { useApp } from "../../context/AppContext";
import { trailingAverages, totalLiquidAssets, computeRunway } from "../../utils/combinedFinancial";

export default function DashboardHeader({ targetMonths = 6 }) {
  const { transactions = [], assets = [], lookups = {} } = useApp();

  // trailing averages (last 3 months)
  const { avgIncome, avgOutflow, avgNet } = useMemo(() => {
    const res = trailingAverages(transactions, 3);
    return { avgIncome: res.avgIncome || 0, avgOutflow: res.avgOutflow || 0, avgNet: res.avgNet || 0 };
  }, [transactions]);

  // total liquid assets - pass lookups.assetTypes for better detection
  const liquidTotal = useMemo(() => {
    return totalLiquidAssets(assets, lookups.assetTypes || []);
  }, [assets, lookups]);

  // compute runway using avgNet (income - outflow)
  const runwayResult = useMemo(() => {
    return computeRunway({ liquidAssets: liquidTotal, avgNetOutflow: avgNet, minMonths: targetMonths });
  }, [liquidTotal, avgNet, targetMonths]);

  const runwayText = runwayResult.months === Infinity ? "∞" : (runwayResult.months === null ? "N/A" : Math.round(runwayResult.months * 10) / 10);

  return (
    <div className="grid grid-cols-1 md:grid-cols-4 gap-4 items-start">
      <div className="bg-white p-4 rounded shadow">
        <div className="text-xs text-gray-500">Avg Monthly Income</div>
        <div className="text-xl font-semibold mt-2">{Math.round(avgIncome).toLocaleString()}</div>
        <div className="text-xs text-gray-400 mt-1">Based on last 3 months</div>
      </div>

      <div className="bg-white p-4 rounded shadow">
        <div className="text-xs text-gray-500">Avg Net Flow</div>
        <div className={`text-xl font-semibold mt-2 ${avgNet >= 0 ? "text-green-600" : "text-red-600"}`}>
          {Math.round(avgNet).toLocaleString()}
        </div>
        <div className="text-xs text-gray-400 mt-1">Avg Income − Avg Outflow</div>
      </div>

      <div className="bg-white p-4 rounded shadow md:col-span-2">
        <div className="flex items-center justify-between">
          <div>
            <div className="text-xs text-gray-500">Runway (liquid / monthly burn)</div>
            <div className="flex items-baseline gap-2">
              <div className="text-2xl font-extrabold">{runwayText}</div>
              <div className="text-sm text-gray-500">months</div>
              <div className="ml-4 text-xs text-gray-500">Target: {targetMonths} mo</div>
            </div>
          </div>
          <div>
            <div
              className={`text-xs px-2 py-0.5 rounded ${
                runwayResult.status === "GREEN"
                  ? "bg-green-100 text-green-700"
                  : runwayResult.status === "RED"
                  ? "bg-red-100 text-red-700"
                  : runwayResult.status === "YELLOW"
                  ? "bg-yellow-100 text-yellow-700"
                  : "bg-gray-100 text-gray-700"
              }`}
            >
              {runwayResult.status || "UNKNOWN"}
            </div>
          </div>
        </div>
        <div className="text-sm text-gray-600 mt-2">{runwayResult.message}</div>
      </div>
    </div>
  );
}