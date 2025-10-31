// src/components/Modern/ModernAccounts.jsx
import React, { useState, useMemo, useEffect } from 'react';
import { useAuth } from '../../context/AuthContext';
import api from '../../api/client';
import { getAccounts, createAccount, deleteAccount as apiDeleteAccount, resetAccountData } from '../../api/services/accounts';

/**
 * ModernAccounts - Bank accounts and credit cards management
 * Upload CSV per account, prepare for future Account Aggregator API integration
 */

const ACCOUNT_TYPES = [
  {
    id: 'savings',
    label: 'Savings Account',
    icon: '🏦',
    color: 'from-blue-500 to-cyan-500',
    description: 'Regular savings account'
  },
  {
    id: 'current',
    label: 'Current Account',
    icon: '💼',
    color: 'from-purple-500 to-indigo-500',
    description: 'Business/current account'
  },
  {
    id: 'credit_card',
    label: 'Credit Card',
    icon: '💳',
    color: 'from-orange-500 to-red-500',
    description: 'Credit card account'
  },
  {
    id: 'investment',
    label: 'Investment Account',
    icon: '📈',
    color: 'from-green-500 to-emerald-500',
    description: 'Mutual funds, stocks'
  }
];

export default function ModernAccounts() {
  const { user } = useAuth();
  const [accounts, setAccounts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showAddModal, setShowAddModal] = useState(false);
  const [selectedType, setSelectedType] = useState(null);
  const [formData, setFormData] = useState({
    name: '',
    bankName: '',
    accountNumber: ''
  });
  const [uploadingFor, setUploadingFor] = useState(null);
  const [uploadResult, setUploadResult] = useState({}); // Store results by accountId
  const [uploadError, setUploadError] = useState({}); // Store errors by accountId

  // Load accounts from API
  useEffect(() => {
    loadAccounts();
  }, []);

  const loadAccounts = async () => {
    try {
      const data = await getAccounts();
      setAccounts(data);
    } catch (err) {
      console.error('Error loading accounts:', err);
    } finally {
      setLoading(false);
    }
  };

  const formatCurrency = (amount) => {
    if (amount >= 10000000) return `₹${(amount / 10000000).toFixed(2)}Cr`;
    if (amount >= 100000) return `₹${(amount / 100000).toFixed(2)}L`;
    if (amount >= 1000) return `₹${(amount / 1000).toFixed(1)}K`;
    return `₹${amount.toFixed(0)}`;
  };

  const handleAddAccount = async () => {
    if (!selectedType || !formData.name || !formData.bankName) {
      alert('Please fill all required fields');
      return;
    }

    try {
      const newAccount = await createAccount({
        account_name: formData.name,
        bank_name: formData.bankName,
        account_type: selectedType.id,
        account_number: formData.accountNumber || null
      });

      // Reload accounts to get the new one
      await loadAccounts();

      // Reset form
      setShowAddModal(false);
      setSelectedType(null);
      setFormData({
        name: '',
        bankName: '',
        accountNumber: ''
      });
    } catch (err) {
      alert('Error adding account: ' + (err?.response?.data?.detail || 'unknown'));
    }
  };

  const handleDeleteAccount = async (accountId) => {
    if (!window.confirm('Delete this account? All associated transactions will remain.')) return;
    
    try {
      await apiDeleteAccount(accountId);
      await loadAccounts();
    } catch (err) {
      alert('Error deleting account: ' + (err?.response?.data?.detail || 'unknown'));
    }
  };

  const handleResetAccountData = async (accountId) => {
    if (!window.confirm('⚠️ WARNING: This will delete ALL transactions for this account!\n\nThis action cannot be undone.\n\nAre you sure?')) return;
    
    try {
      const result = await resetAccountData(accountId);
      alert(`✅ Reset complete! Deleted ${result.transactions_deleted} transactions.`);
      await loadAccounts();
      // Reload the page to refresh data
      window.location.reload();
    } catch (err) {
      alert('Error resetting account data: ' + (err?.response?.data?.detail || 'unknown'));
    }
  };

  const handleFileUpload = async (accountId, event) => {
    const file = event.target.files[0];
    if (!file) return;

    // Clear previous results for this specific account
    setUploadResult(prev => {
      const newResult = { ...prev };
      delete newResult[accountId];
      return newResult;
    });
    setUploadError(prev => {
      const newError = { ...prev };
      delete newError[accountId];
      return newError;
    });

    // Upload directly from here
    try {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('account_id', accountId);

      // Show uploading state
      setUploadingFor(accountId);
      
      // Determine endpoint based on file type
      const isPDF = file.name.endsWith('.pdf') || file.type === 'application/pdf';
      const endpoint = isPDF ? '/upload/pdf-smart' : '/upload/csv-smart';  // Use parser service for both
      
      const response = await api.post(endpoint, formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });

      // Show detailed result for this specific account
      setUploadResult(prev => ({
        ...prev,
        [accountId]: response.data
      }));
      
      // Reset file input
      event.target.value = '';
      
      // Reload data after 2 seconds
      setTimeout(() => {
        window.location.reload();
      }, 2000);
    } catch (err) {
      // Store error for this specific account
      setUploadError(prev => ({
        ...prev,
        [accountId]: err?.response?.data?.detail || 'Upload failed: unknown error'
      }));
      // Clear result for this account
      setUploadResult(prev => {
        const newResult = { ...prev };
        delete newResult[accountId];
        return newResult;
      });
    } finally {
      setUploadingFor(null);
    }
  };

  const openAddModal = (accountType) => {
    setSelectedType(accountType);
    setFormData({
      name: '',
      bankName: '',
      accountNumber: ''
    });
    setShowAddModal(true);
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 pb-24 flex items-center justify-center">
        <div className="text-gray-600">Loading accounts...</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 pb-24">
      {/* Header */}
      <div className="bg-gradient-to-br from-indigo-600 to-purple-700 text-white px-4 pt-8 pb-12">
        <div className="max-w-lg mx-auto">
          <h1 className="text-3xl font-bold mb-2">My Accounts</h1>
          <p className="text-white/80 text-sm mb-6">Manage bank accounts & cards</p>
          
          <button
            onClick={() => setShowAddModal(true)}
            className="bg-white/20 hover:bg-white/30 text-white px-4 py-2 rounded-lg text-sm font-medium backdrop-blur transition"
          >
            + Add Account
          </button>
        </div>
      </div>

      {/* Accounts Grid */}
      <div className="max-w-lg mx-auto px-4 -mt-8">
        {accounts.length === 0 ? (
          <div className="bg-white rounded-2xl shadow-md p-8 text-center">
            <div className="text-6xl mb-4">🏦</div>
            <h3 className="text-xl font-semibold text-gray-800 mb-2">No Accounts Yet</h3>
            <p className="text-gray-600 mb-6">Add your first bank account to start tracking transactions</p>
            <button
              onClick={() => setShowAddModal(true)}
              className="bg-indigo-600 text-white px-6 py-3 rounded-lg font-medium hover:bg-indigo-700 transition"
            >
              Add Account
            </button>
          </div>
        ) : (
          <div className="space-y-4">
            {accounts.map(account => (
              <div
                key={account.account_id}
                className="bg-white rounded-2xl shadow-md overflow-hidden"
              >
                {/* Account Header */}
                <div className={`bg-gradient-to-r ${ACCOUNT_TYPES.find(t => t.id === account.account_type)?.color || 'from-gray-500 to-gray-600'} p-6 text-white`}>
                  <div className="flex items-center justify-between mb-2">
                    <h3 className="text-xl font-bold">{account.account_name}</h3>
                    <div className="flex gap-2">
                      <button
                        onClick={() => handleResetAccountData(account.account_id)}
                        className="bg-white/20 hover:bg-white/30 px-3 py-1 rounded text-sm transition"
                        title="Reset all data for this account"
                      >
                        🔄 Reset
                      </button>
                      <button
                        onClick={() => handleDeleteAccount(account.account_id)}
                        className="bg-white/20 hover:bg-white/30 px-3 py-1 rounded text-sm transition"
                      >
                        🗑️ Delete
                      </button>
                    </div>
                  </div>
                  <p className="text-white/90 text-sm">{account.bank_name}</p>
                </div>

                {/* Account Details */}
                <div className="p-6">
                  <div className="space-y-3 mb-6">
                    <div className="flex items-center justify-between text-sm">
                      <span className="text-gray-600">Account Number</span>
                      <span className="font-medium text-gray-800">{account.account_number_ref || 'N/A'}</span>
                    </div>
                    <div className="flex items-center justify-between text-sm">
                      <span className="text-gray-600">Type</span>
                      <span className="font-medium text-gray-800 capitalize">{account.account_type}</span>
                    </div>
                    <div className="flex items-center justify-between text-sm">
                      <span className="text-gray-600">Currency</span>
                      <span className="font-medium text-gray-800">{account.currency}</span>
                    </div>
                  </div>

                  {/* Upload CSV or PDF */}
                  <label className="block">
                    <input
                      type="file"
                      accept=".csv,.pdf"
                      className="hidden"
                      onChange={(e) => handleFileUpload(account.account_id, e)}
                      disabled={uploadingFor === account.account_id}
                    />
                    <div className={`border-2 border-dashed rounded-lg p-4 text-center transition ${
                      uploadingFor === account.account_id 
                        ? 'bg-blue-50 border-blue-300 cursor-wait' 
                        : 'bg-gray-50 hover:bg-gray-100 border-gray-300 cursor-pointer'
                    }`}>
                      {uploadingFor === account.account_id ? (
                        <div className="flex items-center justify-center">
                          <svg className="animate-spin h-5 w-5 mr-2 text-blue-600" fill="none" viewBox="0 0 24 24">
                            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                          </svg>
                          <span className="text-blue-600 text-sm font-medium">Uploading...</span>
                        </div>
                      ) : (
                        <span className="text-gray-600 text-sm">📁 Upload Statement CSV or PDF</span>
                      )}
                    </div>
                  </label>

                  {/* Upload Result - Show only for this specific account */}
                  {uploadResult[account.account_id] && !uploadingFor && (
                    <div className="mt-3 bg-green-50 border-l-4 border-green-400 rounded-lg p-4">
                      <div className="flex items-start">
                        <span className="text-2xl mr-3">✓</span>
                        <div className="flex-1">
                          <p className="font-semibold text-green-800 mb-2">Upload Successful!</p>
                          <div className="space-y-1 text-sm">
                            <div className="flex items-center justify-between">
                              <span className="text-green-700">📊 Transactions imported:</span>
                              <span className="font-bold text-green-800">
                                {uploadResult[account.account_id].transactions_imported || uploadResult[account.account_id].transactions_created || 0}
                              </span>
                            </div>
                            {uploadResult[account.account_id].duplicates_found > 0 && (
                              <div className="flex items-center justify-between bg-yellow-100 rounded p-2 mt-1">
                                <span className="text-orange-700">🔄 Duplicates skipped:</span>
                                <span className="font-bold text-orange-800">
                                  {uploadResult[account.account_id].duplicates_found}
                                </span>
                              </div>
                            )}
                            {uploadResult[account.account_id].emis_identified > 0 && (
                              <div className="flex items-center justify-between">
                                <span className="text-green-700">💳 EMIs identified:</span>
                                <span className="font-bold text-green-800">
                                  {uploadResult[account.account_id].emis_identified}
                                </span>
                              </div>
                            )}
                            {uploadResult[account.account_id].assets_created > 0 && (
                              <div className="flex items-center justify-between">
                                <span className="text-green-700">🏠 Assets created:</span>
                                <span className="font-bold text-green-800">
                                  {uploadResult[account.account_id].assets_created}
                                </span>
                              </div>
                            )}
                          </div>
                        </div>
                      </div>
                    </div>
                  )}

                  {/* Upload Error - Show only for this specific account */}
                  {uploadError[account.account_id] && !uploadingFor && (
                    <div className="mt-3 bg-red-50 border-l-4 border-red-400 rounded-lg p-4">
                      <div className="flex items-start">
                        <span className="text-2xl mr-3">⚠️</span>
                        <div>
                          <p className="font-semibold text-red-800 mb-1">Upload Failed</p>
                          <p className="text-sm text-red-700">{uploadError[account.account_id]}</p>
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Add Account Modal */}
      {showAddModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-2xl shadow-2xl max-w-md w-full p-6">
            <h2 className="text-2xl font-bold mb-6">Add New Account</h2>

            {!selectedType ? (
              <div className="grid grid-cols-2 gap-3">
                {ACCOUNT_TYPES.map(type => (
                  <button
                    key={type.id}
                    onClick={() => openAddModal(type)}
                    className={`p-4 rounded-lg border-2 border-gray-200 hover:border-indigo-500 transition text-center`}
                  >
                    <div className="text-3xl mb-2">{type.icon}</div>
                    <div className="text-sm font-medium text-gray-800">{type.label}</div>
                  </button>
                ))}
              </div>
            ) : (
              <form onSubmit={(e) => { e.preventDefault(); handleAddAccount(); }}>
                <div className="space-y-4 mb-6">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Account Name
                    </label>
                    <input
                      type="text"
                      required
                      className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                      value={formData.name}
                      onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                      placeholder="e.g., HDFC Savings"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Bank Name
                    </label>
                    <input
                      type="text"
                      required
                      className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                      value={formData.bankName}
                      onChange={(e) => setFormData({ ...formData, bankName: e.target.value })}
                      placeholder="e.g., HDFC Bank"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Account Number (optional)
                    </label>
                    <input
                      type="text"
                      className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                      value={formData.accountNumber}
                      onChange={(e) => setFormData({ ...formData, accountNumber: e.target.value })}
                      placeholder="Last 4 digits"
                    />
                  </div>
                </div>

                <div className="flex gap-3">
                  <button
                    type="button"
                    onClick={() => {
                      setShowAddModal(false);
                      setSelectedType(null);
                    }}
                    className="flex-1 px-4 py-3 bg-gray-100 text-gray-700 rounded-lg font-medium hover:bg-gray-200 transition"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    className="flex-1 px-4 py-3 bg-indigo-600 text-white rounded-lg font-medium hover:bg-indigo-700 transition"
                  >
                    Add Account
                  </button>
                </div>
              </form>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

