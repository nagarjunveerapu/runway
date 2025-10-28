// src/components/Reports/RecurringPayments.jsx
import React, { useMemo } from 'react';

/**
 * RecurringPayments - Shows recurring payment patterns
 * Detects merchants with multiple transactions and displays them
 */

// Helper function to clean merchant names from raw descriptions
function cleanMerchantName(rawMerchant) {
  if (!rawMerchant || rawMerchant === 'Unknown') return 'Unknown';

  let cleaned = rawMerchant;

  // Remove common prefixes (UPI, NEFT, IMPS, etc.)
  cleaned = cleaned.replace(/^(UPI|NEFT|IMPS|RTGS|CMS|ATM|POS|ACH|NACH|MANDATE|TPT)\/?/i, '');

  // Remove transaction IDs and reference numbers (long alphanumeric strings)
  cleaned = cleaned.replace(/[A-Z0-9]{15,}/g, '');

  // Remove common separators and their content
  cleaned = cleaned.replace(/--[^-]+$/g, ''); // Remove trailing --REFERENCE
  cleaned = cleaned.replace(/\/\w+\/\d+/g, ''); // Remove /REF/12345

  // Extract merchant name from NEFT/UPI patterns
  // Pattern: NEFT-CITIN...-MERCHANT NAME--REF
  const neftMatch = cleaned.match(/NEFT-[^-]+-([^-]+)/i);
  if (neftMatch && neftMatch[1]) {
    cleaned = neftMatch[1];
  }

  // Pattern: UPI/MERCHANTNAME/...
  const upiMatch = cleaned.match(/UPI\/([^\/]+)/i);
  if (upiMatch && upiMatch[1]) {
    cleaned = upiMatch[1];
  }

  // Remove leading/trailing slashes, hyphens, and whitespace
  cleaned = cleaned.replace(/^[\s\-\/]+|[\s\-\/]+$/g, '');

  // Remove extra whitespace
  cleaned = cleaned.replace(/\s+/g, ' ').trim();

  // If cleaned name is too short or empty, return original (truncated)
  if (cleaned.length < 3) {
    return rawMerchant.substring(0, 50) + (rawMerchant.length > 50 ? '...' : '');
  }

  // Limit length
  if (cleaned.length > 50) {
    cleaned = cleaned.substring(0, 50) + '...';
  }

  return cleaned || 'Unknown';
}

export default function RecurringPayments({ transactions = [] }) {
  const recurringData = useMemo(() => {
    const merchantMap = {};

    transactions.forEach(t => {
      // Only count expenses (not income)
      if (t.type === 'income') return;

      const rawMerchant = t.merchant || t.description_raw || 'Unknown';
      const merchant = cleanMerchantName(rawMerchant);
      const amount = Number(t.amount || 0);

      if (!merchantMap[merchant]) {
        merchantMap[merchant] = {
          count: 0,
          totalAmount: 0,
          avgAmount: 0,
          dates: []
        };
      }

      merchantMap[merchant].count += 1;
      merchantMap[merchant].totalAmount += amount;
      if (t.date) {
        merchantMap[merchant].dates.push(t.date);
      }
    });

    // Filter merchants with 3+ transactions (likely recurring)
    // and calculate average amount
    const recurringArray = Object.entries(merchantMap)
      .map(([merchant, data]) => ({
        merchant,
        count: data.count,
        totalAmount: data.totalAmount,
        avgAmount: data.totalAmount / data.count,
        dates: data.dates.sort()
      }))
      .filter(item => item.count >= 3)
      .sort((a, b) => b.count - a.count);

    return recurringArray;
  }, [transactions]);

  const formatCurrency = (amount) => {
    return `₹${amount.toLocaleString('en-IN', { maximumFractionDigits: 0 })}`;
  };

  const getRecurringBadge = (count) => {
    if (count >= 12) {
      return { text: 'Monthly', color: 'bg-green-100 text-green-800' };
    } else if (count >= 6) {
      return { text: 'Frequent', color: 'bg-blue-100 text-blue-800' };
    } else {
      return { text: 'Recurring', color: 'bg-purple-100 text-purple-800' };
    }
  };

  if (recurringData.length === 0) {
    return (
      <div className="bg-white p-6 rounded-lg shadow-md">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">
          Recurring Payments
        </h3>
        <div className="text-sm text-gray-500">
          No recurring payment patterns detected (need 3+ transactions to same merchant)
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white p-6 rounded-lg shadow-md">
      <h3 className="text-lg font-semibold text-gray-900 mb-4">
        Recurring Payments
      </h3>
      <p className="text-sm text-gray-600 mb-4">
        Merchants with 3 or more transactions (likely subscriptions or recurring bills)
      </p>

      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-gray-200">
              <th className="text-left py-3 px-2 font-semibold text-gray-700 min-w-[200px]">
                Merchant
              </th>
              <th className="text-center py-3 px-2 font-semibold text-gray-700 whitespace-nowrap">
                Frequency
              </th>
              <th className="text-right py-3 px-2 font-semibold text-gray-700 whitespace-nowrap">
                Avg Amount
              </th>
              <th className="text-right py-3 px-2 font-semibold text-gray-700 whitespace-nowrap">
                Total Spent
              </th>
              <th className="text-center py-3 px-2 font-semibold text-gray-700 whitespace-nowrap">
                Pattern
              </th>
            </tr>
          </thead>
          <tbody>
            {recurringData.map((item, index) => {
              const badge = getRecurringBadge(item.count);
              return (
                <tr key={index} className="border-b border-gray-100 hover:bg-gray-50">
                  <td className="py-3 px-2 font-medium text-gray-900 max-w-[300px]" title={item.merchant}>
                    <div className="truncate">{item.merchant}</div>
                  </td>
                  <td className="py-3 px-2 text-center">
                    <span className="font-semibold text-gray-700">
                      {item.count}
                    </span>
                    <span className="text-gray-500 text-xs ml-1">times</span>
                  </td>
                  <td className="py-3 px-2 text-right text-gray-900">
                    {formatCurrency(item.avgAmount)}
                  </td>
                  <td className="py-3 px-2 text-right font-semibold text-gray-900">
                    {formatCurrency(item.totalAmount)}
                  </td>
                  <td className="py-3 px-2 text-center">
                    <span className={`inline-block px-2 py-1 rounded-full text-xs font-medium ${badge.color}`}>
                      {badge.text}
                    </span>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      <div className="mt-4 pt-4 border-t border-gray-200">
        <div className="flex justify-between items-center text-sm">
          <span className="text-gray-600">
            Total recurring merchants: <span className="font-semibold">{recurringData.length}</span>
          </span>
          <span className="text-gray-600">
            Total recurring spend:
            <span className="font-semibold ml-1">
              {formatCurrency(
                recurringData.reduce((sum, item) => sum + item.totalAmount, 0)
              )}
            </span>
          </span>
        </div>
      </div>
    </div>
  );
}
