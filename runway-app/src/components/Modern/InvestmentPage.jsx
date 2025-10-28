// src/components/Modern/InvestmentPage.jsx
import React from 'react';
import InvestmentOptimizer from './InvestmentOptimizer';

export default function InvestmentPage({ onNavigate }) {
  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 pb-24">
      <div className="bg-white/80 backdrop-blur-md sticky top-0 z-20 border-b border-gray-100">
        <div className="max-w-lg mx-auto px-4 py-4">
          <button
            onClick={() => onNavigate('optimize')}
            className="flex items-center gap-2 text-gray-600 hover:text-gray-900 mb-2"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
            </svg>
            <span className="text-sm font-medium">Back to Optimize</span>
          </button>
          <h1 className="text-2xl font-bold text-gray-900">📈 Investment Optimizer</h1>
          <p className="text-sm text-gray-500 mt-1">Track and optimize your portfolio</p>
        </div>
      </div>

      <div className="max-w-lg mx-auto px-4 py-6">
        <InvestmentOptimizer />
      </div>
    </div>
  );
}

