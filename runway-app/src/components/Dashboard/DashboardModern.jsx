import React, { useMemo, memo } from 'react';
import { useApp } from '../../context/AppContext';
import EMIDateCalculator from './EMIDateCalculator';
import { parseMonth } from '../../utils/dateParser';

function formatNumber(n) {
  if (n == null) return '₹0';
  return `₹${Number(n).toLocaleString('en-IN')}`;
}

function formatCurrency(n) {
  if (n == null) return '₹0';
  return new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0
  }).format(n);
}

// Memoized Dashboard for performance
const DashboardModernMemo = memo(function DashboardModern({ onNavigate }) {
  const { transactions = [], assets = [], lookups = {} } = useApp();

  // Monthly aggregates - use database month field directly
  const monthly = useMemo(() => {
    const map = {};
    for (const t of transactions || []) {
      // Use database month field if it's valid YYYY-MM format, otherwise extract from date
      let month = t.month;
      if (!month || !month.match(/^\d{4}-\d{2}$/)) {
        month = parseMonth(t.date) || 'unknown';
      }
      
      map[month] = map[month] || { income: 0, outflow: 0, invest: 0, emi: 0 };
      const amt = Number(t.amount || 0);
      const category = (t.category || '').toLowerCase();
      
      // Smart categorization based on database category
      const desc = (t.description_raw || '').toLowerCase();
      
      // EMIs (check first to avoid double counting)
      if (/emi|loan/i.test(category) || /personal loan|canfin|cannfin|canfinhomes|ltd|home loan/i.test(desc)) {
        map[month].emi += amt;
      }
      // Investments
      else if (/investment/i.test(category)) {
        map[month].invest += amt;
      }
      // Income - any large credit OR salary category OR income category
      else if (t.type === 'credit') {
        if (category === 'salary' || category === 'income' || amt >= 50000) {
          map[month].income += amt;
        } else {
          // Small credits like interest or transfers
          map[month].income += amt;
        }
      }
      
      // All debits go to outflow (includes EMIs, investments, and expenses)
      if (t.type === 'debit') {
        map[month].outflow += amt;
      }
    }
    const months = Object.keys(map).sort();
    return { map, months };
  }, [transactions]);

  const { avgIncome3 = 0, avgOutflow3 = 0, avgNet3 = 0, avgEMI3 = 0, avgInvest3 = 0 } = useMemo(() => {
    const months = monthly.months;
    if (!months.length) {
      console.log('⚠️ No months found in monthly data');
      return { avgIncome3: 0, avgOutflow3: 0, avgNet3: 0, avgEMI3: 0, avgInvest3: 0 };
    }
    
    // Filter out malformed dates and get last 3 real months
    const realMonths = months.filter(m => m.match(/^\d{4}-\d{2}$/));
    
    // Filter to only months that have data, and take the most recent 3
    // Sort by month (YYYY-MM format sorts correctly)
    const monthsWithData = realMonths.filter(m => {
      const data = monthly.map[m] || {};
      return data && (data.income || data.outflow);
    });
    
    // Get last 3 months that actually have data
    const last3 = monthsWithData.slice(-3);
    
    let iSum = 0, oSum = 0, eSum = 0, invSum = 0;
    for (const m of last3) {
      const monthData = monthly.map[m] || {};
      iSum += monthData.income || 0;
      oSum += monthData.outflow || 0;
      eSum += monthData.emi || 0;
      invSum += monthData.invest || 0;
    }
    const denom = last3.length || 1;
    
    const result = { 
      avgIncome3: iSum / denom, 
      avgOutflow3: oSum / denom, 
      avgNet3: (iSum - oSum) / denom,
      avgEMI3: eSum / denom,
      avgInvest3: invSum / denom
    };
    
    return result;
  }, [monthly]);

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

  const runwayMonths = useMemo(() => {
    const net = avgNet3;
    if (Math.abs(net) < 1) return null;
    if (net > 0) return Infinity;
    const monthlyBurn = Math.abs(net);
    return totalLiquidAssets / monthlyBurn;
  }, [avgNet3, totalLiquidAssets]);

  const savingsRate = useMemo(() => {
    if (avgIncome3 <= 0) return 0;
    return Math.round((avgNet3 / avgIncome3) * 100);
  }, [avgNet3, avgIncome3]);

  const recent = (transactions || []).slice().sort((a,b)=> (new Date(b.date) - new Date(a.date))).slice(0,5);

  return (
    <div className="space-y-6 p-6">
      {/* Hero Card - Financial Health */}
      <div className="bg-gradient-to-br from-indigo-600 to-purple-600 rounded-2xl shadow-xl p-8 text-white">
        <div className="flex items-start justify-between mb-6">
          <div>
            <h2 className="text-2xl font-bold mb-2">Financial Health</h2>
            <p className="text-indigo-100">Track your financial progress</p>
          </div>
          <div className="text-right">
            <div className="text-4xl mb-1">📊</div>
          </div>
        </div>
        
        <div className="grid grid-cols-2 gap-6 mt-6">
          <div className="bg-white/10 backdrop-blur rounded-xl p-4">
            <div className="text-indigo-100 text-sm mb-1">Monthly Savings</div>
            <div className="text-3xl font-bold">{formatCurrency(avgNet3)}</div>
            <div className="text-xs text-indigo-100 mt-1">{savingsRate > 0 ? `${savingsRate}% savings rate` : 'Improve expenses'}</div>
          </div>
          <div className="bg-white/10 backdrop-blur rounded-xl p-4">
            <div className="text-indigo-100 text-sm mb-1">Runway</div>
            <div className="text-3xl font-bold">
              {runwayMonths === null ? 'N/A' : (runwayMonths === Infinity ? '∞' : `${Math.round(runwayMonths)}mo`)}
            </div>
            <div className="text-xs text-indigo-100 mt-1">Emergency fund duration</div>
          </div>
        </div>
      </div>

      {/* Key Metrics Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Income Card */}
        <div className="bg-white rounded-xl shadow-md hover:shadow-lg transition-shadow p-6 border-l-4 border-green-500">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-semibold text-gray-600 uppercase tracking-wide">Monthly Income</span>
            <span className="text-2xl">💰</span>
          </div>
          <div className="text-2xl font-bold text-gray-900">{formatCurrency(avgIncome3)}</div>
          <div className="text-xs text-gray-500 mt-1">Average of last 3 months</div>
        </div>

        {/* Expenses Card */}
        <div className="bg-white rounded-xl shadow-md hover:shadow-lg transition-shadow p-6 border-l-4 border-blue-500">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-semibold text-gray-600 uppercase tracking-wide">Monthly Expenses</span>
            <span className="text-2xl">💸</span>
          </div>
          <div className="text-2xl font-bold text-gray-900">{formatCurrency(avgOutflow3 - avgEMI3 - avgInvest3)}</div>
          <div className="text-xs text-gray-500 mt-1">Without EMI & Investments</div>
        </div>

        {/* Investments Card */}
        <div className="bg-white rounded-xl shadow-md hover:shadow-lg transition-shadow p-6 border-l-4 border-purple-500">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-semibold text-gray-600 uppercase tracking-wide">EMI & Investments</span>
            <span className="text-2xl">📈</span>
          </div>
          <div className="text-2xl font-bold text-gray-900">{formatCurrency(avgEMI3 + avgInvest3)}</div>
          <div className="text-xs text-gray-500 mt-1">{formatCurrency(avgEMI3)} EMI + {formatCurrency(avgInvest3)} Invest</div>
        </div>

        {/* Assets Card */}
        <div className="bg-white rounded-xl shadow-md hover:shadow-lg transition-shadow p-6 border-l-4 border-amber-500">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-semibold text-gray-600 uppercase tracking-wide">Liquid Assets</span>
            <span className="text-2xl">🏦</span>
          </div>
          <div className="text-2xl font-bold text-gray-900">{formatCurrency(totalLiquidAssets)}</div>
          <div className="text-xs text-gray-500 mt-1">Savings & Investments</div>
        </div>
      </div>

      {/* Detailed Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="bg-white rounded-xl shadow-md p-6">
          <h3 className="text-lg font-semibold text-gray-800 mb-4 flex items-center">
            <span className="mr-2">📉</span> Spending Breakdown
          </h3>
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-600">Total Outflow</span>
              <span className="font-semibold text-red-600">{formatCurrency(avgOutflow3)}</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-600">EMI Payments</span>
              <span className="font-semibold text-orange-600">{formatCurrency(avgEMI3)}</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-600">Investments</span>
              <span className="font-semibold text-purple-600">{formatCurrency(avgInvest3)}</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-600">Pure Expenses</span>
              <span className="font-semibold text-blue-600">{formatCurrency(avgOutflow3 - avgEMI3 - avgInvest3)}</span>
            </div>
            <div className="pt-3 border-t border-gray-200 mt-3">
              <div className="flex items-center justify-between">
                <span className="text-sm font-semibold text-gray-800">Savings Rate</span>
                <span className={`text-lg font-bold ${savingsRate >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                  {savingsRate}%
                </span>
              </div>
            </div>
          </div>
        </div>

        <div className="bg-white rounded-xl shadow-md p-6">
          <h3 className="text-lg font-semibold text-gray-800 mb-4 flex items-center">
            <span className="mr-2">💼</span> Asset Portfolio
          </h3>
          <div className="space-y-3">
            {assets.length > 0 ? (
              <>
                {assets.slice(0, 4).map(asset => (
                  <div key={asset.id} className="flex items-center justify-between p-2 bg-gray-50 rounded-lg">
                    <div className="flex items-center">
                      <span className="text-xl mr-2">{asset.asset_type === 'Property' ? '🏠' : asset.liquid ? '💎' : '🏦'}</span>
                      <div>
                        <div className="text-sm font-medium text-gray-800">{asset.name}</div>
                        <div className="text-xs text-gray-500">{asset.asset_type}</div>
                      </div>
                    </div>
                    <div className="text-right">
                      <div className="font-semibold text-gray-900">{formatCurrency(asset.current_value || asset.purchase_value)}</div>
                      <div className="text-xs text-gray-500">
                        {asset.liquid ? 'Liquid' : 'Non-liquid'}
                      </div>
                    </div>
                  </div>
                ))}
              </>
            ) : (
              <div className="text-sm text-gray-500">No assets yet. Add your first investment!</div>
            )}
          </div>
        </div>
      </div>

      {/* EMI Date Calculator */}
      <EMIDateCalculator onViewDetails={() => onNavigate && onNavigate('reports')} />

      {/* Recent Transactions */}
      <div className="bg-white rounded-xl shadow-md p-6">
        <h3 className="text-lg font-semibold text-gray-800 mb-4 flex items-center">
          <span className="mr-2">🕒</span> Recent Transactions
        </h3>
        {recent.length === 0 ? (
          <div className="text-center py-8 text-gray-500">
            <div className="text-4xl mb-2">📭</div>
            <p className="text-sm">No transactions yet</p>
            <p className="text-xs mt-1">Upload a CSV or add transactions manually</p>
          </div>
        ) : (
          <div className="divide-y divide-gray-100">
            {recent.map(t => (
              <div key={t.id} className="py-3 flex items-center justify-between hover:bg-gray-50 transition-colors rounded px-2">
                <div className="flex items-center">
                  <div className={`w-10 h-10 rounded-full flex items-center justify-center mr-3 ${
                    t.type === 'credit' ? 'bg-green-100' : (t.category && /emi|loan/i.test(t.category.toLowerCase())) ? 'bg-orange-100' : 'bg-blue-100'
                  }`}>
                    <span className="text-xl">
                      {t.type === 'credit' ? '💰' : (t.category && /emi|loan/i.test(t.category.toLowerCase())) ? '🏦' : '💳'}
                    </span>
                  </div>
                  <div>
                    <div className="font-medium text-gray-900">{t.category || 'Transaction'}</div>
                    <div className="text-xs text-gray-500">{t.date} • {t.description_raw || t.notes || 'No description'}</div>
                  </div>
                </div>
                <div className="text-right">
                  <div className={`font-bold ${
                    t.type === 'credit' ? 'text-green-600' : 'text-gray-900'
                  }`}>
                    {t.type === 'credit' ? '+' : '-'}{formatCurrency(t.amount)}
                  </div>
                  <div className="text-xs text-gray-500">{t.type === 'credit' ? 'Income' : 'Expense'}</div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
});

export default DashboardModernMemo;

