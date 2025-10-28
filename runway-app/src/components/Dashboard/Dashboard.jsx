// src/components/Dashboard/Dashboard.jsx
import React, { useMemo } from 'react';
import { useApp } from '../../context/AppContext';

/*
  Simple Dashboard — shows:
  - Avg monthly income (last N months)
  - Avg net flow (income - outflow)
  - Runway estimate (liquid / monthly burn) — very simple: take liquid assets and divide by avg negative net (if burn)
  - Recent transactions (latest 6)
*/

function formatNumber(n) {
  if (n == null) return '0';
  return Number(n).toLocaleString();
}

export default function Dashboard() {
  const { transactions = [], assets = [], lookups = {} } = useApp();

  // derive monthly aggregates
  const monthly = useMemo(() => {
    const map = {};
    for (const t of transactions || []) {
      const month = (t.month) || (t.date && t.date.slice(0,7)) || 'unknown';
      map[month] = map[month] || { income: 0, outflow: 0, invest: 0, emi: 0 };
      const amt = Number(t.amount || 0);
      
      // Categorize transaction
      const category = (t.category || '').toLowerCase();
      const desc = (t.description_raw || t.notes || '').toLowerCase();
      
      if (t.type === 'income' || /salary|dividend|interest|income/i.test(category)) {
        map[month].income += amt;
      } else if (/emi|loan/i.test(category)) {
        map[month].emi += amt;
        map[month].outflow += amt;
      } else if (/invest|sip/i.test(category)) {
        map[month].invest += amt;
        map[month].outflow += amt;
      } else {
        map[month].outflow += amt;
      }
    }
    // convert to sorted array newest last
    const months = Object.keys(map).sort();
    return { map, months };
  }, [transactions]);

  // average over last 3 months (or all if <3)
  const { avgIncome3 = 0, avgOutflow3 = 0, avgNet3 = 0, avgEMI3 = 0, avgInvest3 = 0 } = useMemo(() => {
    const months = monthly.months;
    if (!months.length) return { avgIncome3: 0, avgOutflow3: 0, avgNet3: 0, avgEMI3: 0, avgInvest3: 0 };
    const last3 = months.slice(-3);
    let iSum = 0, oSum = 0, eSum = 0, invSum = 0;
    for (const m of last3) {
      iSum += monthly.map[m].income || 0;
      oSum += monthly.map[m].outflow || 0;
      eSum += monthly.map[m].emi || 0;
      invSum += monthly.map[m].invest || 0;
    }
    const denom = last3.length || 1;
    return { 
      avgIncome3: iSum / denom, 
      avgOutflow3: oSum / denom, 
      avgNet3: (iSum - oSum) / denom,
      avgEMI3: eSum / denom,
      avgInvest3: invSum / denom
    };
  }, [monthly]);

  // simple liquid assets total (assetTypes use lookups)
  const totalLiquidAssets = useMemo(() => {
    const assetTypes = (lookups && lookups.assetTypes) || [];
    const isLiquid = (a) => {
      if (a == null) return false;
      if (a.hasOwnProperty('liquid')) return !!a.liquid;
      const def = assetTypes.find(t => t.name === a.type);
      return !!(def && def.liquid);
    };
    return (assets || []).filter(a => !a.disposed && isLiquid(a)).reduce((s,a) => s + Number(a.current_value || a.purchase_value || 0), 0);
  }, [assets, lookups]);

  // runway: if avgNet3 is <= 0 (meaning net positive) show Infinity / surplus; if negative (burn) compute months = liquid / burn
  const runwayMonths = useMemo(() => {
    const net = avgNet3;
    if (Math.abs(net) < 1) return null; // unknown or zero
    if (net > 0) return Infinity; // surplus, not burning
    const monthlyBurn = Math.abs(net);
    return totalLiquidAssets / monthlyBurn;
  }, [avgNet3, totalLiquidAssets]);

  const recent = (transactions || []).slice().sort((a,b)=> (new Date(b.date) - new Date(a.date))).slice(0,6);

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-white p-4 rounded shadow">
          <div className="text-sm text-gray-600">Avg Monthly Income</div>
          <div className="text-2xl font-bold mt-2">{formatNumber(avgIncome3)}</div>
          <div className="text-xs text-gray-500 mt-1">Last 3 months avg</div>
        </div>
        <div className="bg-white p-4 rounded shadow">
          <div className="text-sm text-gray-600">Avg Monthly Expenses</div>
          <div className="text-2xl font-bold mt-2" style={{ color: '#e53e3e' }}>{formatNumber(avgOutflow3 - avgEMI3 - avgInvest3)}</div>
          <div className="text-xs text-gray-500 mt-1">Excluding EMI & Investments</div>
        </div>
        <div className="bg-white p-4 rounded shadow">
          <div className="text-sm text-gray-600">Avg EMI & Investments</div>
          <div className="text-2xl font-bold mt-2">{formatNumber(avgEMI3 + avgInvest3)}</div>
          <div className="text-xs text-gray-500 mt-1">{formatNumber(avgEMI3)} EMI + {formatNumber(avgInvest3)} Invest</div>
        </div>
        <div className="bg-white p-4 rounded shadow">
          <div className="text-sm text-gray-600">Net Savings Rate</div>
          <div className="text-2xl font-bold mt-2" style={{ color: avgNet3 < 0 ? '#e53e3e' : '#16a34a' }}>{avgIncome3 > 0 ? Math.round((avgNet3 / avgIncome3) * 100) : 0}%</div>
          <div className="text-xs text-gray-500 mt-1">Income saved</div>
        </div>
      </div>
      
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div className="bg-white p-4 rounded shadow">
          <div className="text-sm text-gray-600">Avg Net Flow</div>
          <div className="text-2xl font-bold mt-2" style={{ color: avgNet3 < 0 ? '#e53e3e' : '#16a34a' }}>{formatNumber(avgNet3)}</div>
          <div className="text-xs text-gray-500 mt-1">Income − Total Outflow</div>
        </div>
        <div className="bg-white p-4 rounded shadow">
          <div className="text-sm text-gray-600">Liquid Assets</div>
          <div className="text-2xl font-bold mt-2">{formatNumber(totalLiquidAssets)}</div>
          <div className="text-xs text-gray-500 mt-1">Savings + Investments</div>
        </div>
        <div className="bg-white p-4 rounded shadow">
          <div className="text-sm text-gray-600">Runway (months)</div>
          <div className="text-2xl font-bold mt-2">{runwayMonths === null ? 'N/A' : (runwayMonths === Infinity ? '∞' : Math.round(runwayMonths))}</div>
          <div className="text-xs text-gray-500 mt-1">Target: 6+ mo</div>
        </div>
      </div>

      <div className="bg-white p-4 rounded shadow">
        <h3 className="font-semibold">Overview</h3>
        <div className="text-sm text-gray-600 mt-2">Keep an eye on Avg Monthly Income and Avg Net Flow above. Use Reports for drill-downs and to tune your runway targets.</div>
      </div>

      <div className="bg-white p-4 rounded shadow">
        <h3 className="font-semibold">Recent activity</h3>
        {recent.length === 0 ? (
          <div className="text-sm text-gray-500 mt-3">No transactions yet.</div>
        ) : (
          <ul className="mt-3 space-y-2">
            {recent.map(t => (
              <li key={t.id} className="flex justify-between items-start">
                <div>
                  <div className="font-medium">{t.date} — {t.category}</div>
                  <div className="text-xs text-gray-500">{t.notes}</div>
                </div>
                <div className="text-right">
                  <div className="font-medium">{formatNumber(t.amount)}</div>
                  <div className="text-xs text-gray-500">{t.type || 'expense'}</div>
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}