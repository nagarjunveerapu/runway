// src/components/Modern/ModernAssetsLiabilities.jsx
import React, { useState, useEffect } from 'react';
import { getAllRecurringPayments } from '../../api/services/recurringPayments';

/**
 * ModernAssetsLiabilities - Unified view of assets and liabilities
 * Handles the real-world scenario:
 * - Home EMI → Creates LIABILITY (outstanding loan) + ASSET (property value)
 * - Personal Loan → Pure liability
 * - SBI Pension Fund → Asset
 * - Auto-detect and suggest mappings from EMIs
 */

const ASSET_TYPES = [
  { id: 'flat', label: 'Flat/House', icon: '🏠', color: 'from-blue-500 to-cyan-500', emi_linkable: true },
  { id: 'car', label: 'Car/Vehicle', icon: '🚗', color: 'from-purple-500 to-indigo-500', emi_linkable: true },
  { id: 'gold', label: 'Gold', icon: '✨', color: 'from-yellow-500 to-orange-500', emi_linkable: false },
  { id: 'stocks', label: 'Stocks', icon: '📈', color: 'from-green-500 to-emerald-500', emi_linkable: false },
  { id: 'crypto', label: 'Crypto', icon: '₿', color: 'from-orange-500 to-red-500', emi_linkable: false },
  { id: 'fd', label: 'Fixed Deposit', icon: '🏦', color: 'from-indigo-500 to-purple-500', emi_linkable: false },
  { id: 'pension', label: 'Pension Fund', icon: '👴', color: 'from-teal-500 to-cyan-500', emi_linkable: false },
  { id: 'other', label: 'Other Asset', icon: '💎', color: 'from-gray-500 to-slate-600', emi_linkable: false }
];

const LIABILITY_TYPES = [
  { id: 'home_loan', label: 'Home Loan', icon: '🏠', color: 'from-blue-500 to-cyan-500' },
  { id: 'personal_loan', label: 'Personal Loan', icon: '💳', color: 'from-red-500 to-pink-500' },
  { id: 'car_loan', label: 'Car Loan', icon: '🚗', color: 'from-purple-500 to-indigo-500' },
  { id: 'credit_card', label: 'Credit Card', icon: '💳', color: 'from-orange-500 to-amber-500' },
  { id: 'other', label: 'Other Debt', icon: '💸', color: 'from-gray-500 to-slate-600' }
];

export default function ModernAssetsLiabilities({ onNavigate }) {
  const [assets, setAssets] = useState([]);
  const [liabilities, setLiabilities] = useState([]);
  const [detectedEMIs, setDetectedEMIs] = useState([]);
  const [loadingEMIs, setLoadingEMIs] = useState(true);
  const [showAddModal, setShowAddModal] = useState(false);
  const [modalType, setModalType] = useState(null); // 'asset' or 'liability'
  const [selectedCategory, setSelectedCategory] = useState(null);
  const [formData, setFormData] = useState({});
  const [typeSelectorLinkedEMI, setTypeSelectorLinkedEMI] = useState(null);
  // Single-page layout (no tabs)

  // Load EMIs and data
  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    await Promise.all([
      loadEMIs(),
      loadAssets(),
      loadLiabilities()
    ]);
  };

  const loadEMIs = async () => {
    try {
      setLoadingEMIs(true);
      const { loans } = await getAllRecurringPayments();
      
      const emisRaw = loans.map(loan => ({
        name: loan.user_label || loan.merchant_source,
        amount: loan.emi_amount,
        count: loan.occurrence_count,
        category: loan.category,
        subcategory: loan.subcategory,
        lastDate: loan.last_detected_date,
        merchant_source: loan.merchant_source,
        pattern_id: loan.pattern_id
      }));

      // Deduplicate EMIs by stable key (pattern_id if present, else normalized name+amount)
      const normalize = (s) => (s || '').toLowerCase().replace(/\s+/g, '');
      const uniqueMap = new Map();
      for (const e of emisRaw) {
        const key = e.pattern_id || `${normalize(e.name)}:${Math.round(Number(e.amount) || 0)}`;
        if (!uniqueMap.has(key)) uniqueMap.set(key, e);
      }

      const emis = Array.from(uniqueMap.values());

      setDetectedEMIs(emis);
    } catch (error) {
      console.error('Error loading EMIs:', error);
      setDetectedEMIs([]);
    } finally {
      setLoadingEMIs(false);
    }
  };

  const loadAssets = async () => {
    try {
      const response = await fetch('http://localhost:8000/api/v1/assets/', {
        headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
      });
      if (response.ok) {
        setAssets(await response.json());
      }
    } catch (error) {
      console.error('Error loading assets:', error);
    }
  };

  const loadLiabilities = async () => {
    try {
      const response = await fetch('http://localhost:8000/api/v1/liabilities/', {
        headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
      });
      if (response.ok) {
        setLiabilities(await response.json());
      }
    } catch (error) {
      console.error('Error loading liabilities:', error);
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

  // Calculate totals
  const totalAssets = assets.reduce((sum, a) => sum + (a.current_value || a.purchase_price || 0), 0);
  const totalLiabilities = liabilities.reduce((sum, l) => sum + (l.outstanding_balance || l.principal_amount || 0), 0);
  const trueNetWorth = totalAssets - totalLiabilities;

  const openTypeSelector = (type, linkedEMI = null) => {
    setModalType(type);
    setSelectedCategory(null);
    setTypeSelectorLinkedEMI(linkedEMI);
    setShowAddModal(true);
  };

  const openAddModal = (type, category, linkedEMI = null) => {
    setModalType(type);
    setSelectedCategory(category);
    // Presets by type
    const presets = { interestRate: '', rateType: 'fixed', rateResetFrequency: '', originalTenure: '', moratoriumMonths: '', processingFee: '', prepaymentPenaltyPct: '' };
    if (type === 'liability') {
      switch (category.id) {
        case 'home_loan':
          presets.rateType = 'floating';
          presets.rateResetFrequency = '6';
          presets.originalTenure = '240';
          presets.prepaymentPenaltyPct = '2';
          break;
        case 'car_loan':
          presets.rateType = 'fixed';
          presets.originalTenure = '60';
          break;
        case 'personal_loan':
          presets.rateType = 'fixed';
          presets.originalTenure = '36';
          break;
        default:
          break;
      }
    }

    const inferredStartDate = linkedEMI?.lastDate ? linkedEMI.lastDate : '';

    setFormData({
      name: linkedEMI ? linkedEMI.name.replace(/loan|emi/gi, '').trim() : '',
      value: '',
      outstandingBalance: linkedEMI ? linkedEMI.amount * 60 : '',
      emiAmount: linkedEMI ? linkedEMI.amount : '',
      lenderName: linkedEMI ? linkedEMI.merchant_source : '',
      interestRate: presets.interestRate,
      rateType: presets.rateType,
      rateResetFrequency: presets.rateResetFrequency,
      startDate: inferredStartDate,
      originalTenure: presets.originalTenure,
      moratoriumMonths: presets.moratoriumMonths,
      processingFee: presets.processingFee,
      prepaymentPenaltyPct: presets.prepaymentPenaltyPct,
      linkedEMI
    });
    setShowAddModal(true);
  };

  const handleSave = async () => {
    if (!formData.name || (modalType === 'asset' && !formData.value) || 
        (modalType === 'liability' && !formData.outstandingBalance)) {
      alert('Please fill all required fields');
      return;
    }

    try {
      if (modalType === 'asset') {
        // Create asset
        await fetch('http://localhost:8000/api/v1/assets/', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${localStorage.getItem('token')}`
          },
          body: JSON.stringify({
            name: formData.name,
            asset_type: selectedCategory.id,
            purchase_price: Number(formData.value),
            purchase_date: new Date().toISOString().slice(0, 10),
            quantity: 1,
            notes: formData.linkedEMI ? `mapped_from_emi:${formData.linkedEMI.pattern_id}:${formData.linkedEMI.name}` : undefined
          })
        });
      } else {
        // Create liability
        await fetch('http://localhost:8000/api/v1/liabilities/', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${localStorage.getItem('token')}`
          },
          body: JSON.stringify({
            name: formData.name,
            liability_type: selectedCategory.id,
            outstanding_balance: Number(formData.outstandingBalance),
            emi_amount: formData.emiAmount ? Number(formData.emiAmount) : undefined,
            interest_rate: formData.interestRate ? Number(formData.interestRate) : undefined,
            rate_type: formData.rateType || undefined,
            rate_reset_frequency_months: formData.rateResetFrequency ? Number(formData.rateResetFrequency) : undefined,
            start_date: formData.startDate || undefined,
            original_tenure_months: formData.originalTenure ? Number(formData.originalTenure) : undefined,
            moratorium_months: formData.moratoriumMonths ? Number(formData.moratoriumMonths) : undefined,
            processing_fee: formData.processingFee ? Number(formData.processingFee) : undefined,
            prepayment_penalty_pct: formData.prepaymentPenaltyPct ? Number(formData.prepaymentPenaltyPct) : undefined,
            lender_name: formData.lenderName,
            recurring_pattern_id: formData.linkedEMI?.pattern_id,
            principal_amount: Number(formData.outstandingBalance)
          })
        });
      }

      await loadData();
      setShowAddModal(false);
    } catch (err) {
      alert('Error: ' + (err?.message || 'unknown'));
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-pink-50 to-red-50 pb-24">
      {/* Header with Tabs */}
      <div className="bg-white/80 backdrop-blur-md sticky top-0 z-20 border-b border-gray-100">
        <div className="max-w-lg mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div>
              <div className="text-lg font-bold text-gray-900">Assets & Liabilities</div>
              <div className="text-xs text-gray-500">Your complete financial picture</div>
            </div>
            <div className="flex gap-2">
              <button
                onClick={() => openTypeSelector('asset')}
                className="px-3 py-2 rounded-xl bg-gradient-to-r from-blue-500 to-cyan-500 text-white text-xs font-semibold hover:shadow-md active:scale-95"
              >
                + Asset
              </button>
              <button
                onClick={() => openTypeSelector('liability')}
                className="px-3 py-2 rounded-xl bg-gradient-to-r from-red-500 to-pink-500 text-white text-xs font-semibold hover:shadow-md active:scale-95"
              >
                + Liability
              </button>
            </div>
        </div>
          <div className="mt-3 grid grid-cols-3 gap-2">
            <div className="rounded-xl bg-blue-50 border border-blue-100 p-3">
              <div className="text-[10px] text-gray-500">Assets</div>
              <div className="text-sm font-bold text-blue-600">{assets.length}</div>
            </div>
            <div className="rounded-xl bg-red-50 border border-red-100 p-3">
              <div className="text-[10px] text-gray-500">Liabilities</div>
              <div className="text-sm font-bold text-red-600">{liabilities.length}</div>
            </div>
            <div className={`rounded-xl p-3 border ${trueNetWorth >= 0 ? 'bg-green-50 border-green-100' : 'bg-red-50 border-red-100'}`}>
              <div className="text-[10px] text-gray-500">True Net Worth</div>
              <div className={`text-sm font-bold ${trueNetWorth >= 0 ? 'text-green-700' : 'text-red-700'}`}>{formatCurrency(trueNetWorth)}</div>
            </div>
          </div>
        </div>
      </div>

      <div className="max-w-lg mx-auto px-4 py-6 space-y-5">
        {/* Summary Card */}
        <div className={`bg-gradient-to-br ${trueNetWorth >= 0 ? 'from-green-50 to-emerald-50 border-green-200' : 'from-red-50 to-pink-50 border-red-200'} rounded-2xl p-5 border-2 shadow-sm`}>
          <div className="text-xs text-gray-500 mb-1">True Net Worth</div>
          <div className={`text-4xl font-bold ${trueNetWorth >= 0 ? 'text-green-600' : 'text-red-600'}`}>
            {formatCurrency(trueNetWorth)}
          </div>
          <div className="text-xs text-gray-600 mt-2 flex gap-4">
            <span>Assets: {formatCurrency(totalAssets)}</span>
            <span>•</span>
            <span>Liabilities: {formatCurrency(totalLiabilities)}</span>
          </div>
        </div>
            {/* Quick Stats */}
            <div className="grid grid-cols-2 gap-4">
              <div className="bg-white rounded-2xl p-4 shadow-sm border border-blue-100">
                <div className="text-xs text-gray-500 mb-1">Assets</div>
                <div className="text-2xl font-bold text-blue-600">{assets.length}</div>
                <div className="text-xs text-gray-400 mt-1">{formatCurrency(totalAssets)}</div>
              </div>
              <div className="bg-white rounded-2xl p-4 shadow-sm border border-red-100">
                <div className="text-xs text-gray-500 mb-1">Liabilities</div>
                <div className="text-2xl font-bold text-red-600">{liabilities.length}</div>
                <div className="text-xs text-gray-400 mt-1">{formatCurrency(totalLiabilities)}</div>
              </div>
        </div>

        {/* EMI Suggestions */}
        {!loadingEMIs && detectedEMIs.length > 0 && (
              <div className="bg-gradient-to-br from-orange-50 to-amber-50 rounded-2xl p-5 border border-orange-200 shadow-sm">
                <div className="flex items-center gap-2 mb-3">
                  <span className="text-2xl">💡</span>
                  <div className="flex-1">
                    <h3 className="font-semibold text-orange-900">Map Your EMIs</h3>
                    <p className="text-xs text-orange-700 mt-0.5">
                      Convert detected EMIs into assets and liabilities
                    </p>
                  </div>
                </div>
                <div className="space-y-2">
                  {detectedEMIs.map((emi, idx) => {
                    const normalize = (s) => (s || '').toLowerCase().replace(/\s+/g, '');
                    const emiKey = normalize(emi.name);
                    const assetMapped = assets.some(a => {
                      const notes = a.notes || '';
                      const nameMatch = normalize(a.name).includes(emiKey);
                      const notesHasId = emi.pattern_id && notes.includes(emi.pattern_id);
                      const notesHasName = emi.name && notes.includes(emi.name);
                      return nameMatch || notesHasId || notesHasName;
                    });
                    const liabilityMapped = liabilities.some(l => l.recurring_pattern_id === emi.pattern_id);
                    const backendMappedAs = emi.mapped_as; // 'asset' | 'liability' if provided by API
                    const isMapped = !!backendMappedAs || assetMapped || liabilityMapped;
                    
                    return (
                      <div key={idx} className="bg-white rounded-xl p-3">
                        <div className="flex items-center justify-between mb-2">
                          <div className="font-medium text-sm text-gray-900">{emi.name}</div>
                          <div className="text-xs font-semibold text-orange-600">
                            ₹{Number(emi.amount).toLocaleString('en-IN')}/month
                          </div>
                        </div>
                        <div className="flex gap-2">
                          {!isMapped && (
                            <>
                              <button
                                onClick={() => openTypeSelector('asset', emi)}
                                className="flex-1 px-3 py-2 rounded-lg bg-gradient-to-r from-blue-500 to-cyan-500 text-white text-xs font-medium hover:shadow-md active:scale-95 transition-all"
                              >
                                + Asset
                              </button>
                              <button
                                onClick={() => openTypeSelector('liability', emi)}
                                className="flex-1 px-3 py-2 rounded-lg bg-gradient-to-r from-red-500 to-pink-500 text-white text-xs font-medium hover:shadow-md active:scale-95 transition-all"
                              >
                                + Liability
                              </button>
                            </>
                          )}
                          {isMapped && (
                            <div className="flex-1 flex items-center justify-center text-xs text-green-600">
                              ✓ Mapped
                            </div>
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>
        </div>
        )}

        {/* ASSETS SECTION */}
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-semibold text-gray-700">Your Assets</h3>
            <button
              onClick={() => openTypeSelector('asset')}
              className="px-4 py-2 rounded-xl bg-gradient-to-r from-blue-500 to-cyan-500 text-white text-xs font-semibold hover:shadow-md active:scale-95"
            >
              + Add Asset
            </button>
          </div>
          {assets.map(asset => (
            <div key={asset.asset_id} className="bg-white rounded-xl p-4 shadow-sm border border-blue-100">
              <div className="font-semibold text-gray-900">{asset.name}</div>
              <div className="text-sm text-blue-600 font-medium mt-1">
                {formatCurrency(asset.current_value || asset.purchase_price)}
              </div>
            </div>
          ))}
        </div>

        {/* LIABILITIES SECTION */}
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-semibold text-gray-700">Your Liabilities</h3>
            <button
              onClick={() => openTypeSelector('liability')}
              className="px-4 py-2 rounded-xl bg-gradient-to-r from-red-500 to-pink-500 text-white text-xs font-semibold hover:shadow-md active:scale-95"
            >
              + Add Liability
            </button>
          </div>
          {liabilities.map(liability => (
            <div key={liability.liability_id} className="bg-white rounded-xl p-4 shadow-sm border border-red-100">
              <div className="font-semibold text-gray-900">{liability.name}</div>
              <div className="text-sm text-red-600 font-medium mt-1">
                {formatCurrency(liability.outstanding_balance || liability.principal_amount)}
              </div>
              {liability.emi_amount && (
                <div className="text-xs text-gray-500 mt-1">EMI: {formatCurrency(liability.emi_amount)}</div>
              )}
            </div>
          ))}
        </div>

        {/* Type Selection Modal (Step 1) */}
        {showAddModal && !selectedCategory && modalType && (
          <div className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4">
            <div className="bg-white rounded-3xl w-full max-w-md shadow-2xl max-h-[90vh] overflow-y-auto">
              <div className={`bg-gradient-to-br ${modalType === 'liability' ? 'from-red-500 to-pink-500' : 'from-blue-500 to-cyan-500'} text-white p-6 rounded-t-3xl`}>
                <div className="flex items-center justify-between">
                  <div className="text-xl font-bold">Choose {modalType === 'liability' ? 'Liability' : 'Asset'} Type</div>
                  <button onClick={() => setShowAddModal(false)} className="p-2 rounded-lg hover:bg-white/10">✕</button>
                </div>
              </div>
              <div className="p-6">
                <div className="grid grid-cols-2 gap-3">
                  {(modalType === 'liability' ? LIABILITY_TYPES : ASSET_TYPES).map(type => (
                    <button
                      key={type.id}
                      onClick={() => openAddModal(modalType, type, typeSelectorLinkedEMI)}
                      className={`bg-gradient-to-br ${type.color} rounded-2xl p-4 text-left text-white hover:shadow-lg active:scale-95 transition-all`}
                    >
                      <div className="text-3xl mb-2">{type.icon}</div>
                      <div className="text-xs font-semibold">{type.label}</div>
                    </button>
                  ))}
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Add Modal (Step 2: Details) */}
        {showAddModal && selectedCategory && (
          <div className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4">
            <div className="bg-white rounded-3xl w-full max-w-md shadow-2xl max-h-[90vh] overflow-y-auto">
              <div className={`bg-gradient-to-br ${selectedCategory.color} text-white p-6 rounded-t-3xl`}>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <span className="text-3xl">{selectedCategory.icon}</span>
                    <div>
                      <h2 className="text-xl font-bold">Add {selectedCategory.label}</h2>
                      <p className="text-xs text-white/80">{modalType === 'asset' ? 'Asset' : 'Liability'}</p>
                    </div>
                  </div>
                  <button onClick={() => setShowAddModal(false)} className="p-2 rounded-lg hover:bg-white/10">
                    ✕
                  </button>
                </div>
              </div>

              <div className="p-6 space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Name</label>
                  <input
                    type="text"
                    value={formData.name}
                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                    className="w-full px-4 py-3 rounded-xl border border-gray-200 focus:outline-none focus:ring-2 focus:ring-red-500"
                  />
                </div>

                {modalType === 'asset' ? (
                  <>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">Asset Value</label>
                      <input
                        type="number"
                        value={formData.value}
                        onChange={(e) => setFormData({ ...formData, value: e.target.value })}
                        className="w-full px-4 py-3 rounded-xl border border-gray-200 focus:outline-none focus:ring-2 focus:ring-blue-500"
                        placeholder="Current market value"
                      />
                    </div>
                    {formData.linkedEMI && (
                      <div className="text-xs text-gray-500 bg-blue-50 p-3 rounded-lg">
                        💡 Linked to: {formData.linkedEMI.name} (₹{Number(formData.linkedEMI.amount).toLocaleString('en-IN')}/month)
                      </div>
                    )}
                  </>
                ) : (
                  <>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">Outstanding Balance</label>
                      <input
                        type="number"
                        value={formData.outstandingBalance}
                        onChange={(e) => setFormData({ ...formData, outstandingBalance: e.target.value })}
                        className="w-full px-4 py-3 rounded-xl border border-gray-200 focus:outline-none focus:ring-2 focus:ring-red-500"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">Monthly EMI</label>
                      <input
                        type="number"
                        value={formData.emiAmount}
                        onChange={(e) => setFormData({ ...formData, emiAmount: e.target.value })}
                        className="w-full px-4 py-3 rounded-xl border border-gray-200 focus:outline-none focus:ring-2 focus:ring-red-500"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">Interest Rate %</label>
                      <input
                        type="number"
                        value={formData.interestRate}
                        onChange={(e) => setFormData({ ...formData, interestRate: e.target.value })}
                        className="w-full px-4 py-3 rounded-xl border border-gray-200 focus:outline-none focus:ring-2 focus:ring-red-500"
                        placeholder="e.g., 9.0"
                      />
                    </div>
                    <div className="grid grid-cols-2 gap-3">
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">Rate Type</label>
                        <select
                          value={formData.rateType}
                          onChange={(e) => setFormData({ ...formData, rateType: e.target.value })}
                          className="w-full px-4 py-3 rounded-xl border border-gray-200 focus:outline-none focus:ring-2 focus:ring-red-500"
                        >
                          <option value="fixed">Fixed</option>
                          <option value="floating">Floating</option>
                        </select>
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">Rate Reset Freq (Months)</label>
                        <input
                          type="number"
                          value={formData.rateResetFrequency}
                          onChange={(e) => setFormData({ ...formData, rateResetFrequency: e.target.value })}
                          className="w-full px-4 py-3 rounded-xl border border-gray-200 focus:outline-none focus:ring-2 focus:ring-red-500"
                          placeholder="e.g., 6"
                        />
                      </div>
                    </div>
                    <div className="grid grid-cols-2 gap-3">
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">Start Date</label>
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
                    <div className="grid grid-cols-2 gap-3">
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">Moratorium (Months)</label>
                        <input
                          type="number"
                          value={formData.moratoriumMonths}
                          onChange={(e) => setFormData({ ...formData, moratoriumMonths: e.target.value })}
                          className="w-full px-4 py-3 rounded-xl border border-gray-200 focus:outline-none focus:ring-2 focus:ring-red-500"
                          placeholder="e.g., 3"
                        />
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">Processing Fee</label>
                        <input
                          type="number"
                          value={formData.processingFee}
                          onChange={(e) => setFormData({ ...formData, processingFee: e.target.value })}
                          className="w-full px-4 py-3 rounded-xl border border-gray-200 focus:outline-none focus:ring-2 focus:ring-red-500"
                          placeholder="e.g., 2500"
                        />
                      </div>
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">Prepayment Penalty %</label>
                      <input
                        type="number"
                        value={formData.prepaymentPenaltyPct}
                        onChange={(e) => setFormData({ ...formData, prepaymentPenaltyPct: e.target.value })}
                        className="w-full px-4 py-3 rounded-xl border border-gray-200 focus:outline-none focus:ring-2 focus:ring-red-500"
                        placeholder="e.g., 2"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">Lender</label>
                      <input
                        type="text"
                        value={formData.lenderName}
                        onChange={(e) => setFormData({ ...formData, lenderName: e.target.value })}
                        className="w-full px-4 py-3 rounded-xl border border-gray-200 focus:outline-none focus:ring-2 focus:ring-red-500"
                      />
                    </div>
                  </>
                )}

                <div className="flex gap-3 mt-6">
                  <button
                    onClick={() => setShowAddModal(false)}
                    className="flex-1 py-3 rounded-xl bg-gray-200 text-gray-700 font-semibold hover:bg-gray-300"
                  >
                    Cancel
                  </button>
                  <button
                    onClick={handleSave}
                    className={`flex-1 py-3 rounded-xl bg-gradient-to-r ${selectedCategory.color} text-white font-semibold hover:shadow-lg`}
                  >
                    Add
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

