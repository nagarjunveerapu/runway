import React, { useState, useEffect } from 'react';
import { useAuth } from '../../context/AuthContext';
import api from '../../api/client';
import accountStorage from '../../utils/accountStorage';

const CSVUpload = ({ onUploadComplete }) => {
  const [file, setFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [selectedAccount, setSelectedAccount] = useState(null);
  const [progress, setProgress] = useState({ stage: '', message: '' });
  const { token, user } = useAuth();
  
  // Load accounts from API
  useEffect(() => {
    const loadAccounts = async () => {
      if (user) {
        try {
          const response = await api.get('/accounts');
          const accounts = response.data;
          if (accounts && accounts.length > 0) {
            setSelectedAccount(accounts[0]);
          }
        } catch (err) {
          console.error('Error loading accounts:', err);
        }
      }
    };
    loadAccounts();
  }, [user]);

  const handleFileChange = (e) => {
    const selectedFile = e.target.files[0];
    if (selectedFile) {
      const fileType = selectedFile.type;
      const fileName = selectedFile.name;
      
      // Accept CSV or PDF files
      if (fileType === 'text/csv' || 
          fileType === 'application/pdf' || 
          fileName.endsWith('.csv') || 
          fileName.endsWith('.pdf')) {
        setFile(selectedFile);
        setError(null);
      } else {
        setError('Please select a valid CSV or PDF file');
      }
    } else {
      setError('Please select a file');
    }
  };

  const handleUpload = async () => {
    if (!file) {
      setError('Please select a file');
      return;
    }

    setUploading(true);
    setAnalyzing(true);
    setSaving(false);
    setError(null);
    setResult(null);
    
    // Determine file type for progress message
    const isPDF = file.name.endsWith('.pdf') || file.type === 'application/pdf';
    const fileType = isPDF ? 'PDF file' : 'CSV file';
    
    setProgress({ stage: 'uploading', message: `Uploading ${fileType}...` });

    try {
      const formData = new FormData();
      formData.append('file', file);
      
      // Add account_id if available
      if (selectedAccount?.account_id) {
        formData.append('account_id', selectedAccount.account_id);
      }

      setProgress({ stage: 'analyzing', message: 'Analyzing transactions...' });

      // Use different endpoint based on file type
      const endpoint = isPDF ? '/upload/pdf' : '/upload/csv-smart';
      
      const response = await api.post(endpoint, formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
          'Authorization': `Bearer ${token}`
        },
        timeout: 60000, // 60 second timeout for large uploads
        onUploadProgress: (progressEvent) => {
          const percentCompleted = Math.round((progressEvent.loaded * 100) / progressEvent.total);
          setProgress({ stage: 'uploading', message: `Uploading... ${percentCompleted}%` });
        }
      });

      setAnalyzing(false);
      setSaving(true);
      setProgress({ stage: 'saving', message: 'Saving to database...' });

      // Simulate saving delay for better UX
      await new Promise(resolve => setTimeout(resolve, 500));

      setResult(response.data);
      
      // Don't update localStorage for accounts anymore - they're in DB
      
      setProgress({ stage: 'complete', message: '✅ Upload complete!' });
      
      // Wait a bit before redirecting
      setTimeout(() => {
        // Trigger parent callback to refresh data
        if (onUploadComplete) {
          onUploadComplete();
        }
      }, 1000);
      
    } catch (err) {
      console.error('Upload failed:', err);
      setError(err.response?.data?.detail || 'Failed to upload file');
      setProgress({ stage: 'error', message: 'Upload failed' });
    } finally {
      setUploading(false);
      setAnalyzing(false);
      setSaving(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 pb-24 px-4 pt-8">
      <div className="max-w-2xl mx-auto">
        {/* Header */}
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">Upload Transactions</h1>
          <p className="text-gray-600">Import your bank statement CSV file</p>
        </div>

        {/* Account Info */}
        {selectedAccount && (
          <div className="bg-white rounded-xl shadow-md p-6 mb-6 border-l-4 border-blue-500">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-500 mb-1">Uploading to</p>
                <p className="text-lg font-semibold text-gray-900">
                  {selectedAccount.account_name || 'Default Account'}
                </p>
                <p className="text-sm text-gray-500 mt-1">{selectedAccount.bank_name || 'N/A'}</p>
              </div>
              <div className="text-4xl">🏦</div>
            </div>
          </div>
        )}
        
        {!selectedAccount && (
          <div className="bg-yellow-50 border-l-4 border-yellow-400 rounded-lg p-4 mb-6">
            <div className="flex items-start">
              <span className="text-2xl mr-3">⚠️</span>
              <div>
                <p className="font-semibold text-yellow-800 mb-1">No accounts found</p>
                <p className="text-sm text-yellow-700">Please add an account first from the Accounts page.</p>
              </div>
            </div>
          </div>
        )}

        {/* Main Upload Card */}
        <div className="bg-white rounded-xl shadow-md overflow-hidden">
          <div className="p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">What happens after upload?</h2>
            <ul className="space-y-3 mb-6">
              <li className="flex items-start">
                <span className="text-green-600 mr-3">✓</span>
                <span className="text-gray-600">Automatically categorize transactions using ML</span>
              </li>
              <li className="flex items-start">
                <span className="text-green-600 mr-3">✓</span>
                <span className="text-gray-600">Detect and track EMI payments</span>
              </li>
              <li className="flex items-start">
                <span className="text-green-600 mr-3">✓</span>
                <span className="text-gray-600">Identify investment transactions</span>
              </li>
              <li className="flex items-start">
                <span className="text-green-600 mr-3">✓</span>
                <span className="text-gray-600">Save all data to your account</span>
              </li>
            </ul>

            {/* File Input */}
            <div className="mb-6">
              <label htmlFor="csv-file" className="block text-sm font-medium text-gray-700 mb-2">
                Select CSV File
              </label>
              
              {!file ? (
                <div className="mt-1 flex items-center justify-center w-full">
                  <label htmlFor="csv-file" className="flex flex-col items-center justify-center w-full h-32 border-2 border-gray-300 border-dashed rounded-lg cursor-pointer bg-gray-50 hover:bg-gray-100 transition">
                    <div className="flex flex-col items-center justify-center pt-5 pb-6">
                      <svg className="w-10 h-10 mb-3 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                      </svg>
                      <p className="mb-2 text-sm text-gray-500">
                        <span className="font-semibold">Click to upload</span> or drag and drop
                      </p>
                      <p className="text-xs text-gray-500">CSV or PDF files</p>
                    </div>
                  </label>
                  <input
                    id="csv-file"
                    type="file"
                    accept=".csv,.pdf"
                    onChange={handleFileChange}
                    disabled={uploading}
                    className="hidden"
                  />
                </div>
              ) : (
                <div className="mt-3 flex items-center justify-between bg-green-50 border-2 border-green-200 rounded-lg p-4">
                  <div className="flex items-center">
                    <span className="text-3xl mr-3">📄</span>
                    <div>
                      <p className="text-sm font-semibold text-gray-900">{file.name}</p>
                      <p className="text-xs text-gray-500">{(file.size / 1024).toFixed(2)} KB</p>
                    </div>
                  </div>
                  <button
                    onClick={() => {
                      setFile(null);
                      setResult(null);
                      setError(null);
                      // Reset the file input
                      document.getElementById('csv-file').value = '';
                    }}
                    disabled={uploading}
                    className="text-red-600 hover:text-red-700 disabled:opacity-50 text-xl font-bold"
                  >
                    ✕
                  </button>
                </div>
              )}
            </div>

            {/* Error Message */}
            {error && (
              <div className="mb-4 bg-red-50 border-l-4 border-red-400 rounded-lg p-4">
                <div className="flex">
                  <span className="text-2xl mr-3">⚠️</span>
                  <div>
                    <p className="font-semibold text-red-800 mb-1">Upload Failed</p>
                    <p className="text-sm text-red-700">{error}</p>
                  </div>
                </div>
              </div>
            )}

            {/* Success Message */}
            {result && (
              <div className="mb-4 bg-green-50 border-l-4 border-green-400 rounded-lg p-4">
                <div className="flex">
                  <span className="text-2xl mr-3">✓</span>
                  <div>
                    <p className="font-semibold text-green-800 mb-1">Upload Successful!</p>
                    <p className="text-sm text-green-700">
                      {result.transactions_created} transactions created
                      {result.assets_created > 0 && `, ${result.assets_created} assets`}
                      {result.emis_identified > 0 && `, ${result.emis_identified} EMIs`}
                    </p>
                  </div>
                </div>
              </div>
            )}

            {/* Upload Button */}
            <button
              onClick={handleUpload}
              disabled={!file || uploading || !selectedAccount}
              className="w-full bg-indigo-600 text-white py-3 px-6 rounded-lg font-semibold text-lg hover:bg-indigo-700 transition duration-200 disabled:opacity-50 disabled:cursor-not-allowed shadow-md hover:shadow-lg"
            >
              {uploading ? progress.message : 'Upload & Process'}
            </button>

            {/* Progress Bar */}
            {uploading && (
              <div className="mt-6 space-y-3">
                <div className="w-full bg-gray-200 rounded-full h-3 overflow-hidden">
                  <div 
                    className={`h-3 rounded-full transition-all duration-500 ${
                      progress.stage === 'uploading' ? 'bg-blue-600' :
                      progress.stage === 'analyzing' ? 'bg-yellow-600' :
                      progress.stage === 'saving' ? 'bg-green-600' :
                      progress.stage === 'complete' ? 'bg-green-600' :
                      'bg-indigo-600'
                    }`}
                    style={{ 
                      width: progress.stage === 'complete' ? '100%' : '70%',
                      transition: 'width 0.5s ease-out'
                    }}
                  />
                </div>
                <p className="text-sm text-gray-600 text-center font-medium">
                  {progress.message}
                </p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default CSVUpload;

