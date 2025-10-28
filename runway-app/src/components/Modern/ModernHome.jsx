// src/components/Modern/ModernHome.jsx
import React, { useState, useEffect } from 'react';
import { getDashboardSummary } from '../../api/services/dashboard';

/**
 * ModernHome - Mobile-first, sleek, gamified home screen
 * Now powered by Dashboard API for real-time financial insights
 */

export default function ModernHome({ onNavigate }) {
  const [dashboard, setDashboard] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Fetch dashboard data from API
  useEffect(() => {
    const fetchDashboard = async () => {
      try {
        setLoading(true);
        setError(null);
        const data = await getDashboardSummary();
        setDashboard(data);
      } catch (err) {
        console.error('Failed to fetch dashboard:', err);
        setError(err.message || 'Failed to load dashboard data');
      } finally {
        setLoading(false);
      }
    };

    fetchDashboard();
  }, []);

  const formatCurrency = (amount) => {
    if (!amount) return '₹0';
    if (amount >= 10000000) return `₹${(amount / 10000000).toFixed(2)}Cr`;
    if (amount >= 100000) return `₹${(amount / 100000).toFixed(2)}L`;
    if (amount >= 1000) return `₹${(amount / 1000).toFixed(1)}K`;
    return `₹${amount.toFixed(0)}`;
  };

  const getHealthColor = (message) => {
    if (message.includes('Excellent')) return { text: 'Excellent! 🎉', color: 'text-green-500', bg: 'bg-green-50' };
    if (message.includes('Good')) return { text: 'Good Progress 👍', color: 'text-blue-500', bg: 'bg-blue-50' };
    if (message.includes('Building')) return { text: 'Building Up 💪', color: 'text-yellow-500', bg: 'bg-yellow-50' };
    return { text: 'Getting Started 🌱', color: 'text-orange-500', bg: 'bg-orange-50' };
  };

  const getInsightIcon = (type) => {
    switch (type) {
      case 'success': return '🎉';
      case 'warning': return '⚠️';
      case 'info': return 'ℹ️';
      case 'tip': return '💡';
      default: return '📊';
    }
  };

  const getInsightColor = (type) => {
    switch (type) {
      case 'success': return 'from-green-500 to-emerald-600';
      case 'warning': return 'from-orange-500 to-red-600';
      case 'info': return 'from-blue-500 to-indigo-600';
      case 'tip': return 'from-purple-500 to-pink-600';
      default: return 'from-gray-500 to-gray-600';
    }
  };

  // Loading state
  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 pb-24 flex items-center justify-center">
        <div className="text-center">
          <div className="w-16 h-16 border-4 border-purple-500 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
          <div className="text-gray-600">Loading your financial dashboard...</div>
        </div>
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 pb-24 flex items-center justify-center">
        <div className="max-w-lg mx-auto px-4">
          <div className="bg-red-50 border border-red-200 rounded-2xl p-6 text-center">
            <div className="text-4xl mb-3">⚠️</div>
            <div className="text-red-900 font-semibold mb-2">Failed to Load Dashboard</div>
            <div className="text-red-700 text-sm mb-4">{error}</div>
            <button
              onClick={() => window.location.reload()}
              className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700"
            >
              Retry
            </button>
          </div>
        </div>
      </div>
    );
  }

  if (!dashboard) return null;

  const { 
    health_score, 
    health_message, 
    current_month, 
    assets, 
    liabilities,
    true_net_worth,
    liquid_assets,
    runway_months,
    debt_to_asset_ratio,
    insights, 
    net_worth, 
    total_transactions 
  } = dashboard;
  const health = getHealthColor(health_message);

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 pb-24">
      {/* Minimal Top Bar */}
      <div className="bg-white/80 backdrop-blur-md sticky top-0 z-20 border-b border-gray-100">
        <div className="max-w-lg mx-auto px-4 py-3 flex items-center justify-between">
          <div>
            <div className="text-sm text-gray-500">Hey there! 👋</div>
            <div className="text-lg font-bold text-gray-900">Your Finances</div>
          </div>
          <div className="flex items-center gap-2">
            <button className="w-10 h-10 rounded-full bg-gradient-to-br from-purple-500 to-indigo-500 flex items-center justify-center text-white text-sm font-bold">
              {health_score}
            </button>
            <button
              onClick={() => onNavigate('profile')}
              className="w-10 h-10 rounded-full bg-gray-100 flex items-center justify-center text-gray-700 hover:bg-gray-200 active:scale-95 transition-all"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
              </svg>
            </button>
          </div>
        </div>
      </div>

      <div className="max-w-lg mx-auto px-4 py-6 space-y-4">
        {/* Hero Card - Financial Health Score */}
        <div className={`${health.bg} rounded-3xl p-6 shadow-lg border border-gray-200`}>
          <div className="flex items-center justify-between mb-4">
            <div className={`text-sm font-medium ${health.color}`}>Financial Health</div>
            <div className={`text-xs px-2 py-1 rounded-full ${health.bg} border ${health.color}`}>
              This Month
            </div>
          </div>

          <div className="flex items-end gap-2 mb-2">
            <div className={`text-5xl font-black ${health.color}`}>{health_score}</div>
            <div className="text-xl text-gray-500 mb-1">/100</div>
          </div>

          <div className={`text-base font-semibold ${health.color} mb-4`}>{health.text}</div>

          {/* Progress Bar */}
          <div className="w-full h-2 bg-white/50 rounded-full overflow-hidden">
            <div
              className={`h-full ${health.color.replace('text', 'bg')} rounded-full transition-all duration-1000`}
              style={{ width: `${health_score}%` }}
            />
          </div>
        </div>

        {/* Quick Stats Grid */}
        <div className="grid grid-cols-2 gap-4">
          {/* Savings Rate */}
          <div
            className="bg-white rounded-2xl p-4 shadow-sm border border-gray-100 active:scale-95 transition-transform cursor-pointer"
            onClick={() => onNavigate('reports')}
          >
            <div className="text-xs text-gray-500 mb-2">Savings Rate</div>
            <div className={`text-2xl font-bold ${current_month.savings_rate >= 20 ? 'text-green-600' : 'text-orange-600'}`}>
              {current_month.savings_rate.toFixed(1)}%
            </div>
            <div className="text-xs text-gray-400 mt-1">
              {current_month.savings_rate >= 20 ? '✨ Superb!' : '📈 Room to grow'}
            </div>
          </div>

          {/* Net Savings */}
          <div
            className="bg-white rounded-2xl p-4 shadow-sm border border-gray-100 active:scale-95 transition-transform cursor-pointer"
            onClick={() => onNavigate('reports')}
          >
            <div className="text-xs text-gray-500 mb-2">This Month</div>
            <div className={`text-2xl font-bold ${current_month.net_savings >= 0 ? 'text-green-600' : 'text-red-600'}`}>
              {formatCurrency(Math.abs(current_month.net_savings))}
            </div>
            <div className="text-xs text-gray-400 mt-1">
              {current_month.net_savings >= 0 ? '💰 Saved' : '💸 Deficit'}
            </div>
          </div>
        </div>

        {/* Assets Widget */}
        {assets.total_value > 0 ? (
          <div className="bg-white rounded-2xl p-5 shadow-sm border border-gray-100">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-2">
                <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-blue-500 to-indigo-500 flex items-center justify-center">
                  <svg className="w-4 h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" />
                  </svg>
                </div>
                <div className="text-sm font-semibold text-gray-700">My Assets</div>
              </div>
              <div className="flex gap-2">
                <button
                  className="text-xs text-indigo-600 font-medium hover:text-indigo-700"
                  onClick={() => onNavigate('assets')}
                >
                  Assets →
                </button>
                <button
                  className="text-xs text-red-600 font-medium hover:text-red-700"
                  onClick={() => onNavigate('liabilities')}
                >
                  Liabilities →
                </button>
              </div>
            </div>

            <div className="mb-3">
              <div className="text-xs text-gray-500 mb-1">True Net Worth</div>
              <div className={`text-3xl font-bold ${true_net_worth >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                {formatCurrency(true_net_worth)}
              </div>
              {liabilities && liabilities.total_outstanding > 0 && (
                <div className="text-xs text-gray-500 mt-1">
                  Assets: {formatCurrency(assets.total_value)} - Liabilities: {formatCurrency(liabilities.total_outstanding)}
                </div>
              )}
            </div>

            <div className="flex items-center gap-2 mb-3">
              <div className="flex-1 h-2 bg-gray-100 rounded-full overflow-hidden">
                <div className="h-full bg-gradient-to-r from-blue-500 to-indigo-500 rounded-full" style={{ width: '75%' }}></div>
              </div>
              <div className="text-xs text-gray-500">{assets.count} assets</div>
            </div>

            {/* Top 2 Assets Preview */}
            {assets.top_assets.slice(0, 2).map((asset, idx) => (
              <div key={idx} className="flex items-center justify-between py-2 border-t border-gray-100">
                <div className="flex items-center gap-2">
                  <span className="text-lg">{asset.type === 'property' ? '🏠' : asset.type === 'vehicle' ? '🚗' : '💎'}</span>
                  <div>
                    <div className="text-sm font-medium text-gray-900">{asset.name}</div>
                    <div className="text-xs text-gray-500">
                      {asset.purchase_date ? new Date(asset.purchase_date).getFullYear() : 'N/A'}
                    </div>
                  </div>
                </div>
                <div className="text-sm font-semibold text-gray-900">
                  {formatCurrency(asset.value)}
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="bg-gradient-to-br from-blue-50 to-indigo-50 rounded-2xl p-5 border-2 border-dashed border-blue-200">
            <div className="flex items-start gap-3">
              <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-blue-500 to-indigo-500 flex items-center justify-center flex-shrink-0">
                <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                </svg>
              </div>
              <div className="flex-1">
                <div className="text-sm font-semibold text-gray-900 mb-1">Track Your Assets</div>
                <div className="text-xs text-gray-600 mb-3">
                  Add your property, vehicles, and other assets to track your net worth
                </div>
                <button
                  onClick={() => onNavigate('assets')}
                  className="px-4 py-2 bg-gradient-to-r from-blue-500 to-indigo-500 text-white text-xs font-medium rounded-lg hover:from-blue-600 hover:to-indigo-600 active:scale-95 transition-all"
                >
                  Add Your First Asset
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Financial Runway Card */}
        {liquid_assets > 0 && runway_months && runway_months !== Infinity && (
          <div className="bg-gradient-to-br from-green-50 to-emerald-50 rounded-2xl p-5 border border-green-200 shadow-sm">
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2">
                <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-green-500 to-emerald-500 flex items-center justify-center">
                  {runway_months >= 12 ? '🛫' : runway_months >= 6 ? '✈️' : '⚠️'}
                </div>
                <div className="text-sm font-semibold text-green-900">Financial Runway</div>
              </div>
              <div className={`text-xs font-medium px-2 py-1 rounded-full ${
                runway_months >= 12 ? 'bg-green-100 text-green-700' : 
                runway_months >= 6 ? 'bg-yellow-100 text-yellow-700' : 
                'bg-red-100 text-red-700'
              }`}>
                {runway_months >= 12 ? 'Strong' : runway_months >= 6 ? 'Moderate' : 'Low'}
              </div>
            </div>
            <div className="text-3xl font-bold text-green-600 mb-1">
              {runway_months.toFixed(1)} months
            </div>
            <div className="text-xs text-green-700 mb-2">
              Liquid Assets: {formatCurrency(liquid_assets)}
            </div>
            <div className="text-xs text-green-600">
              Months you can sustain without income
            </div>
          </div>
        )}

        {/* Debt-to-Asset Ratio Card */}
        {assets.total_value > 0 && (
          <div className="bg-gradient-to-br from-purple-50 to-indigo-50 rounded-2xl p-5 border border-purple-200 shadow-sm">
            <div className="flex items-center justify-between mb-3">
              <div className="text-sm font-semibold text-purple-900">Debt-to-Asset Ratio</div>
              <div className={`text-xs font-medium px-2 py-1 rounded-full ${
                debt_to_asset_ratio < 30 ? 'bg-green-100 text-green-700' : 
                debt_to_asset_ratio < 50 ? 'bg-yellow-100 text-yellow-700' : 
                'bg-red-100 text-red-700'
              }`}>
                {debt_to_asset_ratio < 30 ? 'Healthy ✓' : debt_to_asset_ratio < 50 ? 'Moderate' : 'High Risk'}
              </div>
            </div>
            <div className={`text-3xl font-bold ${debt_to_asset_ratio < 30 ? 'text-green-600' : debt_to_asset_ratio < 50 ? 'text-yellow-600' : 'text-red-600'}`}>
              {debt_to_asset_ratio.toFixed(1)}%
            </div>
            <div className="text-xs text-purple-600 mt-2">
              Ideal: &lt; 30%
            </div>
          </div>
        )}

        {/* Insights from API */}
        {insights && insights.length > 0 && (
          <div className="space-y-3">
            <div className="text-sm font-semibold text-gray-700 px-1">Insights for You</div>

            {insights.map((insight, idx) => (
              <div
                key={idx}
                className={`bg-gradient-to-br ${getInsightColor(insight.type)} rounded-2xl p-5 shadow-lg active:scale-98 transition-transform ${insight.action ? 'cursor-pointer' : ''}`}
                onClick={() => insight.action && onNavigate(insight.action)}
              >
                <div className="flex items-start justify-between mb-3">
                  <div className="flex items-center gap-2">
                    <div className="w-10 h-10 rounded-xl bg-white/20 backdrop-blur-sm flex items-center justify-center">
                      <span className="text-2xl">{getInsightIcon(insight.type)}</span>
                    </div>
                    <div className="text-white">
                      <div className="font-semibold">{insight.title}</div>
                      <div className="text-xs text-white/70">{insight.type}</div>
                    </div>
                  </div>
                  {insight.action && (
                    <div className="w-6 h-6 rounded-full bg-white/20 flex items-center justify-center">
                      <svg className="w-4 h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                      </svg>
                    </div>
                  )}
                </div>
                <div className="text-white/90 text-sm">
                  {insight.description}
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Recent Activity Teaser */}
        {total_transactions > 0 && (
          <div className="bg-white rounded-2xl p-5 shadow-sm border border-gray-100">
            <div className="flex items-center justify-between mb-3">
              <div className="text-sm font-semibold text-gray-700">Activity</div>
              <button
                className="text-xs text-indigo-600 font-medium"
                onClick={() => onNavigate('reports')}
              >
                See All →
              </button>
            </div>
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-full bg-green-100 flex items-center justify-center">
                <span className="text-lg">💸</span>
              </div>
              <div className="flex-1">
                <div className="text-sm font-medium text-gray-900">
                  {total_transactions} transactions tracked
                </div>
                <div className="text-xs text-gray-500">All time activity</div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
