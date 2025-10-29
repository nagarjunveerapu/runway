// src/components/Modern/ModernWealth.jsx
import React, { useState, useEffect } from 'react';
import { getDashboardSummary } from '../../api/services/dashboard';
import { getAccounts } from '../../api/services/accounts';
import NetWorthTimelineEnhanced from './NetWorthTimelineEnhanced';

/**
 * ModernWealth - Simplified Wealth Dashboard
 * One screen with net worth and direct action cards
 */

export default function ModernWealth({ onNavigate }) {
  const [dashboard, setDashboard] = useState(null);
  const [accounts, setAccounts] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      setLoading(true);
      const [dashboardData, accountsData] = await Promise.all([
        getDashboardSummary(),
        getAccounts()
      ]);
      setDashboard(dashboardData);
      setAccounts(accountsData);
    } catch (err) {
      console.error('Failed to load wealth data:', err);
    } finally {
      setLoading(false);
    }
  };

  const formatCurrency = (amount) => {
    if (amount >= 10000000) return `₹${(amount / 10000000).toFixed(2)}Cr`;
    if (amount >= 100000) return `₹${(amount / 100000).toFixed(2)}L`;
    if (amount >= 1000) return `₹${(amount / 1000).toFixed(1)}K`;
    return `₹${Math.round(amount).toLocaleString('en-IN')}`;
  };

  const netWorth = (dashboard?.total_assets || 0) - (dashboard?.total_liabilities || 0);
  const totalAccounts = accounts.length;
  const totalAccountBalance = accounts.reduce((sum, acc) => sum + (acc.balance || 0), 0);

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 pb-24">
      {/* Header */}
      <div className="bg-white/80 backdrop-blur-md sticky top-0 z-20 border-b border-gray-200">
        <div className="max-w-lg mx-auto px-4 py-6">
          <div className="flex items-center gap-3">
            <div className="bg-gradient-to-br from-green-500 to-emerald-600 text-white p-3 rounded-2xl">
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>
            <div>
              <h1 className="text-2xl font-bold text-gray-900">Wealth</h1>
              <p className="text-sm text-gray-500">Your financial overview</p>
            </div>
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="max-w-lg mx-auto px-4 py-6">
        {loading ? (
          <div className="bg-white p-12 rounded-2xl shadow-sm text-center">
            <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-green-600"></div>
            <p className="mt-4 text-gray-600 text-sm">Loading...</p>
          </div>
        ) : (
          <div className="space-y-4">
            {/* Net Worth Hero Card */}
            <div className="bg-gradient-to-br from-green-500 to-emerald-600 rounded-2xl p-6 shadow-lg text-white">
              <div className="text-sm font-medium mb-2 opacity-90">Total Net Worth</div>
              <div className="text-4xl font-bold mb-4">{formatCurrency(netWorth)}</div>
              <div className="flex justify-between items-center pt-4 border-t border-green-400/30">
                <div>
                  <div className="text-xs opacity-75">Assets</div>
                  <div className="text-lg font-semibold">{formatCurrency(dashboard?.total_assets || 0)}</div>
                </div>
                <div className="text-3xl opacity-50">−</div>
                <div>
                  <div className="text-xs opacity-75">Liabilities</div>
                  <div className="text-lg font-semibold">{formatCurrency(dashboard?.total_liabilities || 0)}</div>
                </div>
              </div>
            </div>

            {/* Quick Stats Grid */}
            <div className="grid grid-cols-2 gap-3">
              <div className="bg-white rounded-xl p-4 shadow-sm border border-gray-100">
                <div className="text-2xl mb-2">🏦</div>
                <div className="text-2xl font-bold text-gray-900">{totalAccounts}</div>
                <div className="text-xs text-gray-500">Bank Accounts</div>
                <div className="text-sm font-medium text-gray-700 mt-1">{formatCurrency(totalAccountBalance)}</div>
              </div>

              <div className="bg-white rounded-xl p-4 shadow-sm border border-gray-100">
                <div className="text-2xl mb-2">💎</div>
                <div className="text-2xl font-bold text-gray-900">{Object.keys(dashboard?.assets_breakdown || {}).length}</div>
                <div className="text-xs text-gray-500">Asset Types</div>
                <div className="text-sm font-medium text-gray-700 mt-1">{formatCurrency(dashboard?.total_assets || 0)}</div>
              </div>
            </div>

            {/* Net Worth Timeline Chart */}
            <NetWorthTimelineEnhanced />

            {/* Action Cards */}
            <div className="bg-white rounded-2xl p-5 shadow-sm border border-gray-100">
              <h3 className="text-base font-semibold text-gray-900 mb-4">Manage Your Wealth</h3>
              <div className="space-y-3">
                <button
                  onClick={() => onNavigate('assets')}
                  className="w-full flex items-center justify-between bg-gradient-to-r from-blue-50 to-indigo-50 hover:from-blue-100 hover:to-indigo-100 text-blue-900 px-4 py-4 rounded-xl transition-all border border-blue-200"
                >
                  <div className="flex items-center gap-3">
                    <div className="text-2xl">💎</div>
                    <div className="text-left">
                      <div className="font-semibold">Assets</div>
                      <div className="text-xs opacity-75">Manage your investments & property</div>
                    </div>
                  </div>
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                  </svg>
                </button>

                <button
                  onClick={() => onNavigate('liabilities')}
                  className="w-full flex items-center justify-between bg-gradient-to-r from-red-50 to-orange-50 hover:from-red-100 hover:to-orange-100 text-red-900 px-4 py-4 rounded-xl transition-all border border-red-200"
                >
                  <div className="flex items-center gap-3">
                    <div className="text-2xl">📋</div>
                    <div className="text-left">
                      <div className="font-semibold">Liabilities</div>
                      <div className="text-xs opacity-75">Track loans & debts</div>
                    </div>
                  </div>
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                  </svg>
                </button>

                <button
                  onClick={() => onNavigate('accounts')}
                  className="w-full flex items-center justify-between bg-gradient-to-r from-purple-50 to-pink-50 hover:from-purple-100 hover:to-pink-100 text-purple-900 px-4 py-4 rounded-xl transition-all border border-purple-200"
                >
                  <div className="flex items-center gap-3">
                    <div className="text-2xl">🏦</div>
                    <div className="text-left">
                      <div className="font-semibold">Accounts</div>
                      <div className="text-xs opacity-75">Manage bank accounts</div>
                    </div>
                  </div>
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                  </svg>
                </button>

                <button
                  onClick={() => onNavigate('reports')}
                  className="w-full flex items-center justify-between bg-gradient-to-r from-green-50 to-emerald-50 hover:from-green-100 hover:to-emerald-100 text-green-900 px-4 py-4 rounded-xl transition-all border border-green-200"
                >
                  <div className="flex items-center gap-3">
                    <div className="text-2xl">📈</div>
                    <div className="text-left">
                      <div className="font-semibold">Reports & Analytics</div>
                      <div className="text-xs opacity-75">View spending insights</div>
                    </div>
                  </div>
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                  </svg>
                </button>
              </div>
            </div>

            {/* Asset Breakdown */}
            {dashboard?.assets_breakdown && Object.keys(dashboard.assets_breakdown).length > 0 && (
              <div className="bg-white rounded-2xl p-5 shadow-sm border border-gray-100">
                <h3 className="text-base font-semibold text-gray-900 mb-4">Asset Allocation</h3>
                <div className="space-y-3">
                  {Object.entries(dashboard.assets_breakdown)
                    .sort((a, b) => b[1] - a[1])
                    .map(([type, amount]) => {
                      const percentage = ((amount / dashboard.total_assets) * 100).toFixed(1);
                      return (
                        <div key={type}>
                          <div className="flex justify-between items-center mb-2">
                            <span className="text-sm font-medium text-gray-700">{type}</span>
                            <div className="text-right">
                              <div className="text-sm font-semibold text-gray-900">{formatCurrency(amount)}</div>
                              <div className="text-xs text-gray-500">{percentage}%</div>
                            </div>
                          </div>
                          <div className="w-full bg-gray-200 rounded-full h-2">
                            <div
                              className="bg-gradient-to-r from-green-500 to-emerald-500 h-2 rounded-full transition-all duration-500"
                              style={{ width: `${percentage}%` }}
                            />
                          </div>
                        </div>
                      );
                    })}
                </div>
              </div>
            )}

            {/* Recent Accounts */}
            {accounts.length > 0 && (
              <div className="bg-white rounded-2xl p-5 shadow-sm border border-gray-100">
                <div className="flex justify-between items-center mb-4">
                  <h3 className="text-base font-semibold text-gray-900">Bank Accounts</h3>
                  <button
                    onClick={() => onNavigate('accounts')}
                    className="text-xs text-green-600 font-medium hover:text-green-700"
                  >
                    View All →
                  </button>
                </div>
                <div className="space-y-3">
                  {accounts.slice(0, 3).map((account) => (
                    <div key={account.account_id} className="flex justify-between items-center p-3 bg-gray-50 rounded-lg">
                      <div>
                        <div className="font-medium text-gray-900">{account.account_name}</div>
                        <div className="text-xs text-gray-500">{account.bank_name} • {account.account_type}</div>
                      </div>
                      <div className="text-right">
                        <div className="font-semibold text-gray-900">{formatCurrency(account.balance)}</div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
