// src/components/Modern/InvestmentOptimizer.jsx
import React, { useState, useEffect } from 'react';
import { analyzeInvestments } from '../../api/services/investmentOptimizer';
import { detectOrRefreshPatterns } from '../../api/services/salarySweepV2';

export default function InvestmentOptimizer() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      setLoading(true);
      setError(null);
      const analysis = await analyzeInvestments();
      setData(analysis);
    } catch (err) {
      console.error('Failed to load investment analysis:', err);
      setError('Failed to load investment data');
    } finally {
      setLoading(false);
    }
  };

  const formatCurrency = (amount) => {
    if (!amount) return '₹0';
    return `₹${Math.round(amount).toLocaleString('en-IN')}`;
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-purple-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Analyzing your investments...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="text-center py-20">
        <div className="text-red-600 text-6xl mb-4">❌</div>
        <h3 className="text-lg font-bold text-gray-900 mb-2">Error Loading Data</h3>
        <p className="text-gray-600 mb-4">{error}</p>
        <button
          onClick={loadData}
          className="bg-purple-600 text-white px-6 py-2 rounded-lg font-medium"
        >
          Retry
        </button>
      </div>
    );
  }

  if (!data) return null;

  const { summary, portfolio_allocation, sips, insights } = data;

  return (
    <div className="space-y-6">
      <div className="bg-gradient-to-br from-purple-500 to-indigo-600 rounded-3xl p-6 text-white">
        <div className="flex items-center gap-3 mb-4">
          <div className="text-4xl">📈</div>
          <div>
            <h2 className="text-2xl font-bold">Investment Summary</h2>
            <p className="text-purple-100">Your portfolio overview</p>
          </div>
        </div>

        <div className="flex gap-3">
          <button
            onClick={async () => {
              try {
                const res = await detectOrRefreshPatterns();
                const newInvestments = (res?.emis || []).filter(e => e.category === 'Investment');
                // Simple feedback; could be replaced with toast
                alert(`Identified ${newInvestments.length} potential investment pattern(s). Review in Salary Sweep.`);
                await loadData();
              } catch (e) {
                console.error('Detect investments failed', e);
                alert('Failed to identify investments. Please try again.');
              }
            }}
            className="bg-white/20 hover:bg-white/30 transition text-white px-4 py-2 rounded-lg text-sm font-medium border border-white/20"
          >
            Identify new investments
          </button>
        </div>

        <div className="grid grid-cols-2 gap-4 mt-6">
          <div className="bg-white/20 backdrop-blur-md rounded-2xl p-4">
            <div className="text-sm text-purple-100 mb-1">Total Invested</div>
            <div className="text-3xl font-bold">{formatCurrency(summary.total_invested)}</div>
          </div>
          <div className="bg-white/20 backdrop-blur-md rounded-2xl p-4">
            <div className="text-sm text-purple-100 mb-1">Total Transactions</div>
            <div className="text-3xl font-bold">{summary.total_transactions}</div>
          </div>
          <div className="bg-white/20 backdrop-blur-md rounded-2xl p-4">
            <div className="text-sm text-purple-100 mb-1">SIPs Active</div>
            <div className="text-3xl font-bold">{summary.sip_count}</div>
          </div>
          <div className="bg-white/20 backdrop-blur-md rounded-2xl p-4">
            <div className="text-sm text-purple-100 mb-1">SIP Investment</div>
            <div className="text-3xl font-bold">{formatCurrency(summary.total_sip_investment)}</div>
          </div>
        </div>
      </div>

      {summary.platforms && summary.platforms.length > 0 && (
        <div className="bg-white rounded-2xl p-5 border border-gray-200">
          <h3 className="text-lg font-bold text-gray-900 mb-4">Investment Platforms</h3>
          <div className="space-y-3">
            {summary.platforms.map((platform, idx) => (
              <div key={idx} className="flex items-center justify-between p-3 bg-gray-50 rounded-xl">
                <div>
                  <div className="font-semibold text-gray-900">{platform.name}</div>
                  <div className="text-sm text-gray-600">{platform.transaction_count} transactions</div>
                </div>
                <div className="text-lg font-bold text-purple-600">
                  {formatCurrency(platform.total_invested)}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {portfolio_allocation && portfolio_allocation.total > 0 && (
        <div className="bg-white rounded-2xl p-5 border border-gray-200">
          <h3 className="text-lg font-bold text-gray-900 mb-4">Portfolio Allocation</h3>
          <div className="space-y-3">
            {portfolio_allocation.equity > 0 && (
              <div>
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm font-medium text-gray-700">Equity</span>
                  <span className="text-sm font-bold text-blue-600">
                    {formatCurrency(portfolio_allocation.equity)}
                    ({((portfolio_allocation.equity / portfolio_allocation.total) * 100).toFixed(0)}%)
                  </span>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-2">
                  <div
                    className="bg-blue-600 h-2 rounded-full"
                    style={{ width: `${(portfolio_allocation.equity / portfolio_allocation.total) * 100}%` }}
                  />
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {insights && insights.length > 0 && (
        <div className="bg-white rounded-2xl p-5 border border-gray-200">
          <h3 className="text-lg font-bold text-gray-900 mb-4">💡 Insights</h3>
          <div className="space-y-3">
            {insights.map((insight, idx) => (
              <div
                key={idx}
                className={`p-4 rounded-xl border-2 ${
                  insight.type === 'opportunity'
                    ? 'bg-blue-50 border-blue-200'
                    : insight.type === 'warning'
                    ? 'bg-orange-50 border-orange-200'
                    : 'bg-gray-50 border-gray-200'
                }`}
              >
                <div className="flex items-start gap-3">
                  <span className="text-2xl">
                    {insight.type === 'opportunity' ? '💡' : insight.type === 'warning' ? '⚠️' : 'ℹ️'}
                  </span>
                  <div className="flex-1">
                    <h4 className="font-semibold text-gray-900 mb-1">{insight.title}</h4>
                    <p className="text-sm text-gray-600">{insight.message}</p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

