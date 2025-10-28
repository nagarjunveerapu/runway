// src/components/Modern/ModernReports.jsx
import React, { useMemo, useState, useEffect } from 'react';
import { useApp } from '../../context/AppContext';
import { getSummary, getTopMerchants } from '../../api/services/analytics';
import CategoryBreakdown from '../Reports/CategoryBreakdown';
import TopMerchants from '../Reports/TopMerchants';
import RecurringPayments from '../../features/reports/recurring-payments/RecurringPayments';
import FIRECalculator from '../../features/reports/fire-calculator/FIRECalculator';
import EmergencyFundHealth from '../../features/reports/emergency-fund/EmergencyFundHealth';
import TransactionList from '../Reports/TransactionList';

/**
 * ModernReports - Mobile-first reports with sleek design
 * Inspired by Jupiter, Fi Money analytics sections
 */

export default function ModernReports({ onNavigate }) {
  const [activeSection, setActiveSection] = useState('overview'); // 'overview' | 'optimize' | 'transactions'
  const [analyticsData, setAnalyticsData] = useState(null);
  const [topMerchantsData, setTopMerchantsData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const app = useApp();
  const transactions = useMemo(() => {
    return app && Array.isArray(app.transactions) ? app.transactions : [];
  }, [app]);

  // Fetch analytics data
  useEffect(() => {
    const fetchAnalytics = async () => {
      try {
        setLoading(true);
        setError(null);
        const [summary, merchants] = await Promise.all([
          getSummary(),
          getTopMerchants({ limit: 10 })
        ]);
        setAnalyticsData(summary);
        setTopMerchantsData(merchants);
      } catch (err) {
        console.error('Error fetching analytics:', err);
        setError('Failed to load analytics data');
      } finally {
        setLoading(false);
      }
    };
    fetchAnalytics();
  }, []);

  // Calculate totals
  const totals = useMemo(() => {
    let income = 0;
    let outflow = 0;
    for (const t of transactions) {
      const amt = Number(t.amount || 0);
      if (t.type === 'income') income += amt;
      else outflow += amt;
    }
    return { income, outflow, net: income - outflow };
  }, [transactions]);

  const formatCurrency = (amount) => {
    if (amount >= 10000000) return `₹${(amount / 10000000).toFixed(2)}Cr`;
    if (amount >= 100000) return `₹${(amount / 100000).toFixed(2)}L`;
    if (amount >= 1000) return `₹${(amount / 1000).toFixed(1)}K`;
    return `₹${amount.toFixed(0)}`;
  };

  function handleDelete(index) {
    if (typeof app.setTransactions !== 'function') {
      alert('Cannot delete transaction');
      return;
    }
    if (!window.confirm('Delete this transaction?')) return;

    app.setTransactions(prev => {
      if (!Array.isArray(prev)) return prev;
      const copy = [...prev];
      copy.splice(index, 1);
      return copy;
    });
  }

  const sections = [
    { id: 'overview', label: 'Overview', icon: '📊' },
    { id: 'transactions', label: 'Transactions', icon: '💸' }
  ];

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 pb-24">
      {/* Sticky Header */}
      <div className="bg-white/80 backdrop-blur-md sticky top-0 z-20 border-b border-gray-100">
        <div className="max-w-lg mx-auto px-4 py-4">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h1 className="text-2xl font-bold text-gray-900">Reports</h1>
              <p className="text-sm text-gray-500 mt-1">Insights & Analytics</p>
            </div>
          </div>

          {/* Quick Stats */}
          <div className="grid grid-cols-3 gap-3 mb-4">
            <div className="bg-gradient-to-br from-green-50 to-emerald-50 rounded-xl p-3 border border-green-100">
              <div className="text-xs text-green-600 font-medium mb-1">Income</div>
              <div className="text-lg font-bold text-green-700">{formatCurrency(totals.income)}</div>
            </div>
            <div className="bg-gradient-to-br from-red-50 to-orange-50 rounded-xl p-3 border border-red-100">
              <div className="text-xs text-red-600 font-medium mb-1">Outflow</div>
              <div className="text-lg font-bold text-red-700">{formatCurrency(totals.outflow)}</div>
            </div>
            <div className={`bg-gradient-to-br ${totals.net >= 0 ? 'from-blue-50 to-indigo-50 border-blue-100' : 'from-gray-50 to-slate-50 border-gray-200'} rounded-xl p-3 border`}>
              <div className={`text-xs font-medium mb-1 ${totals.net >= 0 ? 'text-blue-600' : 'text-gray-600'}`}>Net</div>
              <div className={`text-lg font-bold ${totals.net >= 0 ? 'text-blue-700' : 'text-gray-700'}`}>{formatCurrency(Math.abs(totals.net))}</div>
            </div>
          </div>

          {/* Section Tabs */}
          <div className="flex gap-2 overflow-x-auto no-scrollbar">
            {sections.map(section => (
              <button
                key={section.id}
                onClick={() => setActiveSection(section.id)}
                className={`flex items-center gap-2 px-4 py-2 rounded-full text-sm font-medium transition-all whitespace-nowrap ${
                  activeSection === section.id
                    ? 'bg-purple-600 text-white shadow-md'
                    : 'bg-white text-gray-600 hover:bg-gray-50'
                }`}
              >
                <span>{section.icon}</span>
                <span>{section.label}</span>
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="max-w-lg mx-auto px-4 py-6">
        {/* Overview Section */}
        {activeSection === 'overview' && (
          <div className="space-y-4">
            {loading && (
              <div className="bg-white p-12 rounded-2xl shadow-sm text-center">
                <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-purple-600"></div>
                <p className="mt-4 text-gray-600 text-sm">Loading analytics...</p>
              </div>
            )}

            {error && !loading && (
              <div className="bg-red-50 border border-red-200 p-4 rounded-2xl">
                <p className="text-red-600 text-sm">{error}</p>
                <p className="text-red-500 text-xs mt-1">Using local data...</p>
              </div>
            )}

            {!loading && (
              <>
                {/* FIRE Calculator */}
                <FIRECalculator />

                {/* Emergency Fund Health Check */}
                <EmergencyFundHealth />

                {/* Backend Analytics Summary */}
                {analyticsData && (
                  <div className="bg-white rounded-2xl p-5 shadow-sm border border-gray-100">
                    <h3 className="text-base font-semibold text-gray-900 mb-4">Summary</h3>
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <div className="text-xs text-gray-500 mb-1">Total Transactions</div>
                        <div className="text-xl font-bold text-gray-900">{analyticsData.total_transactions}</div>
                      </div>
                      <div>
                        <div className="text-xs text-gray-500 mb-1">Period</div>
                        <div className="text-xs text-gray-700 mt-2">
                          {analyticsData.date_range?.start} to {analyticsData.date_range?.end}
                        </div>
                      </div>
                    </div>
                  </div>
                )}

                {/* Category Breakdown */}
                <div className="bg-white rounded-2xl p-5 shadow-sm border border-gray-100">
                  {analyticsData?.category_breakdown ? (
                    <>
                      <h3 className="text-base font-semibold text-gray-900 mb-4">Spend by Category</h3>
                      <div className="space-y-3">
                        {Object.entries(analyticsData.category_breakdown)
                          .filter(([cat]) => cat !== 'Income')
                          .sort((a, b) => b[1].total - a[1].total)
                          .map(([category, data], index) => {
                            const maxTotal = Math.max(...Object.entries(analyticsData.category_breakdown)
                              .filter(([cat]) => cat !== 'Income')
                              .map(([, val]) => val.total));
                            const percentage = (data.total / maxTotal) * 100;
                            const colors = ['bg-blue-500', 'bg-purple-500', 'bg-green-500', 'bg-yellow-500', 'bg-red-500'];

                            return (
                              <div key={category}>
                                <div className="flex justify-between items-center mb-1">
                                  <span className="text-sm font-medium text-gray-700">{category}</span>
                                  <div className="text-right">
                                    <span className="text-sm font-semibold text-gray-900">
                                      {formatCurrency(data.total)}
                                    </span>
                                    <span className="text-xs text-gray-500 ml-2">({data.count})</span>
                                  </div>
                                </div>
                                <div className="w-full bg-gray-200 rounded-full h-2">
                                  <div
                                    className={`${colors[index % colors.length]} h-2 rounded-full transition-all duration-500`}
                                    style={{ width: `${percentage}%` }}
                                  />
                                </div>
                              </div>
                            );
                          })}
                      </div>
                    </>
                  ) : (
                    <CategoryBreakdown transactions={transactions} />
                  )}
                </div>

                {/* Top Merchants */}
                <div className="bg-white rounded-2xl p-5 shadow-sm border border-gray-100">
                  <h3 className="text-base font-semibold text-gray-900 mb-4">Top Merchants</h3>
                  {topMerchantsData ? (
                    <div className="space-y-3">
                      {topMerchantsData.slice(0, 5).map((item, index) => {
                        const maxTotal = topMerchantsData[0]?.total_spend || 1;
                        const percentage = (item.total_spend / maxTotal) * 100;

                        return (
                          <div key={`${item.merchant}-${index}`} className="space-y-2">
                            <div className="flex justify-between items-center">
                              <div className="flex items-center gap-2 min-w-0 flex-1">
                                <span className="flex-shrink-0 w-6 h-6 rounded-full bg-purple-100 text-purple-600 text-xs font-bold flex items-center justify-center">
                                  {index + 1}
                                </span>
                                <span className="text-sm font-medium text-gray-700 truncate" title={item.merchant}>
                                  {item.merchant}
                                </span>
                              </div>
                              <span className="text-sm font-semibold text-gray-900 whitespace-nowrap ml-2">
                                {formatCurrency(item.total_spend)}
                              </span>
                            </div>
                            <div className="w-full bg-gray-200 rounded-full h-2">
                              <div
                                className="bg-purple-600 h-2 rounded-full transition-all duration-500"
                                style={{ width: `${percentage}%` }}
                              />
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  ) : (
                    <TopMerchants transactions={transactions} limit={5} />
                  )}
                </div>

                {/* Recurring Payments */}
                <div className="bg-white rounded-2xl p-5 shadow-sm border border-gray-100">
                  <RecurringPayments transactions={transactions} />
                </div>
              </>
            )}
          </div>
        )}

        {/* Transactions Section */}
        {activeSection === 'transactions' && (
          <div className="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden">
            <TransactionList transactions={transactions} onDelete={handleDelete} />
          </div>
        )}
      </div>
    </div>
  );
}
