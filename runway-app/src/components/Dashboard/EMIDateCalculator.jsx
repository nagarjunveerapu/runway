// src/components/Dashboard/EMIDateCalculator.jsx
import React, { useState } from 'react';

/**
 * EMIDateCalculator - Simple, attractive calculator for homepage
 * Shows potential interest gains from optimizing EMI dates
 * Inspired by mutual fund return calculators
 */

const SALARY_ACCOUNT_RATE = 2.5; // Annual %
const SAVINGS_ACCOUNT_RATE = 7.0; // Annual %

export default function EMIDateCalculator({ onViewDetails }) {
  const [monthlySalary, setMonthlySalary] = useState(500000);
  const [monthlyEMI, setMonthlyEMI] = useState(100000);
  const [currentEMIDate, setCurrentEMIDate] = useState(5);
  const [newEMIDate, setNewEMIDate] = useState(20);

  // Calculate results
  const calculateResults = () => {
    // Calculate sweepable amount
    // Keep EMI amount + small buffer (10%) in salary account
    // Sweep the rest to savings account
    const bufferAmount = monthlyEMI * 0.1; // 10% buffer for safety
    const keepInSalaryAccount = monthlyEMI + bufferAmount;
    const sweepableAmount = monthlySalary - keepInSalaryAccount;

    // The money that generates interest difference
    // In salary account: EMI + buffer earns 2.5%
    // In savings account: sweepable amount earns 7% for X days, then 2.5% for remaining days

    // Simplified: Calculate interest on sweepable amount at 7% for the days before EMI
    // Current scenario - EMI early in month
    const currentDaysInSavings = currentEMIDate;
    const currentMonthlyInterest = (sweepableAmount * currentDaysInSavings / 30 * SAVINGS_ACCOUNT_RATE / 100 / 12);
    const currentAnnualInterest = currentMonthlyInterest * 12;

    // New scenario - EMI later in month
    const newDaysInSavings = newEMIDate;
    const newMonthlyInterest = (sweepableAmount * newDaysInSavings / 30 * SAVINGS_ACCOUNT_RATE / 100 / 12);
    const newAnnualInterest = newMonthlyInterest * 12;

    const additionalGain = newAnnualInterest - currentAnnualInterest;
    const percentageIncrease = currentAnnualInterest > 0 ? (additionalGain / currentAnnualInterest) * 100 : 0;

    return {
      sweepableAmount,
      keepInSalaryAccount,
      bufferAmount,
      currentDaysInSavings,
      newDaysInSavings,
      currentAnnualInterest,
      newAnnualInterest,
      additionalGain,
      percentageIncrease
    };
  };

  const results = calculateResults();

  const formatCurrency = (amount) => {
    return `₹${Math.round(amount).toLocaleString('en-IN')}`;
  };

  return (
    <div className="bg-white rounded-xl shadow-lg border border-gray-200 overflow-hidden">
      {/* Header */}
      <div className="bg-gradient-to-r from-purple-600 to-indigo-600 p-6 text-white">
        <div className="flex items-center gap-3 mb-2">
          <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 7h6m0 10v-3m-3 3h.01M9 17h.01M9 14h.01M12 14h.01M15 11h.01M12 11h.01M9 11h.01M7 21h10a2 2 0 002-2V5a2 2 0 00-2-2H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
          </svg>
          <h3 className="text-2xl font-bold">EMI Date Optimizer</h3>
        </div>
        <p className="text-sm opacity-90">Calculate potential interest gains by changing your EMI due date</p>
      </div>

      {/* Calculator Body */}
      <div className="p-6">
        {/* Input Section */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
          {/* Monthly Salary */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Monthly Salary
            </label>
            <div className="relative">
              <span className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500">₹</span>
              <input
                type="number"
                value={monthlySalary}
                onChange={(e) => setMonthlySalary(Number(e.target.value))}
                className="w-full pl-8 pr-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent"
                step="10000"
              />
            </div>
            <input
              type="range"
              min="100000"
              max="2000000"
              step="50000"
              value={monthlySalary}
              onChange={(e) => setMonthlySalary(Number(e.target.value))}
              className="w-full mt-2"
            />
          </div>

          {/* Monthly EMI */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Total Monthly EMI
            </label>
            <div className="relative">
              <span className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500">₹</span>
              <input
                type="number"
                value={monthlyEMI}
                onChange={(e) => setMonthlyEMI(Number(e.target.value))}
                className="w-full pl-8 pr-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent"
                step="5000"
              />
            </div>
            <input
              type="range"
              min="0"
              max="500000"
              step="10000"
              value={monthlyEMI}
              onChange={(e) => setMonthlyEMI(Number(e.target.value))}
              className="w-full mt-2"
            />
          </div>

          {/* Current EMI Date */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Current EMI Date
            </label>
            <select
              value={currentEMIDate}
              onChange={(e) => setCurrentEMIDate(Number(e.target.value))}
              className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent"
            >
              {[5, 10, 15, 20, 25].map(day => (
                <option key={day} value={day}>{day}th of month</option>
              ))}
            </select>
          </div>

          {/* New EMI Date */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Negotiate EMI Date To
            </label>
            <select
              value={newEMIDate}
              onChange={(e) => setNewEMIDate(Number(e.target.value))}
              className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent"
            >
              {[10, 15, 20, 25].map(day => (
                <option key={day} value={day}>{day}th of month</option>
              ))}
            </select>
          </div>
        </div>

        {/* Results Section */}
        <div className="bg-gradient-to-br from-green-50 to-emerald-50 rounded-xl p-6 border-2 border-green-200">
          <h4 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
            <svg className="w-5 h-5 text-green-600" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
            </svg>
            Potential Interest Gains
          </h4>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {/* Current Interest */}
            <div className="bg-white rounded-lg p-4 shadow-sm">
              <div className="text-xs text-gray-600 mb-1">Current Annual Interest</div>
              <div className="text-xl font-bold text-orange-600">
                {formatCurrency(results.currentAnnualInterest)}
              </div>
              <div className="text-xs text-gray-500 mt-1">
                @ {currentEMIDate}th EMI date
              </div>
            </div>

            {/* New Interest */}
            <div className="bg-white rounded-lg p-4 shadow-sm">
              <div className="text-xs text-gray-600 mb-1">New Annual Interest</div>
              <div className="text-xl font-bold text-green-600">
                {formatCurrency(results.newAnnualInterest)}
              </div>
              <div className="text-xs text-gray-500 mt-1">
                @ {newEMIDate}th EMI date
              </div>
            </div>

            {/* Additional Gain */}
            <div className="bg-gradient-to-br from-green-100 to-emerald-100 rounded-lg p-4 shadow-sm border-2 border-green-400">
              <div className="text-xs text-gray-700 font-medium mb-1">Extra Earnings</div>
              <div className="text-2xl font-bold text-green-700">
                {formatCurrency(results.additionalGain)}
              </div>
              <div className="text-xs text-green-600 font-semibold mt-1">
                +{results.percentageIncrease.toFixed(1)}% increase! 🎯
              </div>
            </div>
          </div>

          {/* Monthly Breakdown */}
          <div className="mt-4 pt-4 border-t border-green-200">
            <div className="flex justify-between items-center text-sm">
              <span className="text-gray-700">Monthly extra earnings:</span>
              <span className="font-bold text-green-700">
                {formatCurrency(results.additionalGain / 12)}/month
              </span>
            </div>
            <div className="flex justify-between items-center text-sm mt-2">
              <span className="text-gray-700">Amount to sweep to 7% savings:</span>
              <span className="font-semibold text-gray-900">
                {formatCurrency(results.sweepableAmount)}
              </span>
            </div>
            <div className="flex justify-between items-center text-sm mt-1">
              <span className="text-gray-700">Keep in salary account (2.5%):</span>
              <span className="font-semibold text-gray-600">
                {formatCurrency(results.keepInSalaryAccount)}
              </span>
            </div>
          </div>
        </div>

        {/* How It Works - Brief */}
        <div className="mt-6 bg-blue-50 rounded-lg p-4 border border-blue-200">
          <h5 className="font-semibold text-blue-900 mb-2 text-sm">💡 How It Works</h5>
          <p className="text-xs text-blue-800 leading-relaxed">
            Keep only <strong>{formatCurrency(results.keepInSalaryAccount)}</strong> (EMI + 10% buffer) in your 2.5% salary account.
            Sweep <strong>{formatCurrency(results.sweepableAmount)}</strong> to a 7% savings account.
            Moving your EMI date from <strong>{currentEMIDate}th to {newEMIDate}th</strong> means your swept money earns
            7% for <strong>{newEMIDate - currentEMIDate} extra days</strong> every month - that's an extra <strong>4.5%</strong> interest rate!
          </p>
        </div>

        {/* CTA Button */}
        {onViewDetails && (
          <button
            onClick={onViewDetails}
            className="mt-6 w-full bg-gradient-to-r from-purple-600 to-indigo-600 text-white font-semibold py-4 px-6 rounded-lg hover:from-purple-700 hover:to-indigo-700 transition-all shadow-lg hover:shadow-xl transform hover:-translate-y-0.5"
          >
            <div className="flex items-center justify-center gap-2">
              <span>View Detailed Analysis & Implementation Guide</span>
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
              </svg>
            </div>
          </button>
        )}

        {/* Small disclaimer */}
        <p className="mt-4 text-xs text-gray-500 text-center">
          *Keep EMI + 10% buffer in salary account. Sweep rest to 7% savings (AU/Unity Small Finance Banks). Interest calculated on days in savings.
        </p>
      </div>
    </div>
  );
}
