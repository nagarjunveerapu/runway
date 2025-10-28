// src/components/Reports/TopMerchants.jsx
import React, { useMemo } from 'react';

/**
 * TopMerchants - Shows top merchants by spending
 * Similar to the Streamlit dashboard top merchants section
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
    return rawMerchant.substring(0, 40) + (rawMerchant.length > 40 ? '...' : '');
  }

  // Limit length
  if (cleaned.length > 40) {
    cleaned = cleaned.substring(0, 40) + '...';
  }

  return cleaned || 'Unknown';
}

export default function TopMerchants({ transactions = [], limit = 10 }) {
  const merchantData = useMemo(() => {
    const merchantMap = {};

    transactions.forEach(t => {
      // Only count expenses (not income)
      if (t.type === 'income') return;

      const rawMerchant = t.merchant || t.description_raw || 'Unknown';
      const merchant = cleanMerchantName(rawMerchant);
      const amount = Number(t.amount || 0);

      if (!merchantMap[merchant]) {
        merchantMap[merchant] = { total: 0, count: 0 };
      }
      merchantMap[merchant].total += amount;
      merchantMap[merchant].count += 1;
    });

    // Convert to array and sort by total descending
    const merchantArray = Object.entries(merchantMap)
      .map(([merchant, data]) => ({
        merchant,
        total: data.total,
        count: data.count
      }))
      .sort((a, b) => b.total - a.total)
      .slice(0, limit);

    const maxAmount = merchantArray.length > 0 ? merchantArray[0].total : 1;

    return { merchantArray, maxAmount };
  }, [transactions, limit]);

  const formatCurrency = (amount) => {
    return `₹${amount.toLocaleString('en-IN', { maximumFractionDigits: 0 })}`;
  };

  const getBarColor = (index) => {
    const colors = [
      'bg-indigo-600',
      'bg-blue-600',
      'bg-purple-600',
      'bg-pink-600',
      'bg-red-600',
      'bg-orange-600',
      'bg-yellow-600',
      'bg-green-600',
      'bg-teal-600',
      'bg-cyan-600'
    ];
    return colors[index % colors.length];
  };

  if (merchantData.merchantArray.length === 0) {
    return (
      <div className="bg-white p-6 rounded-lg shadow-md">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">
          Top Merchants
        </h3>
        <div className="text-sm text-gray-500">
          No merchant data available
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white p-6 rounded-lg shadow-md">
      <h3 className="text-lg font-semibold text-gray-900 mb-4">
        Top {limit} Merchants by Spend
      </h3>

      <div className="space-y-4">
        {merchantData.merchantArray.map((item, index) => {
          const percentage = (item.total / merchantData.maxAmount) * 100;

          return (
            <div key={`${item.merchant}-${index}`} className="space-y-2">
              <div className="flex justify-between items-start gap-3">
                <div className="flex items-center gap-2 min-w-0 flex-1">
                  <span className="flex-shrink-0 w-6 h-6 rounded-full bg-gray-100 text-gray-600 text-xs font-medium flex items-center justify-center">
                    {index + 1}
                  </span>
                  <span
                    className="text-sm font-medium text-gray-700 truncate"
                    title={item.merchant}
                  >
                    {item.merchant}
                  </span>
                </div>
                <div className="text-right flex-shrink-0">
                  <div className="text-sm font-semibold text-gray-900 whitespace-nowrap">
                    {formatCurrency(item.total)}
                  </div>
                  <div className="text-xs text-gray-500 whitespace-nowrap">
                    {item.count} txn{item.count !== 1 ? 's' : ''}
                  </div>
                </div>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-2">
                <div
                  className={`${getBarColor(index)} h-2 rounded-full transition-all duration-500`}
                  style={{ width: `${percentage}%` }}
                />
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
