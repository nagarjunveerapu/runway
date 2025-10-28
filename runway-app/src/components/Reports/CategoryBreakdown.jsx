// src/components/Reports/CategoryBreakdown.jsx
import React, { useMemo } from 'react';

/**
 * CategoryBreakdown - Shows spending by category with horizontal bar chart
 * Similar to the Streamlit dashboard category breakdown
 */
export default function CategoryBreakdown({ transactions = [] }) {
  const categoryData = useMemo(() => {
    const categoryMap = {};

    transactions.forEach(t => {
      // Only count expenses (not income)
      if (t.type === 'income') return;

      const category = t.category || 'Uncategorized';
      const amount = Number(t.amount || 0);

      if (!categoryMap[category]) {
        categoryMap[category] = 0;
      }
      categoryMap[category] += amount;
    });

    // Convert to array and sort by amount descending
    const categoryArray = Object.entries(categoryMap)
      .map(([category, amount]) => ({ category, amount }))
      .sort((a, b) => b.amount - a.amount);

    const maxAmount = categoryArray.length > 0 ? categoryArray[0].amount : 1;

    return { categoryArray, maxAmount };
  }, [transactions]);

  const formatCurrency = (amount) => {
    return `₹${amount.toLocaleString('en-IN', { maximumFractionDigits: 0 })}`;
  };

  const getBarColor = (index) => {
    const colors = [
      'bg-blue-500',
      'bg-purple-500',
      'bg-green-500',
      'bg-yellow-500',
      'bg-red-500',
      'bg-indigo-500',
      'bg-pink-500',
      'bg-teal-500',
      'bg-orange-500',
      'bg-cyan-500'
    ];
    return colors[index % colors.length];
  };

  if (categoryData.categoryArray.length === 0) {
    return (
      <div className="bg-white p-6 rounded-lg shadow-md">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">
          Spend by Category
        </h3>
        <div className="text-sm text-gray-500">
          No expense data available
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white p-6 rounded-lg shadow-md">
      <h3 className="text-lg font-semibold text-gray-900 mb-4">
        Spend by Category
      </h3>

      <div className="space-y-3">
        {categoryData.categoryArray.map((item, index) => {
          const percentage = (item.amount / categoryData.maxAmount) * 100;

          return (
            <div key={item.category}>
              <div className="flex justify-between items-center mb-1">
                <span className="text-sm font-medium text-gray-700">
                  {item.category}
                </span>
                <span className="text-sm font-semibold text-gray-900">
                  {formatCurrency(item.amount)}
                </span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-3">
                <div
                  className={`${getBarColor(index)} h-3 rounded-full transition-all duration-500`}
                  style={{ width: `${percentage}%` }}
                />
              </div>
            </div>
          );
        })}
      </div>

      <div className="mt-4 pt-4 border-t border-gray-200">
        <div className="flex justify-between items-center">
          <span className="text-sm font-semibold text-gray-700">Total</span>
          <span className="text-lg font-bold text-gray-900">
            {formatCurrency(
              categoryData.categoryArray.reduce((sum, item) => sum + item.amount, 0)
            )}
          </span>
        </div>
      </div>
    </div>
  );
}
