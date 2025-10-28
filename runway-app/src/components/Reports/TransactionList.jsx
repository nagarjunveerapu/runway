import React from 'react';

/**
 * Enhanced Transaction List with enriched data display
 * Shows detailed transaction information without edit/delete options
 */

const formatCurrency = (amount) => {
  return `₹${Number(amount || 0).toLocaleString('en-IN', { maximumFractionDigits: 2 })}`;
};

const formatDate = (dateStr) => {
  if (!dateStr) return '-';
  try {
    // Handle DD/MM/YYYY format
    if (dateStr.includes('/')) {
      const [day, month, year] = dateStr.split('/');
      return new Date(year, month - 1, day).toLocaleDateString('en-IN', {
        day: 'numeric',
        month: 'short',
        year: 'numeric'
      });
    }
    // Handle YYYY-MM-DD format
    return new Date(dateStr).toLocaleDateString('en-IN', {
      day: 'numeric',
      month: 'short',
      year: 'numeric'
    });
  } catch (e) {
    return dateStr;
  }
};

const getTypeBadgeColor = (type) => {
  switch (type?.toLowerCase()) {
    case 'credit':
      return 'bg-green-100 text-green-800 border-green-200';
    case 'debit':
      return 'bg-red-100 text-red-800 border-red-200';
    case 'income':
      return 'bg-blue-100 text-blue-800 border-blue-200';
    default:
      return 'bg-gray-100 text-gray-800 border-gray-200';
  }
};

const getCategoryColor = (category) => {
  const categoryColors = {
    'salary': 'bg-purple-100 text-purple-800',
    'emi payment': 'bg-orange-100 text-orange-800',
    'investment': 'bg-blue-100 text-blue-800',
    'food & dining': 'bg-pink-100 text-pink-800',
    'groceries': 'bg-yellow-100 text-yellow-800',
    'fuel': 'bg-indigo-100 text-indigo-800',
    'rent': 'bg-red-100 text-red-800',
    'utilities': 'bg-cyan-100 text-cyan-800',
    'shopping': 'bg-violet-100 text-violet-800',
    'medical': 'bg-red-100 text-red-800',
    'transport': 'bg-green-100 text-green-800',
    'banking & fees': 'bg-gray-100 text-gray-800',
    'other': 'bg-gray-100 text-gray-600'
  };
  
  return categoryColors[category?.toLowerCase()] || 'bg-gray-100 text-gray-600';
};

export default function TransactionList({ transactions = [] }) {
  if (!Array.isArray(transactions) || transactions.length === 0) {
    return (
      <div className="mt-6 p-8 bg-white rounded-lg shadow-sm border border-gray-100 text-center">
        <div className="text-gray-400 mb-2">
          <svg className="w-12 h-12 mx-auto" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
          </svg>
        </div>
        <p className="text-gray-600 font-medium">No transactions to display</p>
        <p className="text-sm text-gray-500 mt-1">Upload your bank statement CSV to see transactions here</p>
      </div>
    );
  }

  // Sort by date (newest first)
  const sortedTransactions = [...transactions].sort((a, b) => {
    const dateA = a.date || '';
    const dateB = b.date || '';
    return dateB.localeCompare(dateA);
  });

  return (
    <div className="bg-white rounded-lg shadow-sm border border-gray-100 overflow-hidden">
      {/* Header */}
      <div className="bg-gray-50 px-6 py-3 border-b border-gray-200">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-semibold text-gray-900">Transactions ({transactions.length})</h3>
        </div>
      </div>

      {/* Transaction List */}
      <div className="divide-y divide-gray-100 max-h-[70vh] overflow-y-auto">
        {sortedTransactions.map((t, idx) => {
          const category = t.category || t.merchant_canonical || 'Other';
          const amount = Number(t.amount || 0);
          const isCredit = (t.type || '').toLowerCase() === 'credit';
          const description = t.description_raw || t.description || 'Transaction';
          
          // Truncate long descriptions
          const shortDesc = description.length > 50 ? description.substring(0, 50) + '...' : description;
          
          return (
            <div
              key={t.transaction_id || t.id || idx}
              className="px-6 py-3 hover:bg-gray-50 transition-colors"
            >
              <div className="flex items-center justify-between gap-4">
                {/* Left Section */}
                <div className="flex items-center gap-3 flex-1 min-w-0">
                  {/* Type Icon */}
                  <div className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center ${isCredit ? 'bg-green-100' : 'bg-red-100'}`}>
                    <span className="text-lg">{isCredit ? '↗' : '↘'}</span>
                  </div>

                  {/* Description & Category */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <p className="text-sm font-medium text-gray-900 truncate">{shortDesc}</p>
                      <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${getCategoryColor(category)}`}>
                        {category}
                      </span>
                    </div>
                  </div>
                </div>

                {/* Amount */}
                <div className="flex-shrink-0">
                  <div className={`text-base font-semibold ${isCredit ? 'text-green-600' : 'text-red-600'}`}>
                    {isCredit ? '+' : '-'}{formatCurrency(Math.abs(amount))}
                  </div>
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Footer Summary */}
      <div className="bg-gray-50 px-6 py-3 border-t border-gray-100">
        <div className="flex items-center justify-between text-xs text-gray-600">
          <div className="flex items-center gap-4">
            <span>Debits: <strong className="text-red-600">
              {formatCurrency(
                sortedTransactions
                  .filter(t => t.type?.toLowerCase() === 'debit')
                  .reduce((sum, t) => sum + Number(t.amount || 0), 0)
              )}
            </strong></span>
            <span className="text-gray-400">|</span>
            <span>Credits: <strong className="text-green-600">
              {formatCurrency(
                sortedTransactions
                  .filter(t => t.type?.toLowerCase() === 'credit')
                  .reduce((sum, t) => sum + Number(t.amount || 0), 0)
              )}
            </strong></span>
          </div>
        </div>
      </div>
    </div>
  );
}
