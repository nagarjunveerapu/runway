// src/components/Reports/DashboardMetrics.jsx
import React, { useMemo } from 'react';

/**
 * DashboardMetrics - Shows key spending metrics
 * Similar to the Streamlit dashboard metrics
 */
export default function DashboardMetrics({ transactions = [] }) {
  const metrics = useMemo(() => {
    let totalSpend = 0;
    let upiSpend = 0;
    let withdrawalCount = 0;
    let upiCount = 0;

    transactions.forEach(t => {
      const amount = Number(t.amount || 0);
      const channel = (t.channel || '').toUpperCase();

      // Count withdrawals/expenses (not income)
      if (t.type !== 'income' && amount > 0) {
        totalSpend += amount;
        withdrawalCount++;

        if (channel === 'UPI') {
          upiSpend += amount;
          upiCount++;
        }
      }
    });

    const upiPercentage = totalSpend > 0 ? (upiSpend / totalSpend) * 100 : 0;

    return {
      totalSpend,
      upiSpend,
      upiPercentage,
      totalTransactions: transactions.length,
      withdrawalCount,
      upiCount
    };
  }, [transactions]);

  const formatCurrency = (amount) => {
    return `₹${amount.toLocaleString('en-IN', { maximumFractionDigits: 2 })}`;
  };

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
      {/* Total Spend */}
      <div className="bg-white p-6 rounded-lg shadow-md border-l-4 border-blue-500">
        <div className="text-sm text-gray-600 font-medium">Total Spend</div>
        <div className="text-3xl font-bold text-gray-900 mt-2">
          {formatCurrency(metrics.totalSpend)}
        </div>
        <div className="text-xs text-gray-500 mt-1">
          {metrics.withdrawalCount} expense transactions
        </div>
      </div>

      {/* UPI Spend */}
      <div className="bg-white p-6 rounded-lg shadow-md border-l-4 border-purple-500">
        <div className="text-sm text-gray-600 font-medium">UPI Spend</div>
        <div className="text-3xl font-bold text-gray-900 mt-2">
          {formatCurrency(metrics.upiSpend)}
        </div>
        <div className="text-xs text-gray-500 mt-1">
          {metrics.upiCount} UPI transactions
        </div>
      </div>

      {/* UPI Percentage */}
      <div className="bg-white p-6 rounded-lg shadow-md border-l-4 border-green-500">
        <div className="text-sm text-gray-600 font-medium">UPI % of Spend</div>
        <div className="text-3xl font-bold text-gray-900 mt-2">
          {metrics.upiPercentage.toFixed(1)}%
        </div>
        <div className="text-xs text-gray-500 mt-1">
          Digital payment adoption
        </div>
      </div>

      {/* Total Transactions */}
      <div className="bg-white p-6 rounded-lg shadow-md border-l-4 border-orange-500">
        <div className="text-sm text-gray-600 font-medium">Total Transactions</div>
        <div className="text-3xl font-bold text-gray-900 mt-2">
          {metrics.totalTransactions}
        </div>
        <div className="text-xs text-gray-500 mt-1">
          All recorded transactions
        </div>
      </div>
    </div>
  );
}
