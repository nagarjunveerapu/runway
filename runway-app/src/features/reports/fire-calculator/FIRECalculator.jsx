// src/components/Reports/FIRECalculator.jsx
import React, { useState, useEffect } from 'react';
import { getFIREMetrics } from '../../../api/services/fire';
import { LoadingSpinner, Card } from '../../../shared/ui';
import { formatCurrency as formatCurrencyUtil } from '../../../shared/utils/formatters';

/**
 * FIRE Calculator - Financial Independence, Retire Early
 * Beautiful visualization showing months to FIRE, target corpus, and progress
 */

export default function FIRECalculator() {
  const [metrics, setMetrics] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchMetrics = async () => {
      try {
        setLoading(true);
        setError(null);
        const data = await getFIREMetrics();
        setMetrics(data);
      } catch (err) {
        console.error('Failed to fetch FIRE metrics:', err);
        // Set a fallback error message if it's a network error
        if (err.message?.includes('Network') || err.code === 'ERR_NETWORK' || err.response?.status === 500) {
          setError('Backend endpoint not responding. Check if backend is running with the fire_calculator module.');
        } else {
          setError(err.message || 'Failed to load FIRE metrics');
        }
      } finally {
        setLoading(false);
      }
    };

    fetchMetrics();
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

  const safeToFixed = (value, decimals = 1) => {
    if (value === null || value === undefined || isNaN(value)) return 'N/A';
    return value.toFixed(decimals);
  };

  const safeNumber = (value, fallback = 0) => {
    if (value === null || value === undefined || isNaN(value)) return fallback;
    return Number(value);
  };

  const getStatusColor = (yearsToFire) => {
    if (yearsToFire === Infinity || yearsToFire > 30) return 'from-red-500 to-orange-500';
    if (yearsToFire <= 5) return 'from-green-500 to-emerald-500';
    if (yearsToFire <= 10) return 'from-blue-500 to-cyan-500';
    if (yearsToFire <= 20) return 'from-yellow-500 to-amber-500';
    return 'from-orange-500 to-red-500';
  };

  const getStatusEmoji = (yearsToFire) => {
    if (yearsToFire === Infinity || yearsToFire > 30) return '💪';
    if (yearsToFire <= 5) return '🎉';
    if (yearsToFire <= 10) return '🚀';
    if (yearsToFire <= 20) return '📈';
    return '⚠️';
  };

  if (loading) {
    return (
      <Card>
        <LoadingSpinner text="Calculating your FIRE journey..." />
      </Card>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 rounded-2xl p-6 shadow-md border border-red-200">
        <div className="text-red-800 font-semibold mb-2">⚠️ Unable to Calculate FIRE Metrics</div>
        <div className="text-red-600 text-sm">{error}</div>
      </div>
    );
  }

  if (!metrics) return null;

  const {
    current_monthly_expenses,
    current_monthly_income,
    current_monthly_savings,
    savings_rate,
    fire_corpus_required,
    current_net_worth,
    months_to_fire,
    years_to_fire,
    months_of_expenses_covered,
    deficit,
    progress_percentage,
    message
  } = metrics;

  // Handle null/infinite values safely
  const yearsToFire = (years_to_fire === null || years_to_fire === undefined || isNaN(years_to_fire)) ? 999 : (years_to_fire === Infinity ? 999 : years_to_fire);
  const statusColor = getStatusColor(yearsToFire);
  const statusEmoji = getStatusEmoji(yearsToFire);

  return (
    <div className="bg-gradient-to-br from-indigo-50 via-purple-50 to-pink-50 rounded-2xl p-6 shadow-lg border-2 border-indigo-200">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h3 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
            <span className="text-4xl">{statusEmoji}</span>
            <span>FIRE Calculator</span>
          </h3>
          <p className="text-sm text-gray-600 mt-1">Your path to Financial Independence</p>
        </div>
        <div className="text-right">
          <div className={`text-3xl font-black bg-gradient-to-r ${statusColor} bg-clip-text text-transparent`}>
            {yearsToFire === 999 ? '∞' : safeToFixed(yearsToFire, 1)}
          </div>
          <div className="text-xs text-gray-600">years to FIRE</div>
        </div>
      </div>

      {/* Progress Bar */}
      <div className="mb-6">
        <div className="flex items-center justify-between mb-2">
          <div className="text-sm font-medium text-gray-700">Progress to FIRE</div>
          <div className="text-sm font-semibold text-indigo-600">{safeToFixed(progress_percentage, 1)}%</div>
        </div>
        <div className="w-full h-4 bg-gray-200 rounded-full overflow-hidden">
          <div
            className={`h-full bg-gradient-to-r ${statusColor} transition-all duration-1000 ease-out`}
            style={{ width: `${Math.min(safeNumber(progress_percentage, 0), 100)}%` }}
          />
        </div>
        <div className="flex justify-between text-xs text-gray-500 mt-1">
          <span>₹0</span>
          <span>{formatCurrency(current_net_worth)}</span>
          <span>{formatCurrency(fire_corpus_required)}</span>
        </div>
      </div>

      {/* Key Metrics Grid */}
      <div className="grid grid-cols-2 gap-4 mb-6">
        <div className="bg-white rounded-xl p-4 shadow-sm border border-gray-100">
          <div className="text-xs text-gray-500 mb-1">Target Corpus</div>
          <div className="text-xl font-bold text-indigo-600">
            {formatCurrency(fire_corpus_required)}
          </div>
          <div className="text-xs text-gray-400 mt-1">25x annual expenses</div>
        </div>

        <div className="bg-white rounded-xl p-4 shadow-sm border border-gray-100">
          <div className="text-xs text-gray-500 mb-1">Current Net Worth</div>
          <div className="text-xl font-bold text-green-600">
            {formatCurrency(current_net_worth)}
          </div>
          <div className="text-xs text-gray-400 mt-1">Assets - Liabilities</div>
        </div>

        <div className="bg-white rounded-xl p-4 shadow-sm border border-gray-100">
          <div className="text-xs text-gray-500 mb-1">Monthly Savings</div>
          <div className="text-xl font-bold text-blue-600">
            {formatCurrency(current_monthly_savings)}
          </div>
          <div className="text-xs text-gray-400 mt-1">Savings Rate: {safeToFixed(savings_rate, 1)}%</div>
        </div>

        <div className="bg-white rounded-xl p-4 shadow-sm border border-gray-100">
          <div className="text-xs text-gray-500 mb-1">Remaining to Save</div>
          <div className="text-xl font-bold text-red-600">
            {formatCurrency(deficit)}
          </div>
          <div className="text-xs text-gray-400 mt-1">{(months_to_fire === null || months_to_fire === Infinity) ? '∞' : Math.ceil(months_to_fire)} months</div>
        </div>
      </div>

      {/* Detailed Breakdown */}
      <div className="bg-white/80 rounded-xl p-4 mb-4">
        <div className="grid grid-cols-2 gap-4 text-sm">
          <div>
            <div className="text-gray-600 mb-1">Monthly Income</div>
            <div className="font-semibold text-gray-900">{formatCurrency(current_monthly_income)}</div>
          </div>
          <div>
            <div className="text-gray-600 mb-1">Monthly Expenses</div>
            <div className="font-semibold text-gray-900">{formatCurrency(current_monthly_expenses)}</div>
          </div>
          <div>
            <div className="text-gray-600 mb-1">Financial Runway</div>
            <div className="font-semibold text-gray-900">{safeToFixed(months_of_expenses_covered, 1)} months</div>
          </div>
          <div>
            <div className="text-gray-600 mb-1">Status</div>
            <div className={`font-semibold ${savings_rate > 20 ? 'text-green-600' : 'text-orange-600'}`}>
              {message}
            </div>
          </div>
        </div>
      </div>

      {/* Action Message */}
      <div className={`bg-gradient-to-r ${statusColor} rounded-xl p-4 text-white`}>
        <div className="flex items-start gap-3">
          <span className="text-2xl">{statusEmoji}</span>
          <div>
            <div className="font-semibold mb-1">{message}</div>
            <div className="text-xs text-white/80">
              {yearsToFire <= 10
                ? `Keep saving ${formatCurrency(current_monthly_savings)}/month to achieve FIRE in ${safeToFixed(yearsToFire, 1)} years!`
                : yearsToFire <= 20
                ? `Increase your savings rate to reach FIRE faster. Aim for 30%+ savings rate.`
                : `Focus on increasing income or reducing expenses to accelerate your FIRE journey.`}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
