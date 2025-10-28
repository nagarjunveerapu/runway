// src/components/Modern/SalarySweepOptimizerV2.jsx
import React, { useState, useEffect } from 'react';
import {
  getSavedConfig,
  detectOrRefreshPatterns,
  confirmConfig,
  calculateOptimization,
  updateEMI,
  deleteEMI,
  resetConfig
} from '../../api/services/salarySweepV2';

/**
 * Salary Sweep Optimizer V2 - Two Stage Flow
 *
 * Stage 1: Identify & Save (salary + EMIs)
 * Stage 2: View Optimizations (dashboard with results)
 */

export default function SalarySweepOptimizerV2() {
  // View state: 'setup' or 'dashboard'
  const [view, setView] = useState('loading');

  // Data
  const [salary, setSalary] = useState(null);
  const [savedEMIs, setSavedEMIs] = useState([]);
  const [optimizationResults, setOptimizationResults] = useState(null);

  // Setup mode only
  const [detectingEMIs, setDetectingEMIs] = useState([]);
  const [selectedEMIIds, setSelectedEMIIds] = useState([]);

  // UI state
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // Load on mount
  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      setLoading(true);
      setError(null);

      const savedConfig = await getSavedConfig();

      if (savedConfig && savedConfig.salary_source) {
        // User has saved configuration - show dashboard
        setSalary({
          source: savedConfig.salary_source,
          amount: savedConfig.salary_amount
        });
        setSavedEMIs(savedConfig.confirmed_emis || []);
        setOptimizationResults(savedConfig.optimization_results);
        setView('dashboard');
      } else {
        // No configuration - start setup
        setView('setup');
      }
    } catch (err) {
      console.error('Failed to load:', err);
      setError('Failed to load data');
      setView('setup');
    } finally {
      setLoading(false);
    }
  };

  const handleStartSetup = async () => {
    try {
      setLoading(true);
      setError(null);

      // Detect patterns
      const patterns = await detectOrRefreshPatterns();

      // Check if any data was detected
      if (!patterns.salary && (!patterns.emis || patterns.emis.length === 0)) {
        setError('No salary or recurring payments detected. Please upload your bank statement first to enable automatic detection.');
        setSalary(null);
        setDetectingEMIs([]);
        setView('setup');
        return;
      }

      setSalary(patterns.salary);
      setDetectingEMIs(patterns.emis || []);
      setSelectedEMIIds([]);
      setView('setup');
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to detect patterns');
    } finally {
      setLoading(false);
    }
  };

  const handleToggleEMI = (patternId) => {
    setSelectedEMIIds(prev =>
      prev.includes(patternId)
        ? prev.filter(id => id !== patternId)
        : [...prev, patternId]
    );
  };

  const handleSaveConfiguration = async () => {
    if (!salary) {
      setError('Salary information is required');
      return;
    }

    try {
      setLoading(true);
      setError(null);

      // Save configuration
      const configData = {
        salarySource: salary.source,
        salaryAmount: salary.amount,
        emiPatternIds: selectedEMIIds
      };

      const savedConfig = await confirmConfig(configData);

      // Update state
      setSalary({
        source: savedConfig.salary_source,
        amount: savedConfig.salary_amount
      });
      setSavedEMIs(savedConfig.confirmed_emis || []);
      setOptimizationResults(null); // Clear old results
      setView('dashboard');

      alert('Configuration saved successfully!');
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to save configuration');
    } finally {
      setLoading(false);
    }
  };

  const handleCalculateOptimization = async () => {
    try {
      setLoading(true);
      setError(null);

      const results = await calculateOptimization();
      setOptimizationResults(results.optimization_results);

      alert('Optimization calculated and saved!');
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to calculate optimization');
    } finally {
      setLoading(false);
    }
  };

  const handleAddMoreEMIs = async () => {
    try {
      setLoading(true);
      setError(null);

      // Refresh patterns to get latest
      const patterns = await detectOrRefreshPatterns();
      setDetectingEMIs(patterns.emis || []);
      setSelectedEMIIds(savedEMIs.map(e => e.pattern_id)); // Pre-select already saved
      setView('setup');
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to refresh patterns');
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteEMI = async (patternId) => {
    if (!window.confirm('Delete this EMI pattern?')) return;

    try {
      setLoading(true);
      await deleteEMI(patternId);
      setSavedEMIs(prev => prev.filter(e => e.pattern_id !== patternId));
      // Recalculate if results exist
      if (optimizationResults) {
        const results = await calculateOptimization();
        setOptimizationResults(results.optimization_results);
      }
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to delete EMI');
    } finally {
      setLoading(false);
    }
  };

  const handleResetAll = async () => {
    if (!window.confirm('Delete all saved data and start fresh?')) return;

    try {
      setLoading(true);
      await resetConfig();
      setSalary(null);
      setSavedEMIs([]);
      setOptimizationResults(null);
      setDetectingEMIs([]);
      setSelectedEMIIds([]);
      await handleStartSetup();
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to reset');
    } finally {
      setLoading(false);
    }
  };

  // Helper functions
  const formatCurrency = (amount, compact = true) => {
    if (!amount) return '₹0';
    if (!compact) {
      return `₹${amount.toLocaleString('en-IN', { maximumFractionDigits: 0 })}`;
    }
    if (amount >= 10000000) return `₹${(amount / 10000000).toFixed(2)}Cr`;
    if (amount >= 100000) return `₹${(amount / 100000).toFixed(2)}L`;
    if (amount >= 1000) return `₹${(amount / 1000).toFixed(1)}K`;
    return `₹${amount.toFixed(0)}`;
  };

  const getSuggestionBadge = (action) => {
    switch (action) {
      case 'delete':
        return <span className="inline-block px-2 py-1 bg-red-100 text-red-700 text-xs font-medium rounded-full">🗑️ Suggest Delete</span>;
      case 'update':
        return <span className="inline-block px-2 py-1 bg-yellow-100 text-yellow-700 text-xs font-medium rounded-full">✏️ Suggest Update</span>;
      case 'keep':
        return <span className="inline-block px-2 py-1 bg-green-100 text-green-700 text-xs font-medium rounded-full">✓ Looks Good</span>;
      default:
        return null;
    }
  };

  const getCategoryBadge = (category, subcategory) => {
    const badges = {
      'Loan': { icon: '🏦', color: 'bg-blue-100 text-blue-700', label: subcategory || 'Loan' },
      'Insurance': { icon: '🛡️', color: 'bg-purple-100 text-purple-700', label: subcategory || 'Insurance' },
      'Investment': { icon: '📈', color: 'bg-green-100 text-green-700', label: subcategory || 'Investment' },
      'Government Scheme': { icon: '🏛️', color: 'bg-amber-100 text-amber-700', label: subcategory || 'Govt Scheme' }
    };

    const badge = badges[category] || { icon: '💰', color: 'bg-gray-100 text-gray-700', label: 'Recurring Payment' };

    return (
      <span className={`inline-flex items-center gap-1 px-2 py-1 ${badge.color} text-xs font-medium rounded-full`}>
        <span>{badge.icon}</span>
        <span>{badge.label}</span>
      </span>
    );
  };

  const groupByCategory = (emis) => {
    const grouped = {
      loans: [],
      insurance: [],
      investments: [],
      government_schemes: []
    };

    emis.forEach(emi => {
      if (emi.category === 'Loan') {
        grouped.loans.push(emi);
      } else if (emi.category === 'Insurance') {
        grouped.insurance.push(emi);
      } else if (emi.category === 'Investment') {
        grouped.investments.push(emi);
      } else if (emi.category === 'Government Scheme') {
        grouped.government_schemes.push(emi);
      } else {
        // Default to loans for backward compatibility
        grouped.loans.push(emi);
      }
    });

    return grouped;
  };

  // Loading state
  if (view === 'loading') {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-orange-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Loading your configuration...</p>
        </div>
      </div>
    );
  }

  // STAGE 1: SETUP VIEW (Identify & Save)
  if (view === 'setup') {
    return (
      <div className="space-y-5">
        {/* Error */}
        {error && (
          <div className="bg-red-50 border border-red-200 rounded-xl p-4">
            <p className="text-sm text-red-800">{error}</p>
          </div>
        )}

        {/* Header */}
        <div className="bg-gradient-to-r from-orange-500 to-orange-600 rounded-2xl p-5 text-white">
          <h2 className="text-xl font-bold mb-2">🔍 Stage 1: Identify & Save</h2>
          <p className="text-sm text-orange-100">Select your salary source and recurring EMIs to track</p>
        </div>

        {/* Detect Button */}
        {detectingEMIs.length === 0 && (
          <button
            onClick={handleStartSetup}
            disabled={loading}
            className="w-full bg-orange-600 text-white font-semibold py-4 rounded-xl hover:bg-orange-700 disabled:opacity-50"
          >
            {loading ? 'Detecting patterns...' : '🔍 Detect Salary & EMI Patterns'}
          </button>
        )}

        {/* Detected Salary */}
        {salary && (
          <div className="bg-white rounded-2xl p-5 shadow-sm border border-gray-200">
            <h3 className="text-lg font-semibold text-gray-900 mb-3">✅ Detected Salary</h3>
            <div className="bg-green-50 rounded-xl p-4 border border-green-200">
              <div className="flex items-center justify-between">
                <div>
                  <div className="text-sm text-gray-600 mb-1">Source</div>
                  <div className="text-lg font-bold text-gray-900">{salary.source}</div>
                </div>
                <div className="text-right">
                  <div className="text-sm text-gray-600 mb-1">Amount</div>
                  <div className="text-2xl font-bold text-green-600">{formatCurrency(salary.amount)}</div>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Detected EMIs */}
        {detectingEMIs.length > 0 && (
          <div className="bg-white rounded-2xl p-5 shadow-sm border border-gray-200">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold text-gray-900">💰 Detected EMI Patterns</h3>
              <span className="text-xs text-gray-500">{detectingEMIs.length} patterns found</span>
            </div>

            <p className="text-sm text-gray-600 mb-4">
              Select the EMIs you want to track. These will be saved to your profile.
            </p>

            <div className="space-y-3 max-h-96 overflow-y-auto">
              {detectingEMIs.map((emi) => (
                <div
                  key={emi.pattern_id}
                  className={`border-2 rounded-xl p-4 transition-all cursor-pointer ${
                    selectedEMIIds.includes(emi.pattern_id)
                      ? 'border-orange-400 bg-orange-50'
                      : 'border-gray-200 bg-white hover:border-orange-200'
                  }`}
                  onClick={() => handleToggleEMI(emi.pattern_id)}
                >
                  <div className="flex items-start gap-3">
                    <input
                      type="checkbox"
                      checked={selectedEMIIds.includes(emi.pattern_id)}
                      onChange={() => {}}
                      className="mt-1 w-5 h-5 text-orange-600 rounded"
                    />

                    <div className="flex-1 min-w-0">
                      <div className="flex items-center justify-between mb-2">
                        <div className="flex-1">
                          <div className="font-semibold text-gray-900 truncate">
                            {emi.user_label || emi.merchant_source}
                          </div>
                          {emi.user_label && (
                            <div className="text-xs text-gray-500">{emi.merchant_source}</div>
                          )}
                        </div>
                        <div className="text-right ml-4">
                          <div className="text-lg font-bold text-orange-600">
                            {formatCurrency(emi.emi_amount, false)}
                          </div>
                          <div className="text-xs text-gray-500">
                            {emi.first_detected_date && `Since ${new Date(emi.first_detected_date).toLocaleDateString('en-IN', { month: 'short', year: 'numeric' })}`}
                          </div>
                        </div>
                      </div>

                      {/* Category Badge */}
                      {emi.category && (
                        <div className="mb-2">
                          {getCategoryBadge(emi.category, emi.subcategory)}
                        </div>
                      )}

                      {/* Suggestion Badge */}
                      {emi.suggested_action && (
                        <div className="mb-2">
                          {getSuggestionBadge(emi.suggested_action)}
                          {emi.suggestion_reason && (
                            <p className="text-xs text-gray-600 mt-1">{emi.suggestion_reason}</p>
                          )}
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>

            {/* Save Button */}
            <button
              onClick={handleSaveConfiguration}
              disabled={loading || selectedEMIIds.length === 0}
              className="w-full mt-4 bg-orange-600 text-white font-semibold py-3 rounded-xl hover:bg-orange-700 disabled:opacity-50"
            >
              {loading ? 'Saving...' : `💾 Save Configuration (${selectedEMIIds.length} EMIs selected)`}
            </button>
          </div>
        )}
      </div>
    );
  }

  // STAGE 2: DASHBOARD VIEW
  return (
    <div className="space-y-5">
      {/* Error */}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-xl p-4">
          <p className="text-sm text-red-800">{error}</p>
        </div>
      )}

      {/* Header */}
      <div className="bg-gradient-to-r from-orange-500 to-orange-600 rounded-2xl p-5 text-white">
        <h2 className="text-xl font-bold mb-2">💰 Salary Sweep Dashboard</h2>
        <p className="text-sm text-orange-100">Your saved income and EMI tracking</p>
      </div>

      {/* Salary Card */}
      <div className="bg-white rounded-2xl p-5 shadow-sm border border-gray-200">
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-lg font-semibold text-gray-900">💵 Income Source</h3>
        </div>
        <div className="bg-gradient-to-r from-green-50 to-emerald-50 rounded-xl p-4 border border-green-200">
          <div className="flex items-center justify-between">
            <div>
              <div className="text-sm text-gray-600 mb-1">Source</div>
              <div className="text-xl font-bold text-gray-900">{salary?.source || 'Not set'}</div>
            </div>
            <div className="text-right">
              <div className="text-sm text-gray-600 mb-1">Amount</div>
              <div className="text-2xl font-bold text-green-600">{formatCurrency(salary?.amount || 0)}</div>
            </div>
          </div>
        </div>
      </div>

      {/* Recurring Payments Card */}
      <div className="bg-white rounded-2xl p-5 shadow-sm border border-gray-200">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold text-gray-900">📋 Tracked Recurring Payments</h3>
          <button
            onClick={handleAddMoreEMIs}
            disabled={loading}
            className="px-3 py-1 bg-orange-600 text-white text-sm font-medium rounded-lg hover:bg-orange-700 disabled:opacity-50"
          >
            + Add More
          </button>
        </div>

        {savedEMIs.length === 0 ? (
          <div className="text-center py-8 text-gray-500">
            <p>No recurring payments tracked yet</p>
            <button
              onClick={handleAddMoreEMIs}
              className="mt-3 text-orange-600 hover:text-orange-700 font-medium"
            >
              Add your first payment
            </button>
          </div>
        ) : (
          <div className="space-y-3">
            {savedEMIs.map((emi) => (
              <div
                key={emi.pattern_id}
                className="border border-gray-200 rounded-xl p-4 bg-gray-50"
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="font-semibold text-gray-900">
                      {emi.user_label || emi.merchant_source}
                    </div>
                    {emi.user_label && (
                      <div className="text-xs text-gray-500">{emi.merchant_source}</div>
                    )}

                    {/* Category Badge */}
                    {emi.category && (
                      <div className="mt-2">
                        {getCategoryBadge(emi.category, emi.subcategory)}
                      </div>
                    )}

                    <div className="text-xs text-gray-500 mt-1">
                      {emi.first_detected_date && (
                        <>
                          Started: {new Date(emi.first_detected_date).toLocaleDateString('en-IN', { month: 'short', year: 'numeric' })}
                          {emi.occurrence_count && ` • ${emi.occurrence_count} payments`}
                        </>
                      )}
                    </div>
                  </div>
                  <div className="text-right">
                    <div className="text-xl font-bold text-orange-600">
                      {formatCurrency(emi.emi_amount, false)}
                    </div>
                    <button
                      onClick={() => handleDeleteEMI(emi.pattern_id)}
                      disabled={loading}
                      className="text-xs text-red-600 hover:text-red-700 mt-1"
                    >
                      🗑️ Delete
                    </button>
                  </div>
                </div>
              </div>
            ))}

            {/* Category Summary */}
            {(() => {
              const grouped = groupByCategory(savedEMIs);
              const hasMultipleCategories = Object.values(grouped).filter(arr => arr.length > 0).length > 1;

              if (hasMultipleCategories) {
                return (
                  <div className="border-t-2 border-gray-300 pt-3 mt-3">
                    <div className="text-xs text-gray-600 mb-2">Category Breakdown:</div>
                    <div className="grid grid-cols-2 gap-2 text-xs mb-3">
                      {grouped.loans.length > 0 && (
                        <div className="flex justify-between">
                          <span>🏦 Loans:</span>
                          <span className="font-semibold">{formatCurrency(grouped.loans.reduce((sum, e) => sum + e.emi_amount, 0))}</span>
                        </div>
                      )}
                      {grouped.insurance.length > 0 && (
                        <div className="flex justify-between">
                          <span>🛡️ Insurance:</span>
                          <span className="font-semibold">{formatCurrency(grouped.insurance.reduce((sum, e) => sum + e.emi_amount, 0))}</span>
                        </div>
                      )}
                      {grouped.investments.length > 0 && (
                        <div className="flex justify-between">
                          <span>📈 Investments:</span>
                          <span className="font-semibold">{formatCurrency(grouped.investments.reduce((sum, e) => sum + e.emi_amount, 0))}</span>
                        </div>
                      )}
                      {grouped.government_schemes.length > 0 && (
                        <div className="flex justify-between">
                          <span>🏛️ Govt Schemes:</span>
                          <span className="font-semibold">{formatCurrency(grouped.government_schemes.reduce((sum, e) => sum + e.emi_amount, 0))}</span>
                        </div>
                      )}
                    </div>
                  </div>
                );
              }
              return null;
            })()}

            {/* Total */}
            <div className="border-t-2 border-gray-300 pt-3 mt-3">
              <div className="flex items-center justify-between">
                <span className="font-semibold text-gray-700">Total Monthly Outflow</span>
                <span className="text-2xl font-bold text-orange-600">
                  {formatCurrency(savedEMIs.reduce((sum, emi) => sum + emi.emi_amount, 0), false)}
                </span>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Show Optimization Button */}
      {savedEMIs.length > 0 && (
        <button
          onClick={handleCalculateOptimization}
          disabled={loading}
          className="w-full bg-gradient-to-r from-orange-600 to-orange-700 text-white font-bold py-4 rounded-xl hover:from-orange-700 hover:to-orange-800 disabled:opacity-50 shadow-lg"
        >
          {loading ? 'Calculating...' : '📊 Show Optimization Results'}
        </button>
      )}

      {/* Optimization Results */}
      {optimizationResults && (
        <div className="space-y-4">
          <div className="bg-white rounded-2xl p-5 shadow-sm border border-gray-200">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">🎯 Optimization Results</h3>

            {/* Recommendation */}
            <div className="bg-gradient-to-r from-green-50 to-emerald-50 rounded-xl p-4 border border-green-200 mb-4">
              <div className="text-center">
                <div className="text-sm text-gray-600 mb-1">💰 You can save</div>
                <div className="text-3xl font-bold text-green-600 mb-2">
                  {formatCurrency(optimizationResults.interest_gain_vs_current)}/year
                </div>
                <p className="text-xs text-gray-600">{optimizationResults.recommendation}</p>
              </div>
            </div>

            <h4 className="font-semibold text-gray-900 mb-3 text-sm">📊 Compare Scenarios:</h4>

            {/* Scenario 1: Current */}
            <div className="border-2 border-gray-200 rounded-xl p-4 mb-3 bg-gray-50">
              <div className="flex items-center justify-between mb-2">
                <span className="font-semibold text-gray-900">❌ {optimizationResults.current_scenario.name}</span>
                <span className="text-xs bg-gray-200 text-gray-700 px-2 py-1 rounded-full">Current</span>
              </div>
              <p className="text-xs text-gray-600 mb-3">{optimizationResults.current_scenario.description}</p>

              <div className="grid grid-cols-2 gap-2 text-xs">
                <div>
                  <div className="text-gray-500">Salary Account (2.5%)</div>
                  <div className="font-semibold">{formatCurrency(optimizationResults.current_scenario.salary_account_balance, false)}</div>
                </div>
                <div>
                  <div className="text-gray-500">Savings Account (7%)</div>
                  <div className="font-semibold">{formatCurrency(optimizationResults.current_scenario.savings_account_balance, false)}</div>
                </div>
              </div>

              <div className="mt-3 pt-3 border-t border-gray-300">
                <div className="flex justify-between items-center">
                  <span className="text-gray-600 text-xs">Annual Interest:</span>
                  <span className="font-bold text-gray-700">{formatCurrency(optimizationResults.current_scenario.total_annual_interest)}/yr</span>
                </div>
              </div>
            </div>

            {/* Scenario 2: Uniform Sweep */}
            <div className="border-2 border-blue-200 rounded-xl p-4 mb-3 bg-blue-50">
              <div className="flex items-center justify-between mb-2">
                <span className="font-semibold text-gray-900">💙 {optimizationResults.uniform_sweep.name}</span>
                <span className="text-xs bg-blue-200 text-blue-700 px-2 py-1 rounded-full">Good</span>
              </div>
              <p className="text-xs text-gray-600 mb-3">{optimizationResults.uniform_sweep.description}</p>

              <div className="grid grid-cols-2 gap-2 text-xs mb-2">
                <div>
                  <div className="text-gray-500">Salary Account (2.5%)</div>
                  <div className="font-semibold">{formatCurrency(optimizationResults.uniform_sweep.salary_account_balance, false)}</div>
                  <div className="text-xs text-gray-500">For EMI payments</div>
                </div>
                <div>
                  <div className="text-gray-500">Savings Account (7%)</div>
                  <div className="font-semibold text-green-600">{formatCurrency(optimizationResults.uniform_sweep.savings_account_balance, false)}</div>
                  <div className="text-xs text-gray-500">~{optimizationResults.uniform_sweep.avg_days_in_savings} days avg</div>
                </div>
              </div>

              <div className="mt-3 pt-3 border-t border-blue-300">
                <div className="flex justify-between items-center">
                  <span className="text-gray-600 text-xs">Annual Interest:</span>
                  <span className="font-bold text-blue-700">{formatCurrency(optimizationResults.uniform_sweep.total_annual_interest)}/yr</span>
                </div>
                <div className="text-xs text-green-600 mt-1">
                  +{formatCurrency(optimizationResults.uniform_sweep.total_annual_interest - optimizationResults.current_scenario.total_annual_interest)} vs current
                </div>
              </div>
            </div>

            {/* Scenario 3: Optimized */}
            <div className="border-2 border-green-300 rounded-xl p-4 bg-gradient-to-br from-green-50 to-emerald-50">
              <div className="flex items-center justify-between mb-2">
                <span className="font-semibold text-gray-900">✨ {optimizationResults.optimized_sweep.name}</span>
                <span className="text-xs bg-green-200 text-green-800 px-2 py-1 rounded-full font-bold">⭐ BEST</span>
              </div>
              <p className="text-xs text-gray-600 mb-3">{optimizationResults.optimized_sweep.description}</p>

              <div className="grid grid-cols-2 gap-2 text-xs mb-2">
                <div>
                  <div className="text-gray-500">Salary Account (2.5%)</div>
                  <div className="font-semibold">{formatCurrency(optimizationResults.optimized_sweep.salary_account_balance, false)}</div>
                  <div className="text-xs text-gray-500">For EMI payments</div>
                </div>
                <div>
                  <div className="text-gray-500">Savings Account (7%)</div>
                  <div className="font-semibold text-green-600">{formatCurrency(optimizationResults.optimized_sweep.savings_account_balance, false)}</div>
                  <div className="text-xs text-gray-500">~{optimizationResults.optimized_sweep.avg_days_in_savings} days avg</div>
                </div>
              </div>

              <div className="bg-white/50 rounded-lg p-2 mb-2 text-xs">
                <div className="text-gray-600 mb-1">Strategy:</div>
                <div className="font-medium text-gray-900">{optimizationResults.optimized_sweep.emi_dates}</div>
              </div>

              <div className="mt-3 pt-3 border-t border-green-300">
                <div className="flex justify-between items-center">
                  <span className="text-gray-600 text-xs">Annual Interest:</span>
                  <span className="font-bold text-green-700 text-lg">{formatCurrency(optimizationResults.optimized_sweep.total_annual_interest)}/yr</span>
                </div>
                <div className="text-xs text-green-600 font-semibold mt-1">
                  🎉 +{formatCurrency(optimizationResults.interest_gain_vs_current)} vs current (Best savings!)
                </div>
              </div>
            </div>

            {/* How it works explanation */}
            <div className="mt-4 bg-blue-50 border border-blue-200 rounded-xl p-4">
              <h5 className="font-semibold text-sm text-gray-900 mb-2">💡 How This Works:</h5>
              <div className="space-y-2 text-xs text-gray-700">
                <p>1. <strong>Current:</strong> All money stays in salary account (2.5% interest)</p>
                <p>2. <strong>Uniform Sweep:</strong> Pay all EMIs on day 1, move surplus to savings (7% interest) for ~15 days average</p>
                <p>3. <strong>Optimized:</strong> Stagger EMI payments throughout month, keep surplus in savings longer (~20 days average)</p>
                <p className="text-green-700 font-medium mt-2">✨ More days in high-interest savings = More money earned!</p>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Reset Button */}
      <button
        onClick={handleResetAll}
        disabled={loading}
        className="w-full border border-red-300 text-red-700 font-medium py-3 rounded-xl hover:bg-red-50 disabled:opacity-50"
      >
        🗑️ Reset All Configuration
      </button>
    </div>
  );
}
