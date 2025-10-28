// src/api/services/recurringPayments.js
import api from '../client';

/**
 * Centralized Recurring Payments API
 *
 * This service provides access to user's saved recurring financial obligations
 * across all categories (Loans, Insurance, Investments, Government Schemes)
 */

/**
 * Get all recurring payments grouped by category
 *
 * @returns {Promise<{
 *   loans: Array,
 *   insurance: Array,
 *   investments: Array,
 *   government_schemes: Array
 * }>}
 */
export const getAllRecurringPayments = async () => {
  try {
    const response = await api.get('/salary-sweep/recurring-payments');
    return response.data;
  } catch (error) {
    console.error('Failed to fetch recurring payments:', error);
    throw error;
  }
};

/**
 * Get only loan EMIs (for Loan Optimizer)
 *
 * @returns {Promise<Array>} Array of loan EMI patterns
 */
export const getLoans = async () => {
  const { loans } = await getAllRecurringPayments();
  return loans;
};

/**
 * Get only insurance payments (for Insurance Tracker)
 *
 * @returns {Promise<Array>} Array of insurance patterns
 */
export const getInsurance = async () => {
  const { insurance } = await getAllRecurringPayments();
  return insurance;
};

/**
 * Get only investments (for Investment Dashboard)
 *
 * @returns {Promise<Array>} Array of investment patterns
 */
export const getInvestments = async () => {
  const { investments } = await getAllRecurringPayments();
  return investments;
};

/**
 * Get only government schemes (for Pension/Schemes Tracker)
 *
 * @returns {Promise<Array>} Array of government scheme patterns
 */
export const getGovernmentSchemes = async () => {
  const { government_schemes } = await getAllRecurringPayments();
  return government_schemes;
};

/**
 * Transform recurring payment to loan format
 * Adds placeholders for loan-specific fields that need user input
 *
 * @param {Object} emiPattern - EMI pattern from recurring payments
 * @returns {Object} Loan object with EMI + additional fields
 */
export const transformToLoan = (emiPattern) => {
  return {
    // From recurring payments
    id: emiPattern.pattern_id,
    name: emiPattern.user_label || emiPattern.merchant_source,
    merchantSource: emiPattern.merchant_source,
    monthlyEMI: emiPattern.emi_amount,
    category: emiPattern.category,
    subcategory: emiPattern.subcategory,
    occurrenceCount: emiPattern.occurrence_count,
    firstDate: emiPattern.first_detected_date,
    lastDate: emiPattern.last_detected_date,

    // Loan-specific fields (to be filled by user)
    principalAmount: null,        // User needs to enter
    interestRate: null,           // User needs to enter
    loanTenure: null,             // User needs to enter
    remainingTenure: null,        // User needs to enter
    outstandingBalance: null,     // Can be calculated or entered
    loanType: emiPattern.subcategory || 'Other', // Pre-filled from category
  };
};

/**
 * Transform recurring payment to investment format
 *
 * @param {Object} emiPattern - EMI pattern from recurring payments
 * @returns {Object} Investment object
 */
export const transformToInvestment = (emiPattern) => {
  return {
    id: emiPattern.pattern_id,
    name: emiPattern.user_label || emiPattern.merchant_source,
    monthlyAmount: emiPattern.emi_amount,
    category: emiPattern.subcategory,
    startDate: emiPattern.first_detected_date,
    totalInvested: emiPattern.emi_amount * emiPattern.occurrence_count, // Estimated

    // Investment-specific fields (to be filled)
    currentValue: null,
    returns: null,
    assetClass: 'Mutual Fund', // Default
  };
};

/**
 * Transform recurring payment to insurance format
 *
 * @param {Object} emiPattern - EMI pattern from recurring payments
 * @returns {Object} Insurance object
 */
export const transformToInsurance = (emiPattern) => {
  return {
    id: emiPattern.pattern_id,
    policyName: emiPattern.user_label || emiPattern.merchant_source,
    premium: emiPattern.emi_amount,
    type: emiPattern.subcategory || 'Insurance',
    startDate: emiPattern.first_detected_date,

    // Insurance-specific fields (to be filled)
    sumAssured: null,
    policyNumber: null,
    maturityDate: null,
  };
};

export default {
  getAllRecurringPayments,
  getLoans,
  getInsurance,
  getInvestments,
  getGovernmentSchemes,
  transformToLoan,
  transformToInvestment,
  transformToInsurance
};
