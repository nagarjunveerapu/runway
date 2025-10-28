/**
 * Loan Prepayment Optimizer API Service
 */

import api from '../client';

/**
 * Detect recurring loan/EMI patterns
 */
export const detectLoanPatterns = async () => {
  const response = await api.post('/loan-prepayment/detect');
  return response.data;
};

/**
 * Calculate prepayment optimization with different scenarios
 */
export const calculatePrepaymentOptimization = async (data) => {
  const response = await api.post('/loan-prepayment/calculate', data);
  return response.data;
};

export default {
  detectLoanPatterns,
  calculatePrepaymentOptimization
};
