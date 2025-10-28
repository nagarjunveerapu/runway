// src/components/Modern/ModernLiabilities.jsx
import React, { useState, useEffect } from 'react';
import { getAllRecurringPayments } from '../../api/services/recurringPayments';

/**
 * ModernLiabilities - Track loans and debts
 * Auto-detect EMIs and convert to liabilities
 * Uses the Centralized Recurring Payments System
 */

const LIABILITY_TYPES = [
  { id: 'personal_loan', label: 'Personal Loan', icon: '💳', color: 'from-red-500 to-pink-500' },
  { id: 'home_loan', label: 'Home Loan', icon: '🏠', color: 'from-blue-500 to-cyan-500' },
  { id: 'car_loan', label: 'Car Loan', icon: '🚗', color: 'from-purple-500 to-indigo-500' },
  { id: 'credit_card', label: 'Credit Card', icon: '💳', color: 'from-orange-500 to-amber-500' },
  { id: 'education_loan', label: 'Education Loan', icon: '📚', color: 'from-green-500 to-emerald-500' },
  { id: 'other', label: 'Other Debt', icon: '💸', color: 'from-gray-500 to-slate-600' }
];

export default function ModernLiabilities({ onNavigate }) {
  const [liabilities, setLiabilities] = useState([]);
  const [showAddModal, setShowAddModal] = useState(false);
  const [selectedType, setSelectedType] = useState(null);
  const [formData, setFormData] = useState({
    name: '',
    principalAmount: '',
    outstandingBalance: '',
    emiAmount: '',
    interestRate: '',
    startDate: '',
    originalTenure: '',
    lenderName: '',
    linkedEMI: null
  });
  const [detectedEMIs, setDetectedEMIs] = useState([]);
  const [loadingEMIs, setLoadingEMIs] = useState(true);
  const [mappedEMIs, setMappedEMIs] = useState(new Set());

  // Load EMIs from Centralized Recurring Payments System
  useEffect(() => {
    const loadEMIs = async () => {
      try {
        setLoadingEMIs(true);
        const { loans } = await getAllRecurringPayments();
        
        const emis = loans.map(loan => ({
          name: loan.user_label || loan.merchant_source,
          amount: loan.emi_amount,
          count: loan.occurrence_count,
          category: loan.category,
          subcategory: loan.subcategory,
          lastDate: loan.last_detected_date,
          merchant_source: loan.merchant_source,
          pattern_id: loan.pattern_id
        }));
        
        setDetectedEMIs(emis);
      } catch (error) {
        console.error('Error loading EMIs:', error);
        setDetectedEMIs([]);
      } finally {
        setLoadingEMIs(false);
      }
    };

    loadEMIs();
    loadLiabilities();
  }, []);

  const loadLiabilities = async () => {
    try {
      const response = await fetch('http://localhost:8000/api/v1/liabilities/', {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        }
      });
      if (response.ok) {
        const data = await response.json();
        setLiabilities(data);
        
        // Check which EMIs are mapped
        const mapped = new Set();
        data.forEach(liability => {
          if (liability.recurring_pattern_id) {
            mapped.add(liability.recurring_pattern_id);
          }
        });
        setMappedEMIs(mapped);
      }
    } catch (error) {
      console.error('Error loading liabilities:', error);
    }
  };

  const handleAddLiability = async () => {
    if (!selectedType || !formData.name || !formData.principalAmount || !formData.outstandingBalance) {
      alert('Please fill all required fields (Name, Original Loan Amount, Outstanding Balance)');
      return;
    }

    // Calculate remaining tenure if we have original tenure and start date
    let remainingTenure = undefined;
    if (formData.originalTenure && formData.startDate) {
      const startDate = new Date(formData.startDate);
      const today = new Date();
      const monthsElapsed = (today.getFullYear() - startDate.getFullYear()) * 12 + (today.getMonth() - startDate.getMonth());
      remainingTenure = Math.max(0, Number(formData.originalTenure) - monthsElapsed);
    }

    try {
      const response = await fetch('http://localhost:8000/api/v1/liabilities/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        },
        body: JSON.stringify({
          name: formData.name,
          liability_type: selectedType.id,
          principal_amount: Number(formData.principalAmount),
          outstanding_balance: Number(formData.outstandingBalance),
          emi_amount: Number(formData.emiAmount) || undefined,
          interest_rate: Number(formData.interestRate) || undefined,
          start_date: formData.startDate || undefined,
          original_tenure_months: Number(formData.originalTenure) || undefined,
          remaining_tenure_months: remainingTenure,
          lender_name: formData.lenderName || undefined,
          recurring_pattern_id: formData.linkedEMI?.pattern_id
        })
      });

      if (response.ok) {
        await loadLiabilities();
        setShowAddModal(false);
        setSelectedType(null);
        setFormData({
          name: '',
          principalAmount: '',
          outstandingBalance: '',
          emiAmount: '',
          interestRate: '',
          startDate: '',
          originalTenure: '',
          lenderName: '',
          linkedEMI: null
        });
      } else {
        const error = await response.json();
        alert('Error creating liability: ' + (error.detail || 'unknown'));
      }
    } catch (err) {
      alert('Error: ' + (err?.message || 'unknown'));
    }
  };

  const handleDeleteLiability = async (liabilityId) => {
    if (!window.confirm('Delete this liability?')) return;
    
    try {
      const response = await fetch(`http://localhost:8000/api/v1/liabilities/${liabilityId}`, {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        }
      });

      if (response.ok) {
        await loadLiabilities();
      } else {
        alert('Error deleting liability');
      }
    } catch (err) {
      alert('Error: ' + (err?.message || 'unknown'));
    }
  };

  const formatCurrency = (amount) => {
    if (!amount && amount !== 0) return '₹0';
    const numAmount = Number(amount);
    if (isNaN(numAmount)) return '₹0';
    if (numAmount >= 10000000) return `₹${(numAmount / 10000000).toFixed(2)}Cr`;
    if (numAmount >= 100000) return `₹${(numAmount / 100000).toFixed(2)}L`;
    if (numAmount >= 1000) return `₹${(numAmount / 1000).toFixed(1)}K`;
    return `₹${numAmount.toFixed(0)}`;
  };

  const openAddModal = (liabilityType, linkedEMI = null) => {
    setSelectedType(liabilityType);
    setFormData({
      name: linkedEMI ? linkedEMI.name.replace(/loan|emi/gi, '').trim() : '',
      outstandingBalance: '',
      emiAmount: linkedEMI ? linkedEMI.amount : '',
      interestRate: '',
      lenderName: linkedEMI ? linkedEMI.merchant_source : '',
      linkedEMI
    });
    setShowAddModal(true);
  };

  const totalLiabilities = liabilities.reduce((sum, l) => sum + (l.outstanding_balance || l.principal_amount || 0), 0);

  return (
    <div className="min-h-screen bg-gradient-to-br from-red-50 to-pink-50 pb-24">
      {/* Header */}
      <div className="bg-white/80 backdrop-blur-md sticky top-0 z-20 border-b border-gray-100">
        <div className="max-w-lg mx-auto px-4 py-4 flex items-center justify-between">
          <div>
            <div className="text-lg font-bold text-gray-900">Liabilities</div>
            <div className="text-xs text-gray-500">Track your debts and loans</div>
          </div>
          <button
            onClick={() => setShowAddModal(true)}
            className="w-10 h-10 rounded-full bg-gradient-to-br from-red-500 to-pink-500 flex items-center justify-center text-white hover:shadow-lg active:scale-95 transition-all"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
            </svg>
          </button>
        </div>
      </div>

      <div className="max-w-lg mx-auto px-4 py-6 space-y-4">
        {/* Total Liabilities */}
        <div className="bg-white rounded-2xl p-5 shadow-sm border border-red-200">
          <div className="text-xs text-gray-500 mb-1">Total Outstanding</div>
          <div className="text-3xl font-bold text-red-600">
            {formatCurrency(totalLiabilities)}
          </div>
          <div className="text-xs text-gray-500 mt-2">
            {liabilities.length} {liabilities.length === 1 ? 'liability' : 'liabilities'}
          </div>
        </div>

        {/* EMI Suggestions */}
        {loadingEMIs && (
          <div className="bg-white rounded-2xl p-5 border border-gray-200 mb-6 shadow-sm">
            <div className="flex items-center justify-center py-4">
              <div className="w-6 h-6 border-2 border-red-500 border-t-transparent rounded-full animate-spin"></div>
              <span className="ml-2 text-sm text-red-700">Loading EMIs...</span>
            </div>
          </div>
        )}
        {!loadingEMIs && detectedEMIs.length > 0 && (
          <div className="bg-gradient-to-br from-red-50 to-pink-50 rounded-2xl p-5 border border-red-200 mb-6 shadow-sm">
            <div className="flex items-center gap-2 mb-3">
              <span className="text-2xl">💡</span>
              <div>
                <h3 className="font-semibold text-red-900">Add Liabilities from EMIs</h3>
                <p className="text-xs text-red-700 mt-0.5">We detected {detectedEMIs.length} loan EMIs. Track them as liabilities!</p>
              </div>
            </div>
            <div className="space-y-2">
              {detectedEMIs.map((emi, idx) => {
                const isMapped = mappedEMIs.has(emi.pattern_id);
                const mappedLiability = liabilities.find(l => l.recurring_pattern_id === emi.pattern_id);
                
                return (
                  <div key={idx} className={`flex items-center justify-between rounded-xl p-3 ${isMapped ? 'bg-green-50 border border-green-200' : 'bg-white'}`}>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <div className="font-medium text-gray-900 text-sm truncate">{emi.name}</div>
                        {isMapped && (
                          <span className="text-xs bg-green-100 text-green-700 px-2 py-0.5 rounded-full">
                            ✓ Tracked
                          </span>
                        )}
                      </div>
                      <div className="text-xs text-gray-500 mt-0.5">
                        ₹{Number(emi.amount).toLocaleString('en-IN')} × {emi.count} payments
                        {emi.subcategory && <span className="ml-2 text-red-600">({emi.subcategory})</span>}
                        {isMapped && mappedLiability && (
                          <span className="ml-2 text-green-600">→ {mappedLiability.name}</span>
                        )}
                      </div>
                    </div>
                    {!isMapped && (
                      <button
                        onClick={() => {
                          let suggestedType = LIABILITY_TYPES.find(t => t.id === 'other');
                          const emiName = emi.name.toLowerCase();
                          const subcat = (emi.subcategory || '').toLowerCase();
                          
                          if (emiName.includes('home') || emiName.includes('house') || emiName.includes('flat') || emiName.includes('canfin') || subcat.includes('home')) {
                            suggestedType = LIABILITY_TYPES.find(t => t.id === 'home_loan');
                          } else if (emiName.includes('car') || emiName.includes('vehicle') || subcat.includes('car')) {
                            suggestedType = LIABILITY_TYPES.find(t => t.id === 'car_loan');
                          } else if (emiName.includes('personal')) {
                            suggestedType = LIABILITY_TYPES.find(t => t.id === 'personal_loan');
                          }
                          openAddModal(suggestedType, emi);
                        }}
                        className="ml-3 px-3 py-1.5 rounded-lg bg-gradient-to-r from-red-500 to-pink-500 text-white text-xs font-medium hover:shadow-md active:scale-95 transition-all whitespace-nowrap"
                      >
                        + Track Debt
                      </button>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* Liability Type Cards */}
        {!showAddModal && (
          <div className="grid grid-cols-2 gap-3 mb-6">
            {LIABILITY_TYPES.map(type => (
              <button
                key={type.id}
                onClick={() => openAddModal(type)}
                className={`bg-gradient-to-br ${type.color} rounded-2xl p-4 hover:shadow-lg active:scale-95 transition-all`}
              >
                <div className="text-3xl mb-2">{type.icon}</div>
                <div className="text-xs font-semibold text-white text-left">{type.label}</div>
              </button>
            ))}
          </div>
        )}

        {/* Existing Liabilities */}
        {liabilities.length > 0 && (
          <div className="space-y-3">
            <h3 className="text-sm font-semibold text-gray-600 uppercase tracking-wide">Your Liabilities</h3>
            {liabilities.map(liability => (
              <div key={liability.liability_id} className="bg-white rounded-xl p-4 shadow-sm border border-red-100">
                <div className="flex items-start justify-between">
                  <div className="flex-1 min-w-0">
                    <div className="font-semibold text-gray-900">{liability.name}</div>
                    <div className="text-sm text-gray-500 mt-1">
                      Outstanding: {formatCurrency(liability.outstanding_balance || liability.principal_amount || 0)}
                    </div>
                    {liability.emi_amount && (
                      <div className="text-xs text-gray-400 mt-1">EMI: {formatCurrency(liability.emi_amount)}</div>
                    )}
                    {liability.lender_name && (
                      <div className="text-xs text-gray-400 mt-1">Lender: {liability.lender_name}</div>
                    )}
                  </div>
                  <button
                    onClick={() => handleDeleteLiability(liability.liability_id)}
                    className="ml-2 p-2 rounded-lg hover:bg-red-50 text-red-500 active:scale-95 transition-all"
                  >
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                    </svg>
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Add Liability Modal */}
        {showAddModal && selectedType && (
          <div className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-end sm:items-center justify-center p-4">
            <div className="bg-white rounded-t-3xl sm:rounded-3xl w-full max-w-md shadow-2xl max-h-[90vh] overflow-y-auto">
              {/* Modal Header */}
              <div className={`bg-gradient-to-br ${selectedType.color} text-white p-6 rounded-t-3xl`}>
                <div className="flex items-center justify-between mb-4">
                  <div className="flex items-center gap-3">
                    <div className="w-12 h-12 rounded-xl bg-white/20 backdrop-blur-sm flex items-center justify-center text-2xl">
                      {selectedType.icon}
                    </div>
                    <div>
                      <h2 className="text-xl font-bold">Add {selectedType.label}</h2>
                      {formData.linkedEMI && (
                        <p className="text-xs text-white/80 mt-1">Linked to: {formData.linkedEMI.name}</p>
                      )}
                    </div>
                  </div>
                  <button
                    onClick={() => setShowAddModal(false)}
                    className="p-2 rounded-lg hover:bg-white/10 transition-colors"
                  >
                    <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                    </svg>
                  </button>
                </div>
              </div>

              {/* Form */}
              <div className="p-6 pt-0 space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Loan Name *</label>
                  <input
                    type="text"
                    value={formData.name}
                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                    className="w-full px-4 py-3 rounded-xl border border-gray-200 focus:outline-none focus:ring-2 focus:ring-red-500"
                    placeholder={`e.g., ${selectedType.label}`}
                    required
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Original Loan Amount *</label>
                  <input
                    type="number"
                    value={formData.principalAmount}
                    onChange={(e) => setFormData({ ...formData, principalAmount: e.target.value })}
                    className="w-full px-4 py-3 rounded-xl border border-gray-200 focus:outline-none focus:ring-2 focus:ring-red-500"
                    placeholder="e.g., 1000000 (10 lakhs)"
                    required
                  />
                  <p className="text-xs text-gray-500 mt-1">The full loan amount you borrowed initially</p>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Current Outstanding Balance *</label>
                  <input
                    type="number"
                    value={formData.outstandingBalance}
                    onChange={(e) => setFormData({ ...formData, outstandingBalance: e.target.value })}
                    className="w-full px-4 py-3 rounded-xl border border-gray-200 focus:outline-none focus:ring-2 focus:ring-red-500"
                    placeholder="e.g., 750000 (7.5 lakhs)"
                    required
                  />
                  <p className="text-xs text-gray-500 mt-1">How much you still owe today</p>
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Loan Start Date</label>
                    <input
                      type="date"
                      value={formData.startDate}
                      onChange={(e) => setFormData({ ...formData, startDate: e.target.value })}
                      className="w-full px-4 py-3 rounded-xl border border-gray-200 focus:outline-none focus:ring-2 focus:ring-red-500"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Tenure (Months)</label>
                    <input
                      type="number"
                      value={formData.originalTenure}
                      onChange={(e) => setFormData({ ...formData, originalTenure: e.target.value })}
                      className="w-full px-4 py-3 rounded-xl border border-gray-200 focus:outline-none focus:ring-2 focus:ring-red-500"
                      placeholder="e.g., 240"
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Monthly EMI (Optional)</label>
                  <input
                    type="number"
                    value={formData.emiAmount}
                    onChange={(e) => setFormData({ ...formData, emiAmount: e.target.value })}
                    className="w-full px-4 py-3 rounded-xl border border-gray-200 focus:outline-none focus:ring-2 focus:ring-red-500"
                    placeholder="e.g., 25000"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Interest Rate % (Optional)</label>
                  <input
                    type="number"
                    value={formData.interestRate}
                    onChange={(e) => setFormData({ ...formData, interestRate: e.target.value })}
                    className="w-full px-4 py-3 rounded-xl border border-gray-200 focus:outline-none focus:ring-2 focus:ring-red-500"
                    placeholder="e.g., 10.5"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Lender Name (Optional)</label>
                  <input
                    type="text"
                    value={formData.lenderName}
                    onChange={(e) => setFormData({ ...formData, lenderName: e.target.value })}
                    className="w-full px-4 py-3 rounded-xl border border-gray-200 focus:outline-none focus:ring-2 focus:ring-red-500"
                    placeholder="e.g., SBI, HDFC"
                  />
                </div>

                <div className="flex gap-3 mt-6">
                  <button
                    type="button"
                    onClick={() => setShowAddModal(false)}
                    className="flex-1 py-3 px-4 rounded-xl bg-gray-200 text-gray-700 font-semibold hover:bg-gray-300 active:scale-95 transition-all"
                  >
                    Cancel
                  </button>
                  <button
                    onClick={handleAddLiability}
                    className={`flex-1 py-3 px-4 rounded-xl bg-gradient-to-r ${selectedType.color} text-white font-semibold hover:shadow-lg active:scale-95 transition-all`}
                  >
                    Add {selectedType.label}
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

