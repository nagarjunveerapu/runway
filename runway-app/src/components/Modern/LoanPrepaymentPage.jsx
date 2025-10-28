// src/components/Modern/LoanPrepaymentPage.jsx
import React from 'react';
import LoanPrepaymentOptimizer from '../Reports/LoanPrepaymentOptimizerNew';

/**
 * LoanPrepaymentPage - Dedicated page for Loan Prepayment Optimizer
 */
export default function LoanPrepaymentPage({ onNavigate }) {
  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 pb-24">
      {/* Header */}
      <div className="bg-white/80 backdrop-blur-md sticky top-0 z-20 border-b border-gray-100">
        <div className="max-w-lg mx-auto px-4 py-4">
          <button
            onClick={() => onNavigate('reports')}
            className="flex items-center gap-2 text-gray-600 hover:text-gray-900 mb-2"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
            </svg>
            <span className="text-sm font-medium">Back to Reports</span>
          </button>
          <h1 className="text-2xl font-bold text-gray-900">🎯 Loan Prepayment Optimizer</h1>
          <p className="text-sm text-gray-500 mt-1">Save lakhs in interest</p>
        </div>
      </div>

      {/* Content */}
      <div className="max-w-lg mx-auto px-4 py-6">
        <LoanPrepaymentOptimizer />
      </div>
    </div>
  );
}
