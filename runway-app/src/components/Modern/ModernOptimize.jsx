// src/components/Modern/ModernOptimize.jsx
import React, { useState, useEffect, useRef } from 'react';
import { getAllRecurringPayments } from '../../api/services/recurringPayments';
import { detectOrRefreshPatterns, confirmConfig, resetConfig, updateEMI, deleteEMI } from '../../api/services/salarySweepV2';

/**
 * ModernOptimize - Hub for all financial optimization tools
 * Now includes centralized recurring payment setup
 */

const optimizers = [
  {
    id: 'salary-sweep',
    title: 'Salary Sweep',
    description: 'Maximize interest earnings by auto-sweeping surplus to high-interest accounts',
    icon: '💰',
    gradient: 'from-green-400 to-emerald-500',
    benefits: ['Earn ₹6K-10K/year', 'Zero effort', 'Auto-detect'],
    status: 'active'
  },
  {
    id: 'loan-prepayment',
    title: 'Loan Prepayment',
    description: 'Close high-interest loans faster and save lakhs in interest',
    icon: '🎯',
    gradient: 'from-red-400 to-orange-500',
    benefits: ['Save ₹4L+ interest', 'Reduce tenure', 'Smart priority'],
    status: 'active'
  },
  {
    id: 'tax-optimizer',
    title: 'Tax Optimizer',
    description: 'Maximize deductions and plan tax-saving investments',
    icon: '📊',
    gradient: 'from-blue-400 to-cyan-500',
    benefits: ['Save up to ₹1.5L tax', 'Auto-detect 80C', 'Plan ahead'],
    status: 'coming_soon'
  },
  {
    id: 'investment-rebalancer',
    title: 'Investment Optimizer',
    description: 'Track investments across platforms and optimize your portfolio',
    icon: '📈',
    gradient: 'from-purple-400 to-indigo-500',
    benefits: ['Platform tracking', 'SIP detection', 'Portfolio insights'],
    status: 'active'
  },
  {
    id: 'credit-card-optimizer',
    title: 'Credit Card Optimizer',
    description: 'Maximize rewards and minimize interest charges',
    icon: '💳',
    gradient: 'from-pink-400 to-rose-500',
    benefits: ['Max cashback', 'Smart payments', 'Due alerts'],
    status: 'coming_soon'
  },
  {
    id: 'expense-optimizer',
    title: 'Expense Optimizer',
    description: 'Find subscription leaks and reduce unnecessary spending',
    icon: '🔍',
    gradient: 'from-yellow-400 to-amber-500',
    benefits: ['Find leaks', 'Save ₹2K+/month', 'Track subs'],
    status: 'coming_soon'
  }
];

export default function ModernOptimize({ onNavigate }) {
  // State for recurring payments setup
  const [hasRecurringPayments, setHasRecurringPayments] = useState(false);
  const [recurringPayments, setRecurringPayments] = useState(null);
  const [showSetup, setShowSetup] = useState(false);
  const [loading, setLoading] = useState(true);
  const [detecting, setDetecting] = useState(false);
  const [detectedPatterns, setDetectedPatterns] = useState(null);
  const [selectedPatterns, setSelectedPatterns] = useState([]);
  const [detectionError, setDetectionError] = useState(null);

  // Edit Mode states
  const [editMode, setEditMode] = useState(false);
  const [editingPayment, setEditingPayment] = useState(null);
  const [editValues, setEditValues] = useState({ userLabel: '', emiAmount: '' });

  // Undo/Redo states
  const [history, setHistory] = useState([]);
  const [historyIndex, setHistoryIndex] = useState(-1);
  const isUndoRedoAction = useRef(false);

  // Load recurring payments on mount
  useEffect(() => {
    loadRecurringPayments();
  }, []);

  // Track configuration changes for undo/redo
  useEffect(() => {
    if (!isUndoRedoAction.current && recurringPayments && hasRecurringPayments) {
      const snapshot = JSON.parse(JSON.stringify(recurringPayments));
      setHistory(prev => {
        const newHistory = prev.slice(0, historyIndex + 1);
        newHistory.push(snapshot);
        // Keep only last 20 states to avoid memory issues
        return newHistory.slice(-20);
      });
      setHistoryIndex(prev => Math.min(prev + 1, 19));
    }
    isUndoRedoAction.current = false;
  }, [recurringPayments]);

  const loadRecurringPayments = async () => {
    try {
      setLoading(true);
      const data = await getAllRecurringPayments();
      const totalPayments =
        (data.loans?.length || 0) +
        (data.insurance?.length || 0) +
        (data.investments?.length || 0) +
        (data.government_schemes?.length || 0);

      if (totalPayments > 0) {
        setHasRecurringPayments(true);
        setRecurringPayments(data);
      }
    } catch (err) {
      console.error('Failed to load recurring payments:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleDetectPatterns = async () => {
    try {
      setDetecting(true);
      setDetectionError(null);
      const patterns = await detectOrRefreshPatterns();

      // Check if any data was detected
      if (!patterns.salary && (!patterns.emis || patterns.emis.length === 0)) {
        setDetectionError('no_transactions');
        setDetecting(false);
        return;
      }

      setDetectedPatterns(patterns);
      setShowSetup(true);

      // Auto-select all patterns
      setSelectedPatterns(patterns.emis?.map(e => e.pattern_id) || []);
    } catch (err) {
      console.error('Failed to detect patterns:', err);
      setDetectionError('detection_failed');
    } finally {
      setDetecting(false);
    }
  };

  const handleTogglePattern = (patternId) => {
    setSelectedPatterns(prev =>
      prev.includes(patternId)
        ? prev.filter(id => id !== patternId)
        : [...prev, patternId]
    );
  };

  const handleSaveConfiguration = async () => {
    try {
      setDetecting(true);
      await confirmConfig({
        salarySource: detectedPatterns.salary?.source || 'Unknown',
        salaryAmount: detectedPatterns.salary?.amount || 0,
        emiPatternIds: selectedPatterns,
        salaryAccountRate: 2.5,
        savingsAccountRate: 7.0
      });

      // Reload recurring payments
      await loadRecurringPayments();
      setShowSetup(false);
      alert('✅ Recurring payments saved! All optimizers can now use this data.');
    } catch (err) {
      console.error('Failed to save configuration:', err);
      alert('Failed to save. Please try again.');
    } finally {
      setDetecting(false);
    }
  };

  const handleResetAll = async () => {
    const totalPayments =
      (recurringPayments?.loans?.length || 0) +
      (recurringPayments?.insurance?.length || 0) +
      (recurringPayments?.investments?.length || 0) +
      (recurringPayments?.government_schemes?.length || 0);

    if (!window.confirm(
      `⚠️ Delete all ${totalPayments} recurring payments?\n\n` +
      'This will reset the configuration for ALL optimizers.\n' +
      'This action cannot be undone.'
    )) {
      return;
    }

    try {
      setDetecting(true);
      await resetConfig();

      // Clear all state
      setHasRecurringPayments(false);
      setRecurringPayments(null);
      setDetectedPatterns(null);
      setSelectedPatterns([]);
      setShowSetup(false);
      setHistory([]);
      setHistoryIndex(-1);

      alert('✅ Configuration reset successfully! You can now set up fresh.');
    } catch (err) {
      console.error('Failed to reset configuration:', err);
      alert('❌ Failed to reset configuration. Please try again.');
    } finally {
      setDetecting(false);
    }
  };

  const handleEditMode = () => {
    setEditMode(!editMode);
    setEditingPayment(null);
  };

  const handleStartEdit = (payment) => {
    setEditingPayment(payment.pattern_id);
    setEditValues({
      userLabel: payment.user_label || payment.merchant_source,
      emiAmount: payment.emi_amount.toString()
    });
  };

  const handleCancelEdit = () => {
    setEditingPayment(null);
    setEditValues({ userLabel: '', emiAmount: '' });
  };

  const handleSaveEdit = async (patternId) => {
    try {
      setDetecting(true);
      await updateEMI(patternId, {
        userLabel: editValues.userLabel,
        emiAmount: parseFloat(editValues.emiAmount)
      });

      // Reload data
      await loadRecurringPayments();
      setEditingPayment(null);
      setEditValues({ userLabel: '', emiAmount: '' });
    } catch (err) {
      console.error('Failed to update payment:', err);
      alert('❌ Failed to update payment. Please try again.');
    } finally {
      setDetecting(false);
    }
  };

  const handleDeletePayment = async (patternId, merchantSource) => {
    if (!window.confirm(`Delete "${merchantSource}"?`)) {
      return;
    }

    try {
      setDetecting(true);
      await deleteEMI(patternId);

      // Reload data
      await loadRecurringPayments();
    } catch (err) {
      console.error('Failed to delete payment:', err);
      alert('❌ Failed to delete payment. Please try again.');
    } finally {
      setDetecting(false);
    }
  };

  const handleUndo = () => {
    if (historyIndex > 0) {
      isUndoRedoAction.current = true;
      const previousState = history[historyIndex - 1];
      setRecurringPayments(previousState);
      setHistoryIndex(historyIndex - 1);
    }
  };

  const handleRedo = () => {
    if (historyIndex < history.length - 1) {
      isUndoRedoAction.current = true;
      const nextState = history[historyIndex + 1];
      setRecurringPayments(nextState);
      setHistoryIndex(historyIndex + 1);
    }
  };

  const handleExport = () => {
    const exportData = {
      version: '1.0',
      exported_at: new Date().toISOString(),
      data: recurringPayments
    };

    const blob = new Blob([JSON.stringify(exportData, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `recurring-payments-${new Date().toISOString().split('T')[0]}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const handleImport = (event) => {
    const file = event.target.files?.[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = (e) => {
      try {
        const imported = JSON.parse(e.target?.result);
        if (imported.version && imported.data) {
          setRecurringPayments(imported.data);
          setHasRecurringPayments(true);
          alert('✅ Configuration imported successfully!');
        } else {
          alert('❌ Invalid file format');
        }
      } catch (err) {
        console.error('Import error:', err);
        alert('❌ Failed to import configuration');
      }
    };
    reader.readAsText(file);
  };

  const handleOptimizerClick = (optimizer) => {
    if (optimizer.status === 'active') {
      onNavigate(optimizer.id);
    }
  };

  const formatCurrency = (amount) => {
    if (!amount) return '₹0';
    return `₹${Math.round(amount).toLocaleString('en-IN')}`;
  };

  const getCategoryBadge = (category, subcategory) => {
    const badges = {
      'Loan': { icon: '🏦', color: 'bg-blue-100 text-blue-700' },
      'Insurance': { icon: '🛡️', color: 'bg-purple-100 text-purple-700' },
      'Investment': { icon: '📈', color: 'bg-green-100 text-green-700' },
      'Government Scheme': { icon: '🏛️', color: 'bg-amber-100 text-amber-700' }
    };
    const badge = badges[category] || { icon: '💰', color: 'bg-gray-100 text-gray-700' };
    return (
      <span className={`inline-flex items-center gap-1 px-2 py-1 ${badge.color} text-xs font-medium rounded-full`}>
        {badge.icon} {subcategory || category}
      </span>
    );
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 pb-24">
      {/* Header */}
      <div className="bg-white/80 backdrop-blur-md sticky top-0 z-20 border-b border-gray-100">
        <div className="max-w-lg mx-auto px-4 py-6">
          <div className="flex items-center gap-3 mb-2">
            <div className="bg-gradient-to-br from-purple-500 to-indigo-600 text-white p-3 rounded-2xl">
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
              </svg>
            </div>
            <div>
              <h1 className="text-2xl font-bold text-gray-900">Optimize</h1>
              <p className="text-sm text-gray-500">Financial optimization tools</p>
            </div>
          </div>

          {/* Stats Bar */}
          <div className="flex items-center gap-4 mt-4 p-3 bg-gradient-to-r from-green-50 to-emerald-50 rounded-xl border border-green-200">
            <div className="flex-1 text-center">
              <div className="text-xl font-bold text-green-600">₹10K+</div>
              <div className="text-xs text-gray-600">Potential Savings/yr</div>
            </div>
            <div className="w-px h-10 bg-green-300"></div>
            <div className="flex-1 text-center">
              <div className="text-xl font-bold text-purple-600">{optimizers.filter(o => o.status === 'active').length}</div>
              <div className="text-xs text-gray-600">Active Tools</div>
            </div>
            <div className="w-px h-10 bg-green-300"></div>
            <div className="flex-1 text-center">
              <div className="text-xl font-bold text-blue-600">{optimizers.filter(o => o.status === 'coming_soon').length}</div>
              <div className="text-xs text-gray-600">Coming Soon</div>
            </div>
          </div>
        </div>
      </div>

      {/* Centralized Recurring Payments Setup */}
      <div className="max-w-lg mx-auto px-4 py-6">
        {!loading && !hasRecurringPayments && !showSetup && (
          <div className="mb-6 bg-gradient-to-r from-orange-50 to-amber-50 border-2 border-orange-200 rounded-2xl p-5">
            <div className="flex items-start gap-3 mb-3">
              <span className="text-3xl">🎯</span>
              <div className="flex-1">
                <h3 className="text-lg font-bold text-gray-900 mb-1">Set Up Your Recurring Payments</h3>
                <p className="text-sm text-gray-600 mb-3">
                  Detect your EMIs, insurance, investments, and pension payments once - all optimizers will use this data automatically!
                </p>
                <button
                  onClick={handleDetectPatterns}
                  disabled={detecting}
                  className="w-full bg-gradient-to-r from-orange-500 to-orange-600 text-white font-semibold py-3 rounded-xl hover:from-orange-600 hover:to-orange-700 disabled:opacity-50"
                >
                  {detecting ? 'Detecting...' : '🔍 Detect Recurring Payments'}
                </button>

                {/* Error Messages */}
                {detectionError === 'no_transactions' && (
                  <div className="mt-4 bg-yellow-50 border-2 border-yellow-300 rounded-xl p-4">
                    <div className="flex items-start gap-3">
                      <span className="text-2xl">⚠️</span>
                      <div className="flex-1">
                        <h4 className="font-semibold text-gray-900 mb-1">No Transaction Data Found</h4>
                        <p className="text-sm text-gray-700 mb-3">
                          To detect recurring payments automatically, you need to upload your bank statement first.
                        </p>
                        <button
                          onClick={() => onNavigate('transactions')}
                          className="bg-yellow-500 hover:bg-yellow-600 text-white font-medium px-4 py-2 rounded-lg text-sm"
                        >
                          📤 Upload Bank Statement
                        </button>
                      </div>
                    </div>
                  </div>
                )}

                {detectionError === 'detection_failed' && (
                  <div className="mt-4 bg-red-50 border-2 border-red-300 rounded-xl p-4">
                    <div className="flex items-start gap-3">
                      <span className="text-2xl">❌</span>
                      <div className="flex-1">
                        <h4 className="font-semibold text-gray-900 mb-1">Detection Failed</h4>
                        <p className="text-sm text-gray-700">
                          Something went wrong while detecting patterns. Please try again.
                        </p>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        {hasRecurringPayments && recurringPayments && !editMode && (
          <div className="mb-6 bg-white border-2 border-green-200 rounded-2xl p-5">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-2">
                <span className="text-2xl">✅</span>
                <h3 className="text-lg font-bold text-gray-900">Your Recurring Payments</h3>
              </div>
              <div className="flex gap-2">
                {/* Undo/Redo buttons */}
                <button
                  onClick={handleUndo}
                  disabled={historyIndex <= 0 || detecting}
                  className="text-xs bg-blue-100 hover:bg-blue-200 text-blue-700 px-2 py-1 rounded-lg font-medium disabled:opacity-30"
                  title="Undo"
                >
                  ↶
                </button>
                <button
                  onClick={handleRedo}
                  disabled={historyIndex >= history.length - 1 || detecting}
                  className="text-xs bg-blue-100 hover:bg-blue-200 text-blue-700 px-2 py-1 rounded-lg font-medium disabled:opacity-30"
                  title="Redo"
                >
                  ↷
                </button>

                <button
                  onClick={handleDetectPatterns}
                  disabled={detecting}
                  className="text-xs bg-gray-100 hover:bg-gray-200 text-gray-700 px-3 py-1 rounded-lg font-medium disabled:opacity-50"
                >
                  + Add More
                </button>
                <button
                  onClick={handleEditMode}
                  disabled={detecting}
                  className="text-xs bg-indigo-100 hover:bg-indigo-200 text-indigo-700 px-3 py-1 rounded-lg font-medium disabled:opacity-50"
                >
                  ✏️ Edit
                </button>
                <button
                  onClick={handleResetAll}
                  disabled={detecting}
                  className="text-xs bg-red-100 hover:bg-red-200 text-red-700 px-3 py-1 rounded-lg font-medium disabled:opacity-50"
                >
                  🔄 Reset
                </button>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-2 text-sm mb-3">
              {recurringPayments.loans?.length > 0 && (
                <div className="bg-blue-50 rounded-lg p-2">
                  <div className="text-blue-600 font-semibold">🏦 {recurringPayments.loans.length} Loans</div>
                  <div className="text-xs text-gray-600">
                    {formatCurrency(recurringPayments.loans.reduce((sum, l) => sum + l.emi_amount, 0))}/mo
                  </div>
                </div>
              )}
              {recurringPayments.insurance?.length > 0 && (
                <div className="bg-purple-50 rounded-lg p-2">
                  <div className="text-purple-600 font-semibold">🛡️ {recurringPayments.insurance.length} Insurance</div>
                  <div className="text-xs text-gray-600">
                    {formatCurrency(recurringPayments.insurance.reduce((sum, i) => sum + i.emi_amount, 0))}/mo
                  </div>
                </div>
              )}
              {recurringPayments.investments?.length > 0 && (
                <div className="bg-green-50 rounded-lg p-2">
                  <div className="text-green-600 font-semibold">📈 {recurringPayments.investments.length} Investments</div>
                  <div className="text-xs text-gray-600">
                    {formatCurrency(recurringPayments.investments.reduce((sum, i) => sum + i.emi_amount, 0))}/mo
                  </div>
                </div>
              )}
              {recurringPayments.government_schemes?.length > 0 && (
                <div className="bg-amber-50 rounded-lg p-2">
                  <div className="text-amber-600 font-semibold">🏛️ {recurringPayments.government_schemes.length} Schemes</div>
                  <div className="text-xs text-gray-600">
                    {formatCurrency(recurringPayments.government_schemes.reduce((sum, g) => sum + g.emi_amount, 0))}/mo
                  </div>
                </div>
              )}
            </div>

            <div className="text-xs text-gray-500 bg-gray-50 rounded-lg p-2">
              💡 All optimizers below use this data automatically
            </div>
          </div>
        )}

        {/* Edit Mode View */}
        {hasRecurringPayments && recurringPayments && editMode && (
          <div className="mb-6 bg-white border-2 border-indigo-200 rounded-2xl p-5">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-2">
                <span className="text-2xl">✏️</span>
                <h3 className="text-lg font-bold text-gray-900">Edit Recurring Payments</h3>
              </div>
              <div className="flex gap-2">
                {/* Export/Import */}
                <button
                  onClick={handleExport}
                  disabled={detecting}
                  className="text-xs bg-green-100 hover:bg-green-200 text-green-700 px-3 py-1 rounded-lg font-medium disabled:opacity-50"
                >
                  ⬇ Export
                </button>
                <label className="text-xs bg-green-100 hover:bg-green-200 text-green-700 px-3 py-1 rounded-lg font-medium cursor-pointer">
                  ⬆ Import
                  <input
                    type="file"
                    accept=".json"
                    onChange={handleImport}
                    className="hidden"
                  />
                </label>
                <button
                  onClick={handleEditMode}
                  disabled={detecting}
                  className="text-xs bg-gray-100 hover:bg-gray-200 text-gray-700 px-3 py-1 rounded-lg font-medium disabled:opacity-50"
                >
                  ✓ Done
                </button>
              </div>
            </div>

            <div className="space-y-3 max-h-96 overflow-y-auto">
              {/* Loans */}
              {recurringPayments.loans?.map((payment) => (
                <div key={payment.pattern_id} className="border-2 border-blue-200 rounded-xl p-3 bg-blue-50">
                  {editingPayment === payment.pattern_id ? (
                    <div className="space-y-2">
                      <input
                        type="text"
                        value={editValues.userLabel}
                        onChange={(e) => setEditValues({...editValues, userLabel: e.target.value})}
                        className="w-full px-2 py-1 border rounded text-sm"
                        placeholder="Label"
                      />
                      <input
                        type="number"
                        value={editValues.emiAmount}
                        onChange={(e) => setEditValues({...editValues, emiAmount: e.target.value})}
                        className="w-full px-2 py-1 border rounded text-sm"
                        placeholder="Amount"
                      />
                      <div className="flex gap-2">
                        <button
                          onClick={() => handleSaveEdit(payment.pattern_id)}
                          className="flex-1 bg-green-600 text-white py-1 px-2 rounded text-xs font-medium"
                        >
                          ✓ Save
                        </button>
                        <button
                          onClick={handleCancelEdit}
                          className="flex-1 bg-gray-200 text-gray-700 py-1 px-2 rounded text-xs font-medium"
                        >
                          ✕ Cancel
                        </button>
                      </div>
                    </div>
                  ) : (
                    <div className="flex items-center justify-between">
                      <div className="flex-1">
                        <div className="font-semibold text-blue-900">
                          {payment.user_label || payment.merchant_source}
                        </div>
                        <div className="text-xs text-blue-600">
                          {formatCurrency(payment.emi_amount)}/mo • 🏦 Loan
                        </div>
                      </div>
                      <div className="flex gap-2">
                        <button
                          onClick={() => handleStartEdit(payment)}
                          disabled={detecting}
                          className="text-xs bg-blue-200 hover:bg-blue-300 text-blue-800 px-2 py-1 rounded"
                        >
                          ✏️
                        </button>
                        <button
                          onClick={() => handleDeletePayment(payment.pattern_id, payment.merchant_source)}
                          disabled={detecting}
                          className="text-xs bg-red-200 hover:bg-red-300 text-red-800 px-2 py-1 rounded"
                        >
                          🗑️
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              ))}

              {/* Insurance */}
              {recurringPayments.insurance?.map((payment) => (
                <div key={payment.pattern_id} className="border-2 border-purple-200 rounded-xl p-3 bg-purple-50">
                  {editingPayment === payment.pattern_id ? (
                    <div className="space-y-2">
                      <input
                        type="text"
                        value={editValues.userLabel}
                        onChange={(e) => setEditValues({...editValues, userLabel: e.target.value})}
                        className="w-full px-2 py-1 border rounded text-sm"
                        placeholder="Label"
                      />
                      <input
                        type="number"
                        value={editValues.emiAmount}
                        onChange={(e) => setEditValues({...editValues, emiAmount: e.target.value})}
                        className="w-full px-2 py-1 border rounded text-sm"
                        placeholder="Amount"
                      />
                      <div className="flex gap-2">
                        <button
                          onClick={() => handleSaveEdit(payment.pattern_id)}
                          className="flex-1 bg-green-600 text-white py-1 px-2 rounded text-xs font-medium"
                        >
                          ✓ Save
                        </button>
                        <button
                          onClick={handleCancelEdit}
                          className="flex-1 bg-gray-200 text-gray-700 py-1 px-2 rounded text-xs font-medium"
                        >
                          ✕ Cancel
                        </button>
                      </div>
                    </div>
                  ) : (
                    <div className="flex items-center justify-between">
                      <div className="flex-1">
                        <div className="font-semibold text-purple-900">
                          {payment.user_label || payment.merchant_source}
                        </div>
                        <div className="text-xs text-purple-600">
                          {formatCurrency(payment.emi_amount)}/mo • 🛡️ Insurance
                        </div>
                      </div>
                      <div className="flex gap-2">
                        <button
                          onClick={() => handleStartEdit(payment)}
                          disabled={detecting}
                          className="text-xs bg-purple-200 hover:bg-purple-300 text-purple-800 px-2 py-1 rounded"
                        >
                          ✏️
                        </button>
                        <button
                          onClick={() => handleDeletePayment(payment.pattern_id, payment.merchant_source)}
                          disabled={detecting}
                          className="text-xs bg-red-200 hover:bg-red-300 text-red-800 px-2 py-1 rounded"
                        >
                          🗑️
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              ))}

              {/* Investments */}
              {recurringPayments.investments?.map((payment) => (
                <div key={payment.pattern_id} className="border-2 border-green-200 rounded-xl p-3 bg-green-50">
                  {editingPayment === payment.pattern_id ? (
                    <div className="space-y-2">
                      <input
                        type="text"
                        value={editValues.userLabel}
                        onChange={(e) => setEditValues({...editValues, userLabel: e.target.value})}
                        className="w-full px-2 py-1 border rounded text-sm"
                        placeholder="Label"
                      />
                      <input
                        type="number"
                        value={editValues.emiAmount}
                        onChange={(e) => setEditValues({...editValues, emiAmount: e.target.value})}
                        className="w-full px-2 py-1 border rounded text-sm"
                        placeholder="Amount"
                      />
                      <div className="flex gap-2">
                        <button
                          onClick={() => handleSaveEdit(payment.pattern_id)}
                          className="flex-1 bg-green-600 text-white py-1 px-2 rounded text-xs font-medium"
                        >
                          ✓ Save
                        </button>
                        <button
                          onClick={handleCancelEdit}
                          className="flex-1 bg-gray-200 text-gray-700 py-1 px-2 rounded text-xs font-medium"
                        >
                          ✕ Cancel
                        </button>
                      </div>
                    </div>
                  ) : (
                    <div className="flex items-center justify-between">
                      <div className="flex-1">
                        <div className="font-semibold text-green-900">
                          {payment.user_label || payment.merchant_source}
                        </div>
                        <div className="text-xs text-green-600">
                          {formatCurrency(payment.emi_amount)}/mo • 📈 Investment
                        </div>
                      </div>
                      <div className="flex gap-2">
                        <button
                          onClick={() => handleStartEdit(payment)}
                          disabled={detecting}
                          className="text-xs bg-green-200 hover:bg-green-300 text-green-800 px-2 py-1 rounded"
                        >
                          ✏️
                        </button>
                        <button
                          onClick={() => handleDeletePayment(payment.pattern_id, payment.merchant_source)}
                          disabled={detecting}
                          className="text-xs bg-red-200 hover:bg-red-300 text-red-800 px-2 py-1 rounded"
                        >
                          🗑️
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              ))}

              {/* Government Schemes */}
              {recurringPayments.government_schemes?.map((payment) => (
                <div key={payment.pattern_id} className="border-2 border-amber-200 rounded-xl p-3 bg-amber-50">
                  {editingPayment === payment.pattern_id ? (
                    <div className="space-y-2">
                      <input
                        type="text"
                        value={editValues.userLabel}
                        onChange={(e) => setEditValues({...editValues, userLabel: e.target.value})}
                        className="w-full px-2 py-1 border rounded text-sm"
                        placeholder="Label"
                      />
                      <input
                        type="number"
                        value={editValues.emiAmount}
                        onChange={(e) => setEditValues({...editValues, emiAmount: e.target.value})}
                        className="w-full px-2 py-1 border rounded text-sm"
                        placeholder="Amount"
                      />
                      <div className="flex gap-2">
                        <button
                          onClick={() => handleSaveEdit(payment.pattern_id)}
                          className="flex-1 bg-green-600 text-white py-1 px-2 rounded text-xs font-medium"
                        >
                          ✓ Save
                        </button>
                        <button
                          onClick={handleCancelEdit}
                          className="flex-1 bg-gray-200 text-gray-700 py-1 px-2 rounded text-xs font-medium"
                        >
                          ✕ Cancel
                        </button>
                      </div>
                    </div>
                  ) : (
                    <div className="flex items-center justify-between">
                      <div className="flex-1">
                        <div className="font-semibold text-amber-900">
                          {payment.user_label || payment.merchant_source}
                        </div>
                        <div className="text-xs text-amber-600">
                          {formatCurrency(payment.emi_amount)}/mo • 🏛️ Govt Scheme
                        </div>
                      </div>
                      <div className="flex gap-2">
                        <button
                          onClick={() => handleStartEdit(payment)}
                          disabled={detecting}
                          className="text-xs bg-amber-200 hover:bg-amber-300 text-amber-800 px-2 py-1 rounded"
                        >
                          ✏️
                        </button>
                        <button
                          onClick={() => handleDeletePayment(payment.pattern_id, payment.merchant_source)}
                          disabled={detecting}
                          className="text-xs bg-red-200 hover:bg-red-300 text-red-800 px-2 py-1 rounded"
                        >
                          🗑️
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              ))}
            </div>

            <div className="mt-4 text-xs text-gray-500 bg-gray-50 rounded-lg p-2">
              💡 Click Edit (✏️) to modify details or Delete (🗑️) to remove a payment
            </div>
          </div>
        )}

        {showSetup && detectedPatterns && (
          <div className="mb-6 bg-white border-2 border-orange-200 rounded-2xl p-5">
            <h3 className="text-lg font-bold text-gray-900 mb-3">Select Recurring Payments to Track</h3>
            <p className="text-sm text-gray-600 mb-4">
              Found {detectedPatterns.emis?.length || 0} recurring payments. Select the ones you want to track.
            </p>

            <div className="space-y-2 max-h-96 overflow-y-auto mb-4">
              {detectedPatterns.emis?.map((emi) => (
                <div
                  key={emi.pattern_id}
                  onClick={() => handleTogglePattern(emi.pattern_id)}
                  className={`border-2 rounded-xl p-3 cursor-pointer transition-all ${
                    selectedPatterns.includes(emi.pattern_id)
                      ? 'border-orange-400 bg-orange-50'
                      : 'border-gray-200 hover:border-orange-200'
                  }`}
                >
                  <div className="flex items-start gap-3">
                    <input
                      type="checkbox"
                      checked={selectedPatterns.includes(emi.pattern_id)}
                      onChange={() => {}}
                      className="mt-1 w-4 h-4"
                    />
                    <div className="flex-1">
                      <div className="flex items-center justify-between mb-1">
                        <span className="font-semibold text-gray-900">{emi.merchant_source}</span>
                        <span className="text-lg font-bold text-orange-600">{formatCurrency(emi.emi_amount)}</span>
                      </div>
                      {emi.category && (
                        <div className="mb-1">{getCategoryBadge(emi.category, emi.subcategory)}</div>
                      )}
                      <div className="text-xs text-gray-500">{emi.occurrence_count} payments</div>
                    </div>
                  </div>
                </div>
              ))}
            </div>

            <div className="flex gap-2">
              <button
                onClick={() => setShowSetup(false)}
                className="flex-1 bg-gray-100 text-gray-700 font-semibold py-3 rounded-xl hover:bg-gray-200"
              >
                Cancel
              </button>
              <button
                onClick={handleSaveConfiguration}
                disabled={selectedPatterns.length === 0 || detecting}
                className="flex-1 bg-gradient-to-r from-orange-500 to-orange-600 text-white font-semibold py-3 rounded-xl hover:from-orange-600 hover:to-orange-700 disabled:opacity-50"
              >
                {detecting ? 'Saving...' : `Save ${selectedPatterns.length} Payments`}
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Optimizers Grid */}
      <div className="max-w-lg mx-auto px-4">
        <div className="space-y-4">
          {optimizers.map((optimizer) => (
            <div
              key={optimizer.id}
              onClick={() => handleOptimizerClick(optimizer)}
              className={`relative bg-white rounded-2xl p-5 border-2 transition-all ${
                optimizer.status === 'active'
                  ? 'border-gray-200 hover:border-purple-300 hover:shadow-lg cursor-pointer active:scale-[0.98]'
                  : 'border-gray-100 opacity-60 cursor-not-allowed'
              }`}
            >
              {/* Coming Soon Badge */}
              {optimizer.status === 'coming_soon' && (
                <div className="absolute top-3 right-3 bg-gradient-to-r from-gray-400 to-gray-500 text-white text-xs font-semibold px-3 py-1 rounded-full">
                  Coming Soon
                </div>
              )}

              <div className="flex items-start gap-4">
                {/* Icon */}
                <div className={`w-14 h-14 bg-gradient-to-br ${optimizer.gradient} rounded-2xl flex items-center justify-center text-2xl shadow-lg flex-shrink-0`}>
                  {optimizer.icon}
                </div>

                {/* Content */}
                <div className="flex-1 min-w-0">
                  <h3 className="text-lg font-bold text-gray-900 mb-1">
                    {optimizer.title}
                  </h3>
                  <p className="text-sm text-gray-600 mb-3 line-clamp-2">
                    {optimizer.description}
                  </p>

                  {/* Benefits */}
                  <div className="flex flex-wrap gap-2">
                    {optimizer.benefits.map((benefit, idx) => (
                      <div
                        key={idx}
                        className="inline-flex items-center gap-1 px-2 py-1 bg-gray-100 rounded-lg text-xs font-medium text-gray-700"
                      >
                        <span className="text-green-500">✓</span>
                        {benefit}
                      </div>
                    ))}
                  </div>
                </div>

                {/* Arrow */}
                {optimizer.status === 'active' && (
                  <svg className="w-5 h-5 text-gray-400 flex-shrink-0 mt-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                  </svg>
                )}
              </div>
            </div>
          ))}
        </div>

        {/* Bottom Info */}
        <div className="mt-6 p-4 bg-blue-50 border border-blue-200 rounded-xl">
          <div className="flex items-start gap-3">
            <span className="text-2xl">💡</span>
            <div>
              <p className="text-sm font-medium text-blue-900 mb-1">More tools coming soon!</p>
              <p className="text-xs text-blue-700">
                We're constantly adding new optimization tools to help you save more and grow your wealth faster.
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
