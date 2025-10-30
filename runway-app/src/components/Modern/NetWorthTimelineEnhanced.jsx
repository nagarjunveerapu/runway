// src/components/Modern/NetWorthTimelineEnhanced.jsx
import React, { useState, useEffect } from 'react';
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend, ReferenceLine } from 'recharts';
import { getNetWorthTimeline, getNetWorthProjection } from '../../api/services/netWorth';

/**
 * Enhanced Net Worth Timeline with:
 * - Interactive ruler/slider for timeline navigation
 * - Year/Month zoom controls
 * - EMI payoff markers
 * - Cash flow projection after EMIs
 */

export default function NetWorthTimelineEnhanced() {
  const [timelineData, setTimelineData] = useState([]);
  const [fullData, setFullData] = useState([]); // Store full dataset
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedPeriod, setSelectedPeriod] = useState('1Y');
  const [granularity, setGranularity] = useState('month'); // 'month' or 'year'
  const [sliderValue, setSliderValue] = useState(100); // Percentage of timeline to show (from end)
  const [emiPayoffDates, setEmiPayoffDates] = useState([]);

  const periods = [
    { value: '3M', label: '3M', months: 3 },
    { value: '6M', label: '6M', months: 6 },
    { value: '1Y', label: '1Y', months: 12 },
    { value: 'ALL', label: 'All', months: 999 }
  ];

  useEffect(() => {
    loadTimeline();
  }, [selectedPeriod]);

  useEffect(() => {
    // Apply slider filter to data
    if (fullData.length > 0) {
      applySliderFilter();
    }
  }, [sliderValue, fullData, granularity]);

  const loadTimeline = async () => {
    try {
      setLoading(true);
      setError(null);

      const period = periods.find(p => p.value === selectedPeriod);
      const months = period ? period.months : 12;

      // Try dynamic timeline first (with projections), fall back to basic timeline
      let response;
      try {
        // Use projection endpoint which includes both historical and future projections
        const years = Math.ceil(months / 12);
        response = await getNetWorthProjection(years);
        
        // If projection exists, use it; otherwise try static timeline
        if (!response.timeline || response.timeline.length === 0) {
          response = await getNetWorthTimeline(months);
        }
      } catch (projError) {
        // Fall back to basic timeline if projection fails
        console.error('Projection failed, falling back to static timeline:', projError);
        console.error('Projection error details:', projError.response?.data || projError.message);
        response = await getNetWorthTimeline(months);
      }
      
      // Debug logging
      console.log('Timeline response:', response);
      console.log('Has historical data:', response.has_historical_data);
      console.log('Timeline length:', response.timeline?.length);
      console.log('Liability details:', JSON.stringify(response.liability_details, null, 2));
      console.log('First timeline entry:', JSON.stringify(response.timeline?.[0], null, 2));
      console.log('All timeline values (liabilities):', response.timeline?.map(t => ({ month: t.month, liabilities: t.liabilities, net_worth: t.net_worth })));

      if (!response.timeline || response.timeline.length === 0) {
        setError("No financial data available. Add assets and liabilities to start tracking.");
        setTimelineData([]);
        setFullData([]);
        return;
      }

      // Transform data for Recharts
      // Handle both basic timeline and projection endpoints
      const dataSource = response.timeline || [];
      const chartData = dataSource.map(item => ({
        month: item.month,
        monthFormatted: formatMonth(item.month),
        assets: item.assets || 0,
        liabilities: item.liabilities || 0,
        netWorth: item.net_worth || 0,
        assetsFormatted: formatCurrency(item.assets || 0),
        liabilitiesFormatted: formatCurrency(item.liabilities || 0),
        netWorthFormatted: formatCurrency(item.net_worth || 0),
        // Additional fields for projections
        is_historical: item.is_historical,
        is_projected: item.is_projected,
        payoff_event: item.payoff_event,
        cash_flow_improvement: item.cash_flow_improvement
      }));

      setFullData(chartData);
      setTimelineData(chartData);

      // Detect EMI payoff dates (when liabilities drop significantly)
      // Or use payoff events from projection endpoint
      if (response.loan_payoff_schedule && response.loan_payoff_schedule.length > 0) {
        const payoffMarkers = response.loan_payoff_schedule.map(payoff => ({
          month: payoff.payoff_month,
          amount: payoff.current_balance,
          name: payoff.name,
          type: 'projected'
        }));
        setEmiPayoffDates(payoffMarkers);
      } else {
        detectEMIPayoffs(chartData);
      }

    } catch (err) {
      console.error('Failed to load timeline:', err);
      setError('Failed to load timeline data. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const applySliderFilter = () => {
    if (fullData.length === 0) return;

    // Calculate how many data points to show based on slider
    const totalPoints = fullData.length;
    const pointsToShow = Math.max(3, Math.ceil((sliderValue / 100) * totalPoints));

    // Show the most recent N points
    const startIndex = Math.max(0, totalPoints - pointsToShow);
    let filtered = fullData.slice(startIndex);

    // Apply granularity (month vs year)
    if (granularity === 'year' && filtered.length > 12) {
      // Show only every 12th month (year end)
      filtered = filtered.filter((_, index) => index % 12 === 11 || index === filtered.length - 1);
    }

    setTimelineData(filtered);
  };

  const detectEMIPayoffs = (data) => {
    const payoffs = [];

    for (let i = 1; i < data.length; i++) {
      const prevLiability = data[i - 1].liabilities;
      const currLiability = data[i].liabilities;

      // Detect significant drop in liabilities (> 20% or > 1L)
      const drop = prevLiability - currLiability;
      const dropPercent = (drop / prevLiability) * 100;

      if (drop > 100000 || dropPercent > 20) {
        payoffs.push({
          month: data[i].month,
          amount: drop,
          type: drop > 500000 ? 'major' : 'regular'
        });
      }
    }

    setEmiPayoffDates(payoffs);
  };

  const formatMonth = (monthStr) => {
    const [year, month] = monthStr.split('-');
    const monthNames = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
    return `${monthNames[parseInt(month) - 1]} '${year.slice(2)}`;
  };

  const formatCurrency = (amount) => {
    if (amount >= 10000000) return `₹${(amount / 10000000).toFixed(2)}Cr`;
    if (amount >= 100000) return `₹${(amount / 100000).toFixed(1)}L`;
    if (amount >= 1000) return `₹${(amount / 1000).toFixed(0)}K`;
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
      const data = payload[0].payload;
      return (
        <div className="bg-white p-4 rounded-xl shadow-xl border-2 border-gray-200">
          <p className="text-sm font-bold text-gray-900 mb-3">{data.monthFormatted}</p>
          <div className="space-y-2">
            <div className="flex items-center justify-between gap-6">
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 rounded-full bg-green-500"></div>
                <span className="text-xs text-gray-600">Net Worth</span>
              </div>
              <span className="text-sm font-bold text-green-600">{data.netWorthFormatted}</span>
            </div>
            <div className="flex items-center justify-between gap-6">
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 rounded-full bg-blue-500"></div>
                <span className="text-xs text-gray-600">Assets</span>
              </div>
              <span className="text-sm font-semibold text-blue-600">{data.assetsFormatted}</span>
            </div>
            <div className="flex items-center justify-between gap-6">
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 rounded-full bg-red-500"></div>
                <span className="text-xs text-gray-600">Liabilities</span>
              </div>
              <span className="text-sm font-semibold text-red-600">{data.liabilitiesFormatted}</span>
            </div>
          </div>

          {/* Show EMI payoff marker if this month has one */}
          {emiPayoffDates.find(p => p.month === data.month) && (
            <div className="mt-3 pt-3 border-t border-gray-200">
              <div className="flex items-center gap-2 text-xs">
                <span className="text-orange-600">🎯</span>
                <span className="text-orange-700 font-medium">Loan Payoff</span>
              </div>
            </div>
          )}
        </div>
      );
    }
    return null;
  };

  // Calculate growth metrics
  const growth = timelineData.length >= 2 ? {
    amount: timelineData[timelineData.length - 1].netWorth - timelineData[0].netWorth,
    percent: (((timelineData[timelineData.length - 1].netWorth - timelineData[0].netWorth) / Math.abs(timelineData[0].netWorth || 1)) * 100).toFixed(1),
    isPositive: timelineData[timelineData.length - 1].netWorth >= timelineData[0].netWorth
  } : null;

  if (loading) {
    return (
      <div className="bg-white rounded-2xl p-8 shadow-sm border border-gray-100">
        <div className="flex items-center justify-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-green-600"></div>
          <span className="ml-3 text-gray-600">Loading timeline...</span>
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

  return (
    <div className="bg-white rounded-2xl p-5 shadow-sm border border-gray-100">
      {/* Header with Controls */}
      <div className="flex items-center justify-between mb-4 flex-wrap gap-3">
        <div>
          <h3 className="text-lg font-bold text-gray-900">Net Worth Timeline</h3>
          <p className="text-xs text-gray-500 mt-0.5">Track your wealth journey</p>
        </div>

        {/* Granularity Toggle */}
        <div className="flex gap-2 items-center">
          <span className="text-xs text-gray-600">View:</span>
          <div className="flex gap-1 bg-gray-100 rounded-lg p-1">
            <button
              onClick={() => setGranularity('month')}
              className={`px-3 py-1 text-xs font-medium rounded-md transition-all ${
                granularity === 'month'
                  ? 'bg-white text-green-600 shadow-sm'
                  : 'text-gray-600 hover:text-gray-900'
              }`}
            >
              Months
            </button>
            <button
              onClick={() => setGranularity('year')}
              className={`px-3 py-1 text-xs font-medium rounded-md transition-all ${
                granularity === 'year'
                  ? 'bg-white text-green-600 shadow-sm'
                  : 'text-gray-600 hover:text-gray-900'
              }`}
            >
              Years
            </button>
          </div>
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

      {/* Growth Indicator */}
      {growth && (
        <div className="mb-4 flex items-center gap-2 flex-wrap">
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
            Last {timelineData.length} {granularity === 'year' ? 'years' : 'months'}
          </span>

          {/* EMI Payoffs Count */}
          {emiPayoffDates.length > 0 && (
            <div className="flex items-center gap-1 px-3 py-1 rounded-full text-xs bg-orange-100 text-orange-700 border border-orange-200">
              <span>🎯</span>
              <span>{emiPayoffDates.length} Loan Payoffs</span>
            </div>
          )}
        </div>
      )}

      {/* Chart */}
      <div className="w-full h-80 mt-4">
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
              <linearGradient id="colorLiabilities" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#ef4444" stopOpacity={0.2}/>
                <stop offset="95%" stopColor="#ef4444" stopOpacity={0}/>
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
            <XAxis
              dataKey="monthFormatted"
              tick={{ fill: '#6b7280', fontSize: 11 }}
              tickLine={{ stroke: '#e5e7eb' }}
            />
            <YAxis
              tick={{ fill: '#6b7280', fontSize: 11 }}
              tickLine={{ stroke: '#e5e7eb' }}
              tickFormatter={formatCurrencyAxis}
              domain={['dataMin - 500000', 'dataMax + 500000']}
            />
            <Tooltip content={<CustomTooltip />} />
            <Legend
              wrapperStyle={{ fontSize: '12px', paddingTop: '10px' }}
              iconType="circle"
            />

            {/* Add reference lines for EMI payoffs */}
            {emiPayoffDates.map(payoff => (
              <ReferenceLine
                key={payoff.month}
                x={formatMonth(payoff.month)}
                stroke={payoff.type === 'major' ? '#f59e0b' : '#fbbf24'}
                strokeDasharray="3 3"
                label={{
                  value: '🎯',
                  position: 'top',
                  fontSize: 16
                }}
              />
            ))}

            {/* Liabilities Area (behind) */}
            <Area
              type="monotone"
              dataKey="liabilities"
              stroke="#ef4444"
              strokeWidth={2}
              fill="url(#colorLiabilities)"
              name="Liabilities"
            />

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

      {/* Interactive Ruler/Slider */}
      <div className="mt-6 px-2">
        <div className="flex items-center gap-3">
          <span className="text-xs text-gray-600 whitespace-nowrap">Timeline Ruler:</span>
          <input
            type="range"
            min="20"
            max="100"
            value={sliderValue}
            onChange={(e) => setSliderValue(parseInt(e.target.value))}
            className="flex-1 h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer slider"
            style={{
              background: `linear-gradient(to right, #10b981 0%, #10b981 ${sliderValue}%, #e5e7eb ${sliderValue}%, #e5e7eb 100%)`
            }}
          />
          <span className="text-xs text-gray-600 font-medium whitespace-nowrap">
            {Math.ceil((sliderValue / 100) * fullData.length)} {granularity === 'year' ? 'yrs' : 'mos'}
          </span>
        </div>
        <p className="text-xs text-gray-500 mt-2 text-center">
          Drag the ruler to adjust timeline view • {emiPayoffDates.length > 0 && '🎯 markers show loan payoffs'}
        </p>
      </div>
    </div>
  );
}
