// src/components/Modern/NetWorthTimeline.jsx
import React, { useState, useEffect } from 'react';
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend, ReferenceLine } from 'recharts';
import { getNetWorthTimelineDynamic, getNetWorthProjection } from '../../api/services/netWorth';

/**
 * NetWorthTimeline - Interactive net worth timeline chart with DYNAMIC calculation
 * Features:
 * - EMI-based liability reduction
 * - SIP/investment growth
 * - Asset appreciation
 * - Crossover point indicator
 * - Future projection
 */

export default function NetWorthTimeline() {
  const [timelineData, setTimelineData] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedPeriod, setSelectedPeriod] = useState('12'); // 3, 6, 12, or 'all'
  const [crossoverPoint, setCrossoverPoint] = useState(null);
  const [useDynamic, setUseDynamic] = useState(true); // Use dynamic calculation by default

  useEffect(() => {
    loadTimeline();
  }, [selectedPeriod]);

  const loadTimeline = async () => {
    try {
      setLoading(true);
      setError(null);
      const months = selectedPeriod === 'all' ? 999 : parseInt(selectedPeriod);

      // Use dynamic calculation (considers EMI payments, SIP growth, etc.)
      const data = await getNetWorthTimelineDynamic(months, false);

      // Transform data for Recharts
      const chartData = data.timeline.map(item => ({
        month: formatMonth(item.month),
        assets: item.assets,
        liabilities: item.liabilities,
        netWorth: item.net_worth,
        // For tooltip display
        assetsFormatted: formatCurrency(item.assets),
        liabilitiesFormatted: formatCurrency(item.liabilities),
        netWorthFormatted: formatCurrency(item.net_worth)
      }));

      setTimelineData(chartData);
      setCrossoverPoint(data.crossover_point);
    } catch (err) {
      console.error('Failed to load timeline:', err);
      setError(err.message || 'Failed to load timeline data');
    } finally {
      setLoading(false);
    }
  };

  const formatMonth = (monthStr) => {
    // Convert "2024-01" to "Jan '24"
    const [year, month] = monthStr.split('-');
    const monthNames = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
    return `${monthNames[parseInt(month) - 1]} '${year.slice(2)}`;
  };

  const formatCurrency = (amount) => {
    if (amount >= 10000000) return `₹${(amount / 10000000).toFixed(2)}Cr`;
    if (amount >= 100000) return `₹${(amount / 100000).toFixed(2)}L`;
    if (amount >= 1000) return `₹${(amount / 1000).toFixed(1)}K`;
    return `₹${Math.round(amount).toLocaleString('en-IN')}`;
  };

  const formatCurrencyAxis = (value) => {
    if (value >= 10000000) return `${(value / 10000000).toFixed(1)}Cr`;
    if (value >= 100000) return `${(value / 100000).toFixed(0)}L`;
    if (value >= 1000) return `${(value / 1000).toFixed(0)}K`;
    return value;
  };

  const CustomTooltip = ({ active, payload }) => {
    if (active && payload && payload.length) {
      return (
        <div className="bg-white p-4 rounded-xl shadow-lg border border-gray-200">
          <p className="text-sm font-semibold text-gray-900 mb-2">{payload[0].payload.month}</p>
          <div className="space-y-1">
            <div className="flex items-center justify-between gap-4">
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 rounded-full bg-green-500"></div>
                <span className="text-xs text-gray-600">Net Worth</span>
              </div>
              <span className="text-sm font-bold text-green-600">{payload[0].payload.netWorthFormatted}</span>
            </div>
            <div className="flex items-center justify-between gap-4">
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 rounded-full bg-blue-500"></div>
                <span className="text-xs text-gray-600">Assets</span>
              </div>
              <span className="text-sm font-semibold text-blue-600">{payload[0].payload.assetsFormatted}</span>
            </div>
            <div className="flex items-center justify-between gap-4">
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 rounded-full bg-red-500"></div>
                <span className="text-xs text-gray-600">Liabilities</span>
              </div>
              <span className="text-sm font-semibold text-red-600">{payload[0].payload.liabilitiesFormatted}</span>
            </div>
          </div>
        </div>
      );
    }
    return null;
  };

  const periods = [
    { value: '3', label: '3M' },
    { value: '6', label: '6M' },
    { value: '12', label: '1Y' },
    { value: 'all', label: 'All' }
  ];

  // Calculate growth metrics
  const calculateGrowth = () => {
    if (timelineData.length < 2) return null;

    const latest = timelineData[timelineData.length - 1];
    const oldest = timelineData[0];
    const growth = latest.netWorth - oldest.netWorth;
    const growthPercent = ((growth / oldest.netWorth) * 100).toFixed(1);

    return {
      amount: growth,
      percent: growthPercent,
      isPositive: growth >= 0
    };
  };

  const growth = calculateGrowth();

  if (loading) {
    return (
      <div className="bg-white rounded-2xl p-6 shadow-sm border border-gray-100">
        <div className="flex items-center justify-center h-64">
          <div className="text-center">
            <div className="w-12 h-12 border-4 border-green-500 border-t-transparent rounded-full animate-spin mx-auto mb-3"></div>
            <p className="text-sm text-gray-600">Loading timeline...</p>
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-white rounded-2xl p-6 shadow-sm border border-gray-100">
        <div className="text-center py-8">
          <div className="text-4xl mb-3">📊</div>
          <h3 className="text-lg font-semibold text-gray-900 mb-2">Timeline Not Available</h3>
          <p className="text-sm text-gray-600 mb-4">{error}</p>
          <button
            onClick={loadTimeline}
            className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  if (timelineData.length === 0) {
    return (
      <div className="bg-gradient-to-br from-green-50 to-emerald-50 rounded-2xl p-6 border-2 border-dashed border-green-200">
        <div className="text-center py-4">
          <div className="text-4xl mb-3">📈</div>
          <h3 className="text-lg font-semibold text-gray-900 mb-2">No Timeline Data Yet</h3>
          <p className="text-sm text-gray-600 mb-4">
            Your net worth timeline will appear here as you track your finances over time.
          </p>
          <p className="text-xs text-gray-500">
            Data is automatically captured monthly. Add assets and transactions to get started!
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-2xl p-5 shadow-sm border border-gray-100">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="text-lg font-bold text-gray-900">Net Worth Timeline</h3>
          <p className="text-xs text-gray-500 mt-0.5">Track your wealth journey</p>
        </div>

        {/* Period Selector */}
        <div className="flex gap-1 bg-gray-100 rounded-lg p-1">
          {periods.map(period => (
            <button
              key={period.value}
              onClick={() => setSelectedPeriod(period.value)}
              className={`px-3 py-1 text-xs font-medium rounded-md transition-all ${
                selectedPeriod === period.value
                  ? 'bg-white text-green-600 shadow-sm'
                  : 'text-gray-600 hover:text-gray-900'
              }`}
            >
              {period.label}
            </button>
          ))}
        </div>
      </div>

      {/* Growth Indicator & Crossover Point */}
      <div className="mb-4 flex items-center gap-2 flex-wrap">
        {growth && (
          <>
            <div className={`flex items-center gap-1 px-3 py-1 rounded-full text-sm font-semibold ${
              growth.isPositive
                ? 'bg-green-100 text-green-700'
                : 'bg-red-100 text-red-700'
            }`}>
              <span>{growth.isPositive ? '↑' : '↓'}</span>
              <span>{formatCurrency(Math.abs(growth.amount))}</span>
              <span className="text-xs">({growth.percent}%)</span>
            </div>
            <span className="text-xs text-gray-500">
              {selectedPeriod === 'all' ? 'All time' : `Last ${selectedPeriod} months`}
            </span>
          </>
        )}

        {/* Crossover Point - when net worth becomes positive */}
        {crossoverPoint && (
          <div className="flex items-center gap-1 px-3 py-1 rounded-full text-sm font-semibold bg-blue-100 text-blue-700 border border-blue-200">
            <span>🎯</span>
            <span className="text-xs">Positive by {formatMonth(crossoverPoint)}</span>
          </div>
        )}

        {/* Dynamic Calculation Badge */}
        <div className="flex items-center gap-1 px-2 py-1 rounded-md text-xs bg-purple-50 text-purple-600 border border-purple-200">
          <span>⚡</span>
          <span>Dynamic Calculation</span>
        </div>
      </div>

      {/* Chart */}
      <div className="w-full h-64 mt-4">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart
            data={timelineData}
            margin={{ top: 10, right: 10, left: 0, bottom: 0 }}
          >
            <defs>
              <linearGradient id="colorNetWorth" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#10b981" stopOpacity={0.3}/>
                <stop offset="95%" stopColor="#10b981" stopOpacity={0}/>
              </linearGradient>
              <linearGradient id="colorAssets" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.2}/>
                <stop offset="95%" stopColor="#3b82f6" stopOpacity={0}/>
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
            <XAxis
              dataKey="month"
              tick={{ fill: '#6b7280', fontSize: 11 }}
              tickLine={{ stroke: '#e5e7eb' }}
            />
            <YAxis
              tick={{ fill: '#6b7280', fontSize: 11 }}
              tickLine={{ stroke: '#e5e7eb' }}
              tickFormatter={formatCurrencyAxis}
            />
            <Tooltip content={<CustomTooltip />} />

            {/* Assets Area */}
            <Area
              type="monotone"
              dataKey="assets"
              stroke="#3b82f6"
              strokeWidth={2}
              fill="url(#colorAssets)"
              name="Assets"
            />

            {/* Net Worth Area (primary focus) */}
            <Area
              type="monotone"
              dataKey="netWorth"
              stroke="#10b981"
              strokeWidth={3}
              fill="url(#colorNetWorth)"
              name="Net Worth"
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>

      {/* Legend */}
      <div className="flex items-center justify-center gap-4 mt-4 pt-4 border-t border-gray-100">
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 rounded-full bg-green-500"></div>
          <span className="text-xs text-gray-600 font-medium">Net Worth</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 rounded-full bg-blue-500"></div>
          <span className="text-xs text-gray-600 font-medium">Assets</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 rounded-full bg-red-500"></div>
          <span className="text-xs text-gray-600 font-medium">Liabilities</span>
        </div>
      </div>
    </div>
  );
}
