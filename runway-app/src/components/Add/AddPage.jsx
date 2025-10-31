// src/components/Add/AddPage.jsx
import React, { useState, useRef, useEffect } from "react";
import api from "../../api/client";

const UPLOAD_OPTIONS = [
  {
    id: "bank",
    title: "Add Bank Transactions",
    icon: "🏦",
    description: "Upload savings/current account statement (CSV/PDF)",
    accountType: "savings",
    color: "from-blue-500 to-cyan-500"
  },
  {
    id: "credit_card",
    title: "Add Credit Card Transactions",
    icon: "💳",
    description: "Upload credit card statement (CSV/PDF)",
    accountType: "credit_card",
    color: "from-orange-500 to-red-500"
  },
  {
    id: "investment",
    title: "Add Investment Transactions",
    icon: "📈",
    description: "Upload investment account statement (CSV/PDF)",
    accountType: "investment",
    color: "from-green-500 to-emerald-500"
  }
];

export default function AddPage() {
  const [showMenu, setShowMenu] = useState(false);
  const [uploading, setUploading] = useState(null);
  const [uploadResult, setUploadResult] = useState(null);
  const [uploadError, setUploadError] = useState(null);
  const fileInputRefs = useRef({});

  // Cleanup file inputs on unmount
  useEffect(() => {
    return () => {
      Object.values(fileInputRefs.current).forEach(input => {
        if (input && input.parentNode) {
          input.parentNode.removeChild(input);
        }
      });
    };
  }, []);

  const handleOptionClick = (option) => {
    // Create or get file input for this option
    if (!fileInputRefs.current[option.id]) {
      const input = document.createElement('input');
      input.type = 'file';
      input.accept = '.csv,.pdf';
      input.style.display = 'none';
      input.onchange = (e) => {
        if (e.target && e.target.files && e.target.files.length > 0) {
          handleFileUpload(option, e);
        }
        // Reset input after processing
        setTimeout(() => {
          if (input && input.value) {
            input.value = '';
          }
        }, 100);
      };
      // Append to body temporarily so it can be clicked
      document.body.appendChild(input);
      fileInputRefs.current[option.id] = input;
    }
    
    // Trigger file picker
    const input = fileInputRefs.current[option.id];
    if (input) {
      input.click();
    }
    setShowMenu(false);
  };

  const handleFileUpload = async (option, event) => {
    const file = event.target?.files?.[0];
    if (!file) return;

    // Clear previous results
    setUploadResult(null);
    setUploadError(null);
    setUploading(option.id);

    // Store reference to input element for cleanup
    const inputElement = event.target;

    try {
      const formData = new FormData();
      formData.append('file', file);
      // Don't provide account_id - let the parser auto-create from metadata
      
      // Determine endpoint based on file type
      const isPDF = file.name.endsWith('.pdf') || file.type === 'application/pdf';
      const endpoint = isPDF ? '/upload/pdf-smart' : '/upload/csv-smart';  // Use parser service for both
      
      const response = await api.post(endpoint, formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });

      setUploadResult({
        option: option.title,
        data: response.data
      });
      
      // Reset file input safely
      if (inputElement && inputElement.value) {
        try {
          inputElement.value = '';
        } catch (e) {
          // Ignore if element is already removed
          console.debug('Could not reset file input:', e);
        }
      }
      
      // Reload page after 2 seconds to show new account
      setTimeout(() => {
        window.location.reload();
      }, 2000);
    } catch (err) {
      setUploadError({
        option: option.title,
        message: err?.response?.data?.detail || 'Upload failed: unknown error'
      });
      // Reset file input safely
      if (inputElement && inputElement.value) {
        try {
          inputElement.value = '';
        } catch (e) {
          // Ignore if element is already removed
          console.debug('Could not reset file input:', e);
        }
      }
    } finally {
      setUploading(null);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 pb-24">
      <div className="max-w-4xl mx-auto px-4 py-8">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">Add Transactions</h1>
          <p className="text-gray-600">
            Upload your bank statements to automatically import transactions. Accounts will be created automatically from your statement metadata.
          </p>
        </div>

        {/* Upload Options */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mb-8">
          {UPLOAD_OPTIONS.map((option) => (
            <button
              key={option.id}
              onClick={() => handleOptionClick(option)}
              disabled={uploading === option.id}
              className={`
                relative overflow-hidden p-6 rounded-2xl text-left
                bg-white border-2 border-gray-200
                hover:border-gray-300 hover:shadow-lg
                active:scale-[0.98] transition-all
                disabled:opacity-50 disabled:cursor-not-allowed
                ${uploading === option.id ? 'pointer-events-none' : ''}
              `}
            >
              {/* Background gradient accent */}
              <div className={`absolute top-0 left-0 w-full h-1 bg-gradient-to-r ${option.color}`} />
              
              <div className="flex items-start gap-4">
                <div className={`text-4xl bg-gradient-to-br ${option.color} bg-clip-text text-transparent`}>
                  {option.icon}
                </div>
                <div className="flex-1">
                  <h3 className="font-semibold text-gray-900 mb-1">{option.title}</h3>
                  <p className="text-sm text-gray-600">{option.description}</p>
                </div>
              </div>

              {uploading === option.id && (
                <div className="mt-4 pt-4 border-t border-gray-200">
                  <div className="flex items-center gap-2 text-sm text-gray-600">
                    <div className="animate-spin h-4 w-4 border-2 border-gray-300 border-t-blue-500 rounded-full" />
                    Uploading and processing...
                  </div>
                </div>
              )}
            </button>
          ))}
        </div>

        {/* Upload Success Message */}
        {uploadResult && (
          <div className="mb-6 p-4 bg-green-50 border border-green-200 rounded-lg">
            <div className="flex items-start gap-3">
              <div className="text-2xl">✅</div>
              <div className="flex-1">
                <h3 className="font-semibold text-green-900 mb-1">Upload Successful!</h3>
                <p className="text-sm text-green-700 mb-2">
                  {uploadResult.option}: {uploadResult.data.message || 'File processed successfully'}
                </p>
                {uploadResult.data.transactions_created && (
                  <div className="text-sm text-green-600 space-y-1">
                    <div>📊 Transactions imported: {uploadResult.data.transactions_created}</div>
                    {uploadResult.data.transactions_found && (
                      <div>📄 Total transactions found: {uploadResult.data.transactions_found}</div>
                    )}
                    {uploadResult.data.duplicates_found > 0 && (
                      <div>🔄 Duplicates skipped: {uploadResult.data.duplicates_found}</div>
                    )}
                    {uploadResult.data.emis_identified > 0 && (
                      <div>💰 EMIs identified: {uploadResult.data.emis_identified}</div>
                    )}
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        {/* Upload Error Message */}
        {uploadError && (
          <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg">
            <div className="flex items-start gap-3">
              <div className="text-2xl">❌</div>
              <div className="flex-1">
                <h3 className="font-semibold text-red-900 mb-1">Upload Failed</h3>
                <p className="text-sm text-red-700">
                  {uploadError.option}: {uploadError.message}
                </p>
              </div>
            </div>
          </div>
        )}

        {/* Info Section */}
        <div className="mt-8 p-6 bg-blue-50 border border-blue-200 rounded-lg">
          <h3 className="font-semibold text-blue-900 mb-2">💡 How it works</h3>
          <ul className="text-sm text-blue-800 space-y-1 list-disc list-inside">
            <li>Upload your bank/credit card statement (CSV or PDF)</li>
            <li>The system automatically extracts account number, holder name, and bank name from your statement</li>
            <li>An account is created automatically if it doesn't exist</li>
            <li>All transactions are imported and linked to the account</li>
            <li>Duplicate transactions are automatically detected and skipped</li>
          </ul>
        </div>
      </div>
    </div>
  );
}