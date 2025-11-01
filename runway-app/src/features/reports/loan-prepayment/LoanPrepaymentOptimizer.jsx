// src/components/Reports/LoanPrepaymentOptimizerNew.jsx
import React, { useState, useEffect } from 'react';
import { detectLoanPatterns, calculatePrepaymentOptimization } from '../../api/services/loanPrepayment';
import { getLoans, transformToLoan } from '../../api/services/recurringPayments';

/**
 * LoanPrepaymentOptimizer - Uses centralized recurring payments
 * Fetches loan EMIs from Salary Sweep configuration
 */

export default function LoanPrepaymentOptimizer() {
  const [detectedData, setDetectedData] = useState(null);
  const [savedLoans, setSavedLoans] = useState([]); // From Salary Sweep
  const [loans, setLoans] = useState([]);
  const [annualPrepayment, setAnnualPrepayment] = useState(100000);
  const [monthlyIncome, setMonthlyIncome] = useState(100000);
  const [monthlyExpenses, setMonthlyExpenses] = useState(50000);
  const [scenarios, setScenarios] = useState(null);

  const [loading, setLoading] = useState(true);
  const [calculating, setCalculating] = useState(false);
  const [error, setError] = useState(null);
  const [showLoanForm, setShowLoanForm] = useState(false);

  // Load loans from centralized recurring payments
  useEffect(() => {
    loadSavedLoans();
  }, []);

  const loadSavedLoans = async () => {
    try {
      setLoading(true);
      setError(null);

      // Fetch ONLY loans from centralized endpoint
      const loansFromSalarySweep = await getLoans();
      console.log('Loans from API:', loansFromSalarySweep);

      if (loansFromSalarySweep && loansFromSalarySweep.length > 0) {
        // Transform to expected format for display
        const transformed = loansFromSalarySweep.map(loan => ({
          pattern_id: loan.pattern_id,
          source: loan.user_label || loan.merchant_source || 'Loan',
          avg_emi: loan.emi_amount || 0,
          count: loan.occurrence_count || 0,
          category: loan.category,
          subcategory: loan.subcategory
        }));
        
        console.log('Transformed loans:', transformed);
        
        setSavedLoans(transformed);
        setDetectedData({
          detected_loans: transformed,
          monthly_income: 100000,
          monthly_expenses: 50000,
          source: 'salary_sweep'
        });
        
        // Automatically add all detected loans to the loans array
        const initialLoans = transformed.map((detectedLoan, idx) => ({
          loan_id: `loan_${Date.now()}_${idx}`,
          name: detectedLoan.source,
          source: detectedLoan.source,
          emi: detectedLoan.avg_emi,
          remaining_principal: detectedLoan.remaining_principal || detectedLoan.avg_emi * 100, // Use calculated or estimate
          interest_rate: 10.0,
          remaining_tenure_months: 60,
          is_completed: detectedLoan.is_completed || false,
          original_principal: detectedLoan.original_principal || null,
          total_paid: detectedLoan.total_paid || null
        }));
        setLoans(initialLoans);
        console.log('Initial loans set:', initialLoans);
      } else {
        // Fallback to old detection if no saved loans
        const data = await detectLoanPatterns();
        console.log('✅ Raw detected data:', data);
        console.log('✅ First loan details:', data.detected_loans?.[0]);
        console.log('✅ Second loan details:', data.detected_loans?.[1]);
        console.log('🔍 Detected loans count:', data.detected_loans?.length);
        
        if (data.detected_loans && data.detected_loans.length > 0) {
          console.log('🔍 First detected loan:', JSON.stringify(data.detected_loans[0], null, 2));
          console.log('🔍 Second detected loan:', JSON.stringify(data.detected_loans[1], null, 2));
          
          // Check if principal fields are present
          data.detected_loans.forEach((loan, idx) => {
            console.log(`🔍 Loan ${idx} (${loan.source}):`, {
              original_principal: loan.original_principal,
              remaining_principal: loan.remaining_principal,
              is_completed: loan.is_completed,
              total_paid: loan.total_paid,
              hasOriginalPrincipal: loan.original_principal !== null && loan.original_principal !== undefined,
              hasRemainingPrincipal: loan.remaining_principal !== null && loan.remaining_principal !== undefined
            });
          });
        }
        
        setDetectedData(data);
        setMonthlyIncome(data.monthly_income || 100000);
        setMonthlyExpenses(data.monthly_expenses || 50000);
        
        // Automatically add all detected loans to the loans array
        if (data.detected_loans && data.detected_loans.length > 0) {
          const initialLoans = data.detected_loans.map((detectedLoan, idx) => {
            console.log(`🔍 Processing loan ${idx}:`, detectedLoan);
            return {
              loan_id: `loan_${Date.now()}_${idx}`,
              name: detectedLoan.source,
              source: detectedLoan.source,
              emi: detectedLoan.avg_emi,
              remaining_principal: detectedLoan.remaining_principal !== null && detectedLoan.remaining_principal !== undefined 
                ? detectedLoan.remaining_principal 
                : detectedLoan.avg_emi * 100,
              interest_rate: 10.0,
              remaining_tenure_months: 60,
              is_completed: detectedLoan.is_completed || false,
              original_principal: detectedLoan.original_principal || null,
              total_paid: detectedLoan.total_paid || null
            };
          });
          console.log('🔍 Initial loans:', initialLoans);
          setLoans(initialLoans);
        }
      }
    } catch (err) {
      console.error('Error loading loans:', err);
      setError(err.response?.data?.detail || err.message || 'Failed to load loans');
      setDetectedData({ detected_loans: [], monthly_income: 100000, monthly_expenses: 50000 });
    } finally {
      setLoading(false);
    }
  };

  const handleAddLoan = (detectedLoan) => {
    const newLoan = {
      loan_id: `loan_${Date.now()}`,
      name: detectedLoan.source,
      source: detectedLoan.source,
      emi: detectedLoan.avg_emi,
      remaining_principal: detectedLoan.remaining_principal || detectedLoan.avg_emi * 100, // Use calculated or estimate
      interest_rate: 10.0,
      remaining_tenure_months: 60,
      is_completed: detectedLoan.is_completed || false,
      original_principal: detectedLoan.original_principal || null,
      total_paid: detectedLoan.total_paid || null
    };
    setLoans([...loans, newLoan]);
  };

  const handleRemoveLoan = (loanId) => {
    setLoans(loans.filter(l => l.loan_id !== loanId));
  };

  const handleUpdateLoan = (loanId, field, value) => {
    setLoans(loans.map(loan =>
      loan.loan_id === loanId ? { ...loan, [field]: typeof value === 'boolean' ? value : (parseFloat(value) || 0) } : loan
    ));
  };

  const handleToggleCompleted = (loanId) => {
    setLoans(loans.map(loan =>
      loan.loan_id === loanId ? { ...loan, is_completed: !loan.is_completed } : loan
    ));
  };

  const handleCalculate = async () => {
    if (loans.length === 0) {
      alert('Please add at least one loan');
      return;
    }

    try {
      setCalculating(true);
      setError(null);

      const result = await calculatePrepaymentOptimization({
        loans,
        annual_prepayment: annualPrepayment,
        monthly_income: monthlyIncome,
        monthly_expenses: monthlyExpenses
      });

      setScenarios(result.scenarios);
    } catch (err) {
      console.error('Error calculating optimization:', err);
      const errorMessage = err.response?.data?.detail || err.message || 'Failed to calculate optimization';
      setError(`Calculation Error: ${errorMessage}`);
    } finally {
      setCalculating(false);
    }
  };

  const formatCurrency = (amount) => {
    return `₹${Math.round(amount).toLocaleString('en-IN')}`;
  };

  const formatMonths = (months) => {
    const years = Math.floor(months / 12);
    const remainingMonths = months % 12;
    if (years === 0) return `${remainingMonths}m`;
    if (remainingMonths === 0) return `${years}y`;
    return `${years}y ${remainingMonths}m`;
  };

  if (loading) {
    return (
      <div className="bg-gradient-to-br from-red-50 to-orange-50 p-6 rounded-xl shadow-lg border-2 border-red-200">
        <h3 className="text-xl font-bold text-gray-900 mb-4">🎯 Loan Prepayment Optimizer</h3>
        <div className="text-sm text-gray-600">Loading patterns...</div>
      </div>
    );
  }

  // Show empty state if no loans detected and none added
  if (!detectedData || (detectedData.detected_loans.length === 0 && loans.length === 0 && !showLoanForm)) {
    return (
      <div className="bg-gradient-to-br from-red-50 to-orange-50 p-6 rounded-xl shadow-lg border-2 border-red-200">
        <div className="flex items-center gap-3 mb-4">
          <div className="bg-red-600 text-white p-3 rounded-full">
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 14l6-6m-5.5.5h.01m4.99 5h.01M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16l3.5-2 3.5 2 3.5-2 3.5 2zM10 8.5a.5.5 0 11-1 0 .5.5 0 011 0zm5 5a.5.5 0 11-1 0 .5.5 0 011 0z" />
            </svg>
          </div>
          <div>
            <h3 className="text-xl font-bold text-gray-900">🎯 Loan Prepayment Optimizer</h3>
          </div>
        </div>
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
          <div className="flex items-start gap-3">
            <span className="text-2xl">💡</span>
            <div>
              <p className="text-sm font-medium text-blue-900 mb-1">No loan EMIs found</p>
              <p className="text-xs text-blue-700 mb-3">
                Set up your loan EMIs in Salary Sweep first, then they'll automatically appear here!
              </p>
              <button
                onClick={() => window.location.href = '#/optimize/salary-sweep'}
                className="text-xs bg-blue-600 text-white px-3 py-2 rounded-lg hover:bg-blue-700 font-medium"
              >
                → Go to Salary Sweep to Set Up EMIs
              </button>
              <p className="text-xs text-gray-500 mt-3">
                Or manually add a loan using the button below
              </p>
            </div>
          </div>
        </div>
        {error && (
          <div className="mt-4 bg-red-100 border border-red-300 rounded-lg p-3 text-sm text-red-700">
            {error}
          </div>
        )}
        <button
          onClick={() => setShowLoanForm(true)}
          className="mt-4 w-full bg-white border-2 border-red-300 text-red-600 font-semibold py-3 rounded-lg hover:bg-red-50"
        >
          + Add Loan Manually
        </button>
      </div>
    );
  }

  return (
    <div className="bg-gradient-to-br from-red-50 to-orange-50 p-6 rounded-xl shadow-lg border-2 border-red-200">
      {/* Header */}
      <div className="flex items-center gap-3 mb-6">
        <div className="bg-red-600 text-white p-3 rounded-full">
          <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 14l6-6m-5.5.5h.01m4.99 5h.01M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16l3.5-2 3.5 2 3.5-2 3.5 2zM10 8.5a.5.5 0 11-1 0 .5.5 0 011 0zm5 5a.5.5 0 11-1 0 .5.5 0 011 0z" />
          </svg>
        </div>
        <div>
          <h3 className="text-xl font-bold text-gray-900">
            🎯 Loan Prepayment Optimizer
          </h3>
          <p className="text-sm text-gray-600">
            Close high-interest loans faster and save lakhs in interest
          </p>
        </div>
      </div>

      {error && (
        <div className="mb-4 bg-red-100 border border-red-300 rounded-lg p-3 text-sm text-red-700">
          {error}
        </div>
      )}

      {/* Info Banner - Loaded from Salary Sweep */}
      {detectedData && detectedData.source === 'salary_sweep' && savedLoans.length > 0 && (
        <div className="mb-4 bg-green-50 border border-green-200 rounded-lg p-4">
          <div className="flex items-start gap-3">
            <span className="text-2xl">✅</span>
            <div>
              <p className="text-sm font-medium text-green-900 mb-1">
                Loaded {savedLoans.length} loan(s) from Salary Sweep
              </p>
              <p className="text-xs text-green-700">
                Your loan EMIs are pre-filled from your Salary Sweep configuration. Just fill in the additional details below!
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Detected Loans */}
      {detectedData && detectedData.detected_loans && detectedData.detected_loans.length > 0 && (
        <div className="mb-6 bg-white rounded-lg p-4">
          <h4 className="text-sm font-semibold text-gray-700 mb-3">
            {detectedData.source === 'salary_sweep' ? '💰 Your Saved Loan EMIs' : '✓ Detected Recurring EMIs'}
          </h4>
          {detectedData.detected_loans.map((detected, idx) => {
            // Log for debugging
            if (idx === 0) {
              console.log('🎨 Rendering loan:', {
                source: detected.source,
                is_completed: detected.is_completed,
                original_principal: detected.original_principal,
                remaining_principal: detected.remaining_principal
              });
            }
            
            return (
              <div key={idx} className="flex items-center justify-between py-2 border-b last:border-b-0">
                <div className="flex-1">
                  <div className="flex items-center gap-2">
                    <div className="text-sm font-medium">{detected.source}</div>
                    {detected.is_completed === true && (
                      <span className="px-2 py-0.5 text-xs bg-green-100 text-green-700 rounded-full font-medium">
                        ✅ Completed
                      </span>
                    )}
                    {detected.is_completed === false && detected.remaining_principal != null && detected.remaining_principal > 0 && (
                      <span className="px-2 py-0.5 text-xs bg-orange-100 text-orange-700 rounded-full font-medium">
                        ⏳ Active
                      </span>
                    )}
                  </div>
                  <div className="text-xs text-gray-500 mt-1">
                    {formatCurrency(detected.avg_emi)}/month · {detected.count} payments
                  </div>
                  {(detected.remaining_principal != null || detected.original_principal != null) && (
                    <div className="text-xs font-semibold text-gray-700 mt-1">
                      {detected.remaining_principal != null ? (
                        detected.remaining_principal > 0 
                          ? `Principal: ₹${Math.round(detected.remaining_principal).toLocaleString('en-IN')} remaining`
                          : `✅ Paid Off`
                      ) : (
                        detected.original_principal != null && `Principal: ₹${Math.round(detected.original_principal).toLocaleString('en-IN')}`
                      )}
                    </div>
                  )}
                </div>
                <button
                  onClick={() => handleAddLoan(detected)}
                  disabled={loans.some(l => l.source === detected.source)}
                  className="px-3 py-1 text-xs bg-red-600 text-white rounded hover:bg-red-700 disabled:bg-gray-300 disabled:cursor-not-allowed"
                >
                  {loans.some(l => l.source === detected.source) ? 'Added' : '+ Add'}
                </button>
              </div>
            );
          })}
        </div>
      )}

      {/* Added Loans */}
      {loans.length > 0 && (
        <div className="mb-6 space-y-3">
          <h4 className="text-sm font-semibold text-gray-700">Your Loans</h4>
          {loans.map((loan) => (
            <div key={loan.loan_id} className={`bg-white rounded-lg p-4 border-2 ${loan.is_completed ? 'border-green-300 bg-green-50' : 'border-gray-200'}`}>
              {/* Principal Display at Top */}
              {loan.remaining_principal !== null && loan.remaining_principal !== undefined && (
                <div className={`mb-3 p-3 rounded-lg ${loan.is_completed ? 'bg-green-100 border border-green-300' : 'bg-orange-50 border border-orange-200'}`}>
                  <div className="flex items-center justify-between">
                    <div>
                      <div className="text-xs text-gray-600 mb-1">Remaining Principal</div>
                      <div className={`text-lg font-bold ${loan.is_completed ? 'text-green-700' : 'text-orange-700'}`}>
                        {loan.remaining_principal > 0 
                          ? `₹${Math.round(loan.remaining_principal).toLocaleString('en-IN')}`
                          : `✅ Paid Off`}
                      </div>
                      {loan.original_principal && (
                        <div className="text-xs text-gray-500 mt-1">
                          Original: ₹{Math.round(loan.original_principal).toLocaleString('en-IN')}
                        </div>
                      )}
                    </div>
                    <button
                      onClick={() => handleToggleCompleted(loan.loan_id)}
                      className={`px-3 py-1.5 text-xs rounded-lg font-medium ${
                        loan.is_completed 
                          ? 'bg-green-600 text-white hover:bg-green-700' 
                          : 'bg-orange-600 text-white hover:bg-orange-700'
                      }`}
                    >
                      {loan.is_completed ? '✅ Completed' : '⏳ Mark Complete'}
                    </button>
                  </div>
                </div>
              )}
              
              <div className="flex items-center justify-between mb-3">
                <h5 className="font-semibold text-gray-900">{loan.name}</h5>
                <button
                  onClick={() => handleRemoveLoan(loan.loan_id)}
                  className="text-red-600 hover:text-red-800 text-sm"
                >
                  Remove
                </button>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs text-gray-600">EMI (₹)</label>
                  <input
                    type="number"
                    value={loan.emi}
                    onChange={(e) => handleUpdateLoan(loan.loan_id, 'emi', e.target.value)}
                    className="w-full p-2 border rounded text-sm"
                    disabled
                  />
                </div>
                <div>
                  <label className="text-xs text-gray-600">Remaining Principal (₹)</label>
                  <input
                    type="number"
                    value={loan.remaining_principal}
                    onChange={(e) => handleUpdateLoan(loan.loan_id, 'remaining_principal', e.target.value)}
                    className="w-full p-2 border rounded text-sm"
                    placeholder="e.g., 2500000"
                  />
                </div>
                <div>
                  <label className="text-xs text-gray-600">Interest Rate (%)</label>
                  <input
                    type="number"
                    step="0.1"
                    value={loan.interest_rate}
                    onChange={(e) => handleUpdateLoan(loan.loan_id, 'interest_rate', e.target.value)}
                    className={`w-full p-2 border rounded text-sm ${loan.is_completed ? 'bg-gray-100' : ''}`}
                    placeholder="e.g., 8.5"
                    disabled={loan.is_completed}
                  />
                </div>
                <div>
                  <label className="text-xs text-gray-600">Remaining Tenure (months)</label>
                  <input
                    type="number"
                    value={loan.remaining_tenure_months}
                    onChange={(e) => handleUpdateLoan(loan.loan_id, 'remaining_tenure_months', e.target.value)}
                    className={`w-full p-2 border rounded text-sm ${loan.is_completed ? 'bg-gray-100' : ''}`}
                    placeholder="e.g., 180"
                    disabled={loan.is_completed}
                  />
                </div>
              </div>
              {loan.is_completed && (
                <div className="mt-3 p-2 bg-green-50 border border-green-200 rounded text-xs text-green-700">
                  ✅ This loan is marked as completed and will be excluded from prepayment calculations
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Cash Flow Inputs */}
      <div className="mb-6 bg-white rounded-lg p-4">
        <h4 className="text-sm font-semibold text-gray-700 mb-3">Cash Flow</h4>
        <div className="grid grid-cols-3 gap-3">
          <div>
            <label className="text-xs text-gray-600">Monthly Income</label>
            <input
              type="number"
              value={monthlyIncome}
              onChange={(e) => setMonthlyIncome(parseFloat(e.target.value) || 0)}
              className="w-full p-2 border rounded text-sm"
            />
          </div>
          <div>
            <label className="text-xs text-gray-600">Monthly Expenses</label>
            <input
              type="number"
              value={monthlyExpenses}
              onChange={(e) => setMonthlyExpenses(parseFloat(e.target.value) || 0)}
              className="w-full p-2 border rounded text-sm"
            />
          </div>
          <div>
            <label className="text-xs text-gray-600">Annual Prepayment</label>
            <input
              type="number"
              value={annualPrepayment}
              onChange={(e) => setAnnualPrepayment(parseFloat(e.target.value) || 0)}
              className="w-full p-2 border rounded text-sm"
            />
          </div>
        </div>
      </div>

      {/* Calculate Button */}
      <button
        onClick={handleCalculate}
        disabled={calculating || loans.length === 0}
        className="w-full bg-red-600 text-white py-3 rounded-lg font-semibold hover:bg-red-700 disabled:bg-gray-400 disabled:cursor-not-allowed mb-6"
      >
        {calculating ? 'Calculating...' : 'Calculate Optimization'}
      </button>

      {/* Results */}
      {scenarios && (
        <div className="space-y-4">
          <h4 className="text-lg font-bold text-gray-900">Scenarios Comparison</h4>

          {['no_prepayment', 'uniform', 'optimized'].map((key) => {
            const scenario = scenarios[key];
            return (
              <div key={key} className="bg-white rounded-lg p-4 border-2 border-gray-200">
                <h5 className="font-bold text-gray-900 mb-1">{scenario.name}</h5>
                <p className="text-xs text-gray-600 mb-3">{scenario.description}</p>

                <div className="grid grid-cols-3 gap-2 mb-3">
                  <div className="text-center">
                    <div className="text-xs text-gray-500">Total Interest</div>
                    <div className="text-sm font-bold text-red-600">{formatCurrency(scenario.total_interest)}</div>
                  </div>
                  <div className="text-center">
                    <div className="text-xs text-gray-500">Saved</div>
                    <div className="text-sm font-bold text-green-600">{formatCurrency(scenario.total_saved)}</div>
                  </div>
                  <div className="text-center">
                    <div className="text-xs text-gray-500">Tenure Reduced</div>
                    <div className="text-sm font-bold text-blue-600">{formatMonths(scenario.total_tenure_reduction_months)}</div>
                  </div>
                </div>

                <div className="space-y-2">
                  {scenario.loans.map((loan, idx) => (
                    <div key={idx} className="text-xs bg-gray-50 p-2 rounded">
                      <div className="font-medium">{loan.name}</div>
                      <div className="text-gray-600">
                        Interest: {formatCurrency(loan.interest)}
                        {loan.interest_saved > 0 && (
                          <span className="text-green-600 ml-2">
                            (Save: {formatCurrency(loan.interest_saved)})
                          </span>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
