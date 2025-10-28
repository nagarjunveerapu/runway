import React, { useMemo } from 'react';
import { useApp } from '../../context/AppContext';
import TransactionList from '../Reports/TransactionList';

/*
  Dashboard + DashboardHeader combined file.
  - DashboardHeader computes Avg Monthly Income, Avg Net Flow and Runway
  - Dashboard shows header, overview and recent activity (latest txns)

  Drop this file into: src/components/Dashboard/DashboardComponents.jsx
  Then import `Dashboard` from this file where you previously used Dashboard.
*/

function formatNumber(n) {
  if (n == null) return '0';
  return new Intl.NumberFormat().format(Math.round(n));
}

function lastNMonthsArray(n = 6) {
  const months = [];
  const now = new Date();
  for (let i = n - 1; i >= 0; i--) {
    const d = new Date(now.getFullYear(), now.getMonth() - i, 1);
    months.push(d.toISOString().slice(0, 7)); // YYYY-MM
  }
  return months;
}

function computeMonthlySums(transactions = []) {
  // returns { [month]: { income: number, outflow: number, net: number } }
  const byMonth = {};
  transactions.forEach((t) => {
    const m = t.month || (t.date ? t.date.slice(0, 7) : null);
    if (!m) return;
    if (!byMonth[m]) byMonth[m] = { income: 0, outflow: 0 };
    const amt = Number(t.amount || 0);
    // classify based on t.type where possible
    if (t.type === 'income' || /income/i.test(t.category || '')) byMonth[m].income += amt;
    else if (t.type === 'expense' || /expense|emi|credit|grocer|utilities|tax/i.test(t.category || '')) byMonth[m].outflow += amt;
    else {
      // fallback: positive amounts = income, negative = outflow (but we store positive numbers in sample)
      // use user-provided type else assume outflow for categories matching common expense words
      if (amt >= 0) byMonth[m].outflow += 0; // nothing
    }
  });
  // compute net
  Object.keys(byMonth).forEach((m) => {
    byMonth[m].net = (byMonth[m].income || 0) - (byMonth[m].outflow || 0);
  });
  return byMonth;
}

export function DashboardHeader({ targetMonths = 6 }) {
  const { transactions = [], assets = [] } = useApp();

  // prepare last 6 months labels
  const months = useMemo(() => lastNMonthsArray(6), []);

  const monthly = useMemo(() => computeMonthlySums(transactions), [transactions]);

  // compute averages over the months we have data for (prefer last 3 months)
  const avg = useMemo(() => {
    const last3 = months.slice(-3);
    let incomeSum = 0, outflowSum = 0, count = 0;
    last3.forEach((m) => {
      if (monthly[m]) {
        incomeSum += monthly[m].income || 0;
        outflowSum += monthly[m].outflow || 0;
        count++;
      }
    });
    const monthsUsed = count || 1;
    return {
      avgIncome: Math.round(incomeSum / monthsUsed),
      avgOutflow: Math.round(outflowSum / monthsUsed),
      avgNet: Math.round((incomeSum - outflowSum) / monthsUsed)
    };
  }, [monthly, months]);

  // compute liquid assets (heuristic): bank accounts, cash, or assets with is_investment false
  const totalLiquidAssets = useMemo(() => {
    const liquid = (assets || []).filter(a => {
      if (a.is_investment === false) return true;
      const t = (a.type || '').toLowerCase();
      return /bank|cash|liquid|savings|current/.test(t);
    });
    return liquid.reduce((s, a) => s + Number(a.purchase_value || a.value || 0), 0);
  }, [assets]);

  // runway months: if avgNet < 0 (meaning net outflow) we compute runway = liquid / -avgNet
  const runwayMonths = useMemo(() => {
    const burn = avg.avgNet; // could be negative or positive
    if (burn <= 0) return Infinity; // no burn
    // avgNet is income - outflow; positive means net surplus -> infinite runway
    // we want monthly burn as outflow - income when negative
    const monthlyBurn = Math.max(0, avg.avgOutflow - avg.avgIncome);
    if (monthlyBurn <= 0) return Infinity;
    return totalLiquidAssets / monthlyBurn;
  }, [avg, totalLiquidAssets]);

  const status = useMemo(() => {
    if (!isFinite(runwayMonths)) return { label: 'GREEN', color: 'bg-green-100 text-green-800' };
    if (runwayMonths >= targetMonths) return { label: 'GREEN', color: 'bg-green-100 text-green-800' };
    if (runwayMonths >= targetMonths/2) return { label: 'YELLOW', color: 'bg-yellow-100 text-yellow-800' };
    return { label: 'RED', color: 'bg-red-100 text-red-800' };
  }, [runwayMonths, targetMonths]);

  // sparkline data: last 6 month nets
  const spark = months.map(m => (monthly[m] ? monthly[m].net : 0));

  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
      <div className="bg-white p-4 rounded shadow">
        <div className="text-xs text-gray-500">Avg Monthly Income</div>
        <div className="text-2xl font-semibold mt-2">{formatNumber(avg.avgIncome)}</div>
        <div className="text-xs text-gray-400">Based on last 3 months</div>
      </div>

      <div className="bg-white p-4 rounded shadow">
        <div className="text-xs text-gray-500">Avg Net Flow</div>
        <div className="text-2xl font-semibold mt-2">{formatNumber(avg.avgNet)}</div>
        <div className="text-xs text-gray-400">Avg Income - Avg Outflow</div>
      </div>

      <div className="bg-white p-4 rounded shadow">
        <div className="text-xs text-gray-500">Runway (liquid / monthly burn)</div>
        <div className="flex items-baseline gap-2 mt-2">
          <div className="text-3xl font-bold">{isFinite(runwayMonths) ? Math.round(runwayMonths) : '∞'}</div>
          <div className="text-sm text-gray-500">months</div>
        </div>
        <div className="mt-2 text-xs text-gray-500">Target: {targetMonths} mo</div>

        <div className="mt-3 flex items-center justify-between">
          <div className={`px-2 py-1 rounded text-xs ${status.color}`}>{status.label}</div>
          <div className="text-xs text-gray-400">Tip: Add incomes/expenses for better estimates.</div>
        </div>

        {/* sparkline */}
        <div className="mt-3">
          <Sparkline data={spark} />
        </div>
      </div>
    </div>
  );
}

function Sparkline({ data = [] }) {
  // simple SVG sparkline
  const w = 180, h = 40, pad = 4;
  const max = Math.max(...data.map(d => Math.abs(d)), 1);
  const step = data.length > 1 ? (w - pad*2) / (data.length - 1) : 0;
  const points = data.map((d, i) => {
    const x = pad + i * step;
    const y = h/2 - (d / max) * (h/2 - pad);
    return `${x},${y}`;
  }).join(' ');
  return (
    <svg width={w} height={h} className="block">
      <polyline fill="none" stroke="#2d9c9a" strokeWidth="2" points={points} strokeLinejoin="round" strokeLinecap="round" />
    </svg>
  );
}

export default function Dashboard() {
  const { transactions = [] } = useApp();

  const recent = useMemo(() => {
    return (transactions || []).slice(0, 6);
  }, [transactions]);

  return (
    <div className="min-h-[60vh]">
      <DashboardHeader />

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <div className="lg:col-span-2">
          <div className="bg-white p-4 rounded shadow mb-4">
            <h3 className="font-semibold">Overview</h3>
            <div className="text-sm text-gray-600 mt-2">Keep an eye on Avg Monthly Income and Avg Net Flow above. Use Reports for drill-downs and to tune your runway targets.</div>
          </div>

          <div className="bg-white p-4 rounded shadow">
            <h3 className="font-semibold">Recent activity</h3>
            <div className="mt-3">
              {recent.length === 0 ? <div className="text-sm text-gray-500">No transactions yet.</div>
                : <TransactionList transactions={recent} /> }
            </div>
          </div>
        </div>

        <aside className="bg-white p-4 rounded shadow">
          <h3 className="font-semibold">Quick stat</h3>
          <div className="mt-3 text-sm text-gray-600">Use Reports for full ledger and filters.</div>
        </aside>
      </div>
    </div>
  );
}
