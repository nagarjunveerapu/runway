// src/components/Modern/ModernAssets.jsx
import React, { useState, useMemo, useEffect } from 'react';
import { useApp } from '../../context/AppContext';
import { getAllRecurringPayments } from '../../api/services/recurringPayments';

/**
 * ModernAssets - Simple, futuristic asset management
 * Auto-detect EMIs and convert to assets (Flat, Car, etc.)
 * Uses the Centralized Recurring Payments System
 */

const ASSET_TYPES = [
  { id: 'flat', label: 'Flat/House', icon: '🏠', color: 'from-blue-500 to-cyan-500', canLinkEMI: true },
  { id: 'car', label: 'Car/Vehicle', icon: '🚗', color: 'from-purple-500 to-indigo-500', canLinkEMI: true },
  { id: 'gold', label: 'Gold', icon: '✨', color: 'from-yellow-500 to-orange-500', canLinkEMI: false },
  { id: 'stocks', label: 'Stocks', icon: '📈', color: 'from-green-500 to-emerald-500', canLinkEMI: false },
  { id: 'crypto', label: 'Crypto', icon: '₿', color: 'from-orange-500 to-red-500', canLinkEMI: false },
  { id: 'fd', label: 'Fixed Deposit', icon: '🏦', color: 'from-indigo-500 to-purple-500', canLinkEMI: false },
  { id: 'other', label: 'Other', icon: '💎', color: 'from-gray-500 to-slate-600', canLinkEMI: false }
];

export default function ModernAssets({ onNavigate }) {
  const { assets = [], addAsset, deleteAsset, updateAsset } = useApp();
  const [showAddModal, setShowAddModal] = useState(false);
  const [selectedType, setSelectedType] = useState(null);
  const [formData, setFormData] = useState({
    name: '',
    currentValue: '',
    purchaseValue: '',
    purchaseDate: '',
    linkedEMI: null
  });
  const [detectedEMIs, setDetectedEMIs] = useState([]);
  const [loadingEMIs, setLoadingEMIs] = useState(true);
  const [mappedEMIs, setMappedEMIs] = useState(new Set());
  const [editingAsset, setEditingAsset] = useState(null);

  // Load EMIs from Centralized Recurring Payments System
  useEffect(() => {
    const loadEMIs = async () => {
      try {
        setLoadingEMIs(true);
        const { loans } = await getAllRecurringPayments();
        
        // Transform loan EMIs to the format expected by the component
        const emis = loans.map(loan => ({
          name: loan.user_label || loan.merchant_source,
          amount: loan.emi_amount,
          count: loan.occurrence_count,
          category: loan.category,
          subcategory: loan.subcategory,
          lastDate: loan.last_detected_date,
          // Additional metadata
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
  }, []);

  // Check which EMIs are mapped to existing assets
  useEffect(() => {
    const mapped = new Set();
    assets.forEach(asset => {
      if (asset.notes) {
        // Check if notes contain EMI information
        const emiMatch = asset.notes.match(/EMI:\s*(.+)/i);
        if (emiMatch) {
          mapped.add(emiMatch[1].trim());
        }
      }
    });
    setMappedEMIs(mapped);
  }, [assets]);

  // Group assets by type
  const assetsByType = useMemo(() => {
    const grouped = {};
    ASSET_TYPES.forEach(type => {
      grouped[type.id] = assets.filter(a => a.type === type.id);
    });
    return grouped;
  }, [assets]);

  const totalValue = useMemo(() => {
    return assets.reduce((sum, a) => sum + (Number(a.purchase_value || a.purchase_price) || 0), 0);
  }, [assets]);

  const handleAddAsset = async () => {
    if (!selectedType || !formData.name || !formData.currentValue) {
      alert('Please fill all required fields');
      return;
    }

    try {
      const assetData = {
        name: formData.name,
        asset_type: selectedType.id,
        purchase_price: Number(formData.currentValue),
        purchase_date: formData.purchaseDate || new Date().toISOString().slice(0, 10),
        quantity: 1,
        notes: formData.linkedEMI ? `Linked to EMI: ${formData.linkedEMI.name}` : ''
      };

      if (editingAsset) {
        // Update existing asset
        await updateAsset(editingAsset.id, assetData);
      } else {
        // Create new asset
        await addAsset(assetData);
      }

      // Reset form
      setShowAddModal(false);
      setSelectedType(null);
      setEditingAsset(null);
      setFormData({
        name: '',
        currentValue: '',
        purchaseValue: '',
        purchaseDate: '',
        linkedEMI: null
      });
    } catch (err) {
      alert('Error saving asset: ' + (err?.message || 'unknown'));
    }
  };

  const handleDeleteAsset = async (assetId) => {
    if (!window.confirm('Delete this asset?')) return;
    try {
      await deleteAsset(assetId);
    } catch (err) {
      alert('Error deleting asset: ' + (err?.message || 'unknown'));
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

  const openAddModal = (assetType, linkedEMI = null) => {
    setSelectedType(assetType);
    setFormData({
      name: linkedEMI ? linkedEMI.name.replace(/emi|loan/gi, '').trim() : '',
      currentValue: '',
      purchaseValue: '',
      purchaseDate: '',
      linkedEMI
    });
    setShowAddModal(true);
  };

  const openEditModal = (asset) => {
    // Find the asset type
    const assetType = ASSET_TYPES.find(t => t.id === (asset.asset_type || 'other'));
    setSelectedType(assetType);
    setFormData({
      name: asset.name || '',
      currentValue: asset.purchase_price || asset.purchase_value || asset.current_value || '',
      purchaseValue: asset.purchase_price || asset.purchase_value || '',
      purchaseDate: asset.purchase_date || '',
      linkedEMI: null // Preserve existing EMI link from asset notes
    });
    setEditingAsset(asset);
    setShowAddModal(true);
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 pb-24">
      {/* Header */}
      <div className="bg-gradient-to-br from-purple-600 to-indigo-700 text-white px-4 pt-8 pb-12">
        <div className="max-w-lg mx-auto">
          <button
            onClick={() => onNavigate('profile')}
            className="mb-4 flex items-center gap-2 text-white/80 hover:text-white transition-colors"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
            </svg>
            <span className="text-sm">Back</span>
          </button>

          <h1 className="text-3xl font-bold mb-2">My Assets</h1>
          <p className="text-white/80 text-sm mb-6">Track your wealth & investments</p>

          {/* Total Value Card */}
          <div className="bg-white/10 backdrop-blur-sm rounded-2xl p-5 border border-white/20">
            <div className="text-xs text-white/70 mb-1">Total Portfolio Value</div>
            <div className="text-3xl font-bold mb-2">{formatCurrency(totalValue)}</div>
            <div className="text-xs text-white/70">{assets.length} {assets.length === 1 ? 'asset' : 'assets'}</div>
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="max-w-lg mx-auto px-4 -mt-6">
        {/* EMI Suggestions */}
        {loadingEMIs && (
          <div className="bg-gradient-to-br from-orange-50 to-amber-50 rounded-2xl p-5 border border-orange-200 mb-6 shadow-sm">
            <div className="flex items-center justify-center py-4">
              <div className="w-6 h-6 border-2 border-orange-500 border-t-transparent rounded-full animate-spin"></div>
              <span className="ml-2 text-sm text-orange-700">Loading EMIs...</span>
            </div>
          </div>
        )}
        {!loadingEMIs && detectedEMIs.length > 0 && (
          <div className="bg-gradient-to-br from-orange-50 to-amber-50 rounded-2xl p-5 border border-orange-200 mb-6 shadow-sm">
            <div className="flex items-center gap-2 mb-3">
              <span className="text-2xl">💡</span>
              <div>
                <h3 className="font-semibold text-orange-900">Add Assets from EMIs</h3>
                <p className="text-xs text-orange-700 mt-0.5">We detected {detectedEMIs.length} loan EMIs. Link them to assets!</p>
              </div>
            </div>
            <div className="space-y-2">
              {detectedEMIs.map((emi, idx) => {
                const isMapped = mappedEMIs.has(emi.name);
                const mappedAsset = assets.find(a => a.notes && a.notes.includes(emi.name));
                
                return (
                  <div key={idx} className={`flex items-center justify-between rounded-xl p-3 ${isMapped ? 'bg-green-50 border border-green-200' : 'bg-white'}`}>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <div className="font-medium text-gray-900 text-sm truncate">{emi.name}</div>
                        {isMapped && (
                          <span className="text-xs bg-green-100 text-green-700 px-2 py-0.5 rounded-full">
                            ✓ Mapped
                          </span>
                        )}
                      </div>
                      <div className="text-xs text-gray-500 mt-0.5">
                        ₹{Number(emi.amount).toLocaleString('en-IN')} × {emi.count} payments
                        {emi.subcategory && <span className="ml-2 text-orange-600">({emi.subcategory})</span>}
                        {isMapped && mappedAsset && (
                          <span className="ml-2 text-green-600">→ {mappedAsset.name}</span>
                        )}
                      </div>
                    </div>
                    {!isMapped ? (
                      <button
                        onClick={() => {
                          // Detect type from EMI name/subcategory
                          let suggestedType = ASSET_TYPES.find(t => t.id === 'other');
                          const emiName = emi.name.toLowerCase();
                          const subcat = (emi.subcategory || '').toLowerCase();
                          
                          if (emiName.includes('home') || emiName.includes('house') || emiName.includes('flat') || emiName.includes('canfin') || subcat.includes('home')) {
                            suggestedType = ASSET_TYPES.find(t => t.id === 'flat');
                          } else if (emiName.includes('car') || emiName.includes('vehicle') || subcat.includes('car')) {
                            suggestedType = ASSET_TYPES.find(t => t.id === 'car');
                          }
                          openAddModal(suggestedType, emi);
                        }}
                        className="ml-3 px-3 py-1.5 rounded-lg bg-gradient-to-r from-orange-500 to-amber-500 text-white text-xs font-medium hover:shadow-md active:scale-95 transition-all whitespace-nowrap"
                      >
                        + Add Asset
                      </button>
                    ) : (
                      <div className="flex items-center gap-2 ml-3">
                        <span className="text-xs text-green-600">Already added</span>
                        {mappedAsset && (
                          <button
                            onClick={() => openEditModal(mappedAsset)}
                            className="text-xs text-blue-600 hover:text-blue-700 underline"
                          >
                            Modify
                          </button>
                        )}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* Asset Type Cards */}
        <div className="space-y-4 mb-6">
          <h3 className="text-sm font-semibold text-gray-600 uppercase tracking-wide">Add New Asset</h3>
          <div className="grid grid-cols-2 gap-3">
            {ASSET_TYPES.map(type => (
              <button
                key={type.id}
                onClick={() => openAddModal(type)}
                className="bg-white rounded-2xl p-5 shadow-sm border border-gray-100 hover:shadow-md active:scale-98 transition-all"
              >
                <div className={`w-12 h-12 rounded-xl bg-gradient-to-br ${type.color} flex items-center justify-center text-2xl mb-3 mx-auto`}>
                  {type.icon}
                </div>
                <div className="font-semibold text-gray-900 text-sm">{type.label}</div>
                {assetsByType[type.id]?.length > 0 && (
                  <div className="text-xs text-gray-500 mt-1">
                    {assetsByType[type.id].length} {assetsByType[type.id].length === 1 ? 'item' : 'items'}
                  </div>
                )}
              </button>
            ))}
          </div>
        </div>

        {/* Existing Assets */}
        {assets.length > 0 && (
          <div className="space-y-4">
            <h3 className="text-sm font-semibold text-gray-600 uppercase tracking-wide">Your Assets</h3>
            <div className="space-y-3">
              {ASSET_TYPES.map(type => {
                const typeAssets = assetsByType[type.id];
                if (!typeAssets || typeAssets.length === 0) return null;

                return (
                  <div key={type.id}>
                    <div className="flex items-center gap-2 mb-2">
                      <div className={`w-8 h-8 rounded-lg bg-gradient-to-br ${type.color} flex items-center justify-center text-lg`}>
                        {type.icon}
                      </div>
                      <span className="font-semibold text-gray-700 text-sm">{type.label}</span>
                    </div>
                    {typeAssets.map(asset => (
                      <div key={asset.id} className="bg-white rounded-xl p-4 shadow-sm border border-gray-100 mb-2">
                        <div className="flex items-start justify-between">
                          <div className="flex-1 min-w-0">
                            <div className="font-semibold text-gray-900">{asset.name}</div>
                            <div className="text-sm text-gray-500 mt-1">
                              {formatCurrency(asset.purchase_value || asset.purchase_price || 0)}
                            </div>
                            {asset.notes && (
                              <div className="text-xs text-gray-400 mt-1 truncate">{asset.notes}</div>
                            )}
                          </div>
                          <button
                            onClick={() => handleDeleteAsset(asset.id)}
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
                );
              })}
            </div>
          </div>
        )}
      </div>

      {/* Add Asset Modal */}
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
                    <h2 className="text-xl font-bold">{editingAsset ? 'Edit' : 'Add'} {selectedType.label}</h2>
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

            {/* Modal Form */}
            <div className="p-6 space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Asset Name *</label>
                <input
                  type="text"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  placeholder={`e.g., ${selectedType.id === 'flat' ? 'My Apartment' : selectedType.id === 'car' ? 'Honda City' : selectedType.label}`}
                  className="w-full px-4 py-3 rounded-xl border border-gray-200 focus:border-purple-500 focus:ring-2 focus:ring-purple-200 outline-none transition-all"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Current Value *</label>
                <input
                  type="number"
                  value={formData.currentValue}
                  onChange={(e) => setFormData({ ...formData, currentValue: e.target.value })}
                  placeholder="Enter current market value"
                  className="w-full px-4 py-3 rounded-xl border border-gray-200 focus:border-purple-500 focus:ring-2 focus:ring-purple-200 outline-none transition-all"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Purchase Date</label>
                <input
                  type="date"
                  value={formData.purchaseDate}
                  onChange={(e) => setFormData({ ...formData, purchaseDate: e.target.value })}
                  className="w-full px-4 py-3 rounded-xl border border-gray-200 focus:border-purple-500 focus:ring-2 focus:ring-purple-200 outline-none transition-all"
                />
              </div>

              {formData.linkedEMI && (
                <div className="bg-orange-50 border border-orange-200 rounded-xl p-4">
                  <div className="flex items-start gap-2">
                    <span className="text-lg">🔗</span>
                    <div>
                      <div className="text-sm font-medium text-orange-900">Linked EMI</div>
                      <div className="text-xs text-orange-700 mt-1">{formData.linkedEMI.name}</div>
                      <div className="text-xs text-orange-600 mt-0.5">₹{formData.linkedEMI.amount.toLocaleString()}/month</div>
                    </div>
                  </div>
                </div>
              )}

              {/* Action Buttons */}
              <div className="flex gap-3 pt-4">
                <button
                  onClick={() => setShowAddModal(false)}
                  className="flex-1 py-3 px-4 rounded-xl border-2 border-gray-200 font-semibold text-gray-700 hover:bg-gray-50 active:scale-95 transition-all"
                >
                  Cancel
                </button>
                <button
                  onClick={handleAddAsset}
                  className={`flex-1 py-3 px-4 rounded-xl bg-gradient-to-r ${selectedType.color} text-white font-semibold hover:shadow-lg active:scale-95 transition-all`}
                >
                  {editingAsset ? 'Update' : 'Add'} {selectedType.label}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
