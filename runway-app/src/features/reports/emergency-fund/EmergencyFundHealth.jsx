// src/components/Reports/EmergencyFundHealth.jsx
import React, { useState, useEffect } from 'react';
import { getEmergencyFundHealth } from '../../../api/services/emergencyFund';
import { LoadingSpinner, Card } from '../../../shared/ui';
import { formatCurrency as formatCurrencyUtil } from '../../../shared/utils/formatters';

/**
 * Emergency Fund Health Check - Ensures adequate liquid emergency fund
 * Beautiful visualization showing health score, months covered, and recommendations
 */

export default function EmergencyFundHealth() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        setError(null);
        const result = await getEmergencyFundHealth();
        setData(result);
      } catch (err) {
        console.error('Failed to fetch emergency fund health:', err);
        if (err.message?.includes('Network') || err.code === 'ERR_NETWORK') {
          setError('Backend endpoint not responding. Check if backend is running.');
        } else {
          setError(err.message || 'Failed to load emergency fund health');
        }
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, []);

  const formatCurrency = (amount) => {
    if (!amount && amount !== 0) return '₹0';
    const numAmount = Number(amount);
    if (isNaN(numAmount)) return '₹0';
    if (numAmount >= 10000000) return `₹${(numAmount / 10000000).toFixed(2)}Cr`;
    if (numAmount >= 100000) return `₹${(numAmount / 100000).toFixed(2)}L`;
    if (numAmount >= 1000) return `₹${(numAmount / 1000).toFixed(1)}K`;
    return `₹${numAmount.toFixed(0)}`;
  };

  const getStatusIcon = (statusColor) => {
    switch (statusColor) {
      case 'green':
        return '🛡️';
      case 'blue':
        return '✅';
      case 'yellow':
        return '⚠️';
      case 'orange':
        return '🚨';
      case 'red':
        return '💥';
      default:
        return '📊';
    }
  };

  if (loading) {
    return (
      <Card>
        <LoadingSpinner text="Analyzing emergency fund..." />
      </Card>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 rounded-2xl p-6 shadow-md border border-red-200">
        <div className="text-red-800 font-semibold mb-2">⚠️ Unable to Calculate Emergency Fund Health</div>
        <div className="text-red-600 text-sm">{error}</div>
      </div>
    );
  }

  if (!data) return null;

  const {
    liquid_assets,
    avg_monthly_expenses,
    months_covered,
    recommended_3m,
    recommended_6m,
    recommended_12m,
    health_score,
    status,
    status_color,
    recommendation,
    liquidity_ratio,
    shortfall_3m,
    shortfall_6m,
    shortfall_12m
  } = data;

  const statusIcon = getStatusIcon(status_color);

  return (
    <div className="bg-gradient-to-br from-blue-50 via-cyan-50 to-teal-50 rounded-2xl p-6 shadow-lg border-2 border-blue-200">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h3 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
            <span className="text-4xl">{statusIcon}</span>
            <span>Emergency Fund Health</span>
          </h3>
          <p className="text-sm text-gray-600 mt-1">Your financial safety net</p>
        </div>
        <div className={`px-4 py-2 rounded-full font-semibold text-sm ${
          status_color === 'green' ? 'bg-green-100 text-green-800' :
          status_color === 'blue' ? 'bg-blue-100 text-blue-800' :
          status_color === 'yellow' ? 'bg-yellow-100 text-yellow-800' :
          status_color === 'orange' ? 'bg-orange-100 text-orange-800' :
          'bg-red-100 text-red-800'
        }`}>
          {status}
        </div>
      </div>

      {/* Health Score Gauge */}
      <div className="mb-6">
        <div className="flex items-center justify-between mb-2">
          <div className="text-sm font-medium text-gray-700">Health Score</div>
          <div className={`text-3xl font-black ${
            status_color === 'green' ? 'text-green-600' :
            status_color === 'blue' ? 'text-blue-600' :
            status_color === 'yellow' ? 'text-yellow-600' :
            status_color === 'orange' ? 'text-orange-600' :
            'text-red-600'
          }`}>
            {health_score}%
          </div>
        </div>
        <div className="w-full h-6 bg-gray-200 rounded-full overflow-hidden">
          <div
            className={`h-full bg-gradient-to-r transition-all duration-1000 ease-out ${
              status_color === 'green' ? 'from-green-500 to-emerald-500' :
              status_color === 'blue' ? 'from-blue-500 to-cyan-500' :
              status_color === 'yellow' ? 'from-yellow-500 to-amber-500' :
              status_color === 'orange' ? 'from-orange-500 to-red-500' :
              'from-red-500 to-pink-500'
            }`}
            style={{ width: `${Math.min(health_score, 150)}%` }}
          />
        </div>
      </div>

      {/* Key Metrics */}
      <div className="grid grid-cols-2 gap-4 mb-6">
        <div className="bg-white rounded-xl p-4 shadow-sm border border-gray-100">
          <div className="text-xs text-gray-500 mb-1">Liquid Assets</div>
          <div className="text-xl font-bold text-blue-600">
            {formatCurrency(liquid_assets)}
          </div>
          <div className="text-xs text-gray-400 mt-1">{months_covered.toFixed(1)} months covered</div>
        </div>

        <div className="bg-white rounded-xl p-4 shadow-sm border border-gray-100">
          <div className="text-xs text-gray-500 mb-1">Monthly Expenses</div>
          <div className="text-xl font-bold text-gray-900">
            {formatCurrency(avg_monthly_expenses)}
          </div>
          <div className="text-xs text-gray-400 mt-1">6-month average</div>
        </div>
      </div>

      {/* Recommended Targets */}
      <div className="bg-white/80 rounded-xl p-4 mb-4">
        <div className="text-sm font-semibold text-gray-900 mb-3">Recommended Targets</div>
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <div className="text-sm text-gray-600">Minimum (3 months):</div>
            <div className={`font-semibold ${liquid_assets >= recommended_3m ? 'text-green-600' : 'text-red-600'}`}>
              {formatCurrency(recommended_3m)}
            </div>
          </div>
          <div className="flex items-center justify-between">
            <div className="text-sm text-gray-600">Moderate (6 months):</div>
            <div className={`font-semibold ${liquid_assets >= recommended_6m ? 'text-green-600' : 'text-orange-600'}`}>
              {formatCurrency(recommended_6m)}
            </div>
          </div>
          <div className="flex items-center justify-between">
            <div className="text-sm text-gray-600">Conservative (12 months):</div>
            <div className={`font-semibold ${liquid_assets >= recommended_12m ? 'text-green-600' : 'text-yellow-600'}`}>
              {formatCurrency(recommended_12m)}
            </div>
          </div>
        </div>
      </div>

      {/* Additional Metrics */}
      <div className="grid grid-cols-2 gap-4 mb-4">
        <div className="bg-white rounded-xl p-3 shadow-sm border border-gray-100">
          <div className="text-xs text-gray-500 mb-1">Liquidity Ratio</div>
          <div className="text-lg font-bold text-indigo-600">
            {liquidity_ratio.toFixed(1)}%
          </div>
          <div className="text-xs text-gray-400 mt-1">of total assets</div>
        </div>

        <div className="bg-white rounded-xl p-3 shadow-sm border border-gray-100">
          <div className="text-xs text-gray-500 mb-1">Shortfall (6m)</div>
          <div className="text-lg font-bold text-red-600">
            {formatCurrency(shortfall_6m)}
          </div>
          <div className="text-xs text-gray-400 mt-1">to reach target</div>
        </div>
      </div>

      {/* Recommendation */}
      <div className={`bg-gradient-to-r ${
        status_color === 'green' ? 'from-green-500 to-emerald-500' :
        status_color === 'blue' ? 'from-blue-500 to-cyan-500' :
        status_color === 'yellow' ? 'from-yellow-500 to-amber-500' :
        status_color === 'orange' ? 'from-orange-500 to-red-500' :
        'from-red-500 to-pink-500'
      } rounded-xl p-4 text-white`}>
        <div className="flex items-start gap-3">
          <span className="text-2xl">{statusIcon}</span>
          <div>
            <div className="font-semibold mb-1">{status}</div>
            <div className="text-xs text-white/90">{recommendation}</div>
          </div>
        </div>
      </div>
    </div>
  );
}
