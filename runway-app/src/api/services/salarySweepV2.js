/**
 * Salary Sweep Optimizer API Service V2
 *
 * With database persistence and smart EMI management
 */

import api from '../client';

/**
 * Get saved configuration (if exists)
 */
export const getSavedConfig = async () => {
  const response = await api.get('/salary-sweep/config');
  return response.data;
};

/**
 * Detect patterns or refresh existing with smart suggestions
 */
export const detectOrRefreshPatterns = async () => {
  const response = await api.post('/salary-sweep/detect');
  return response.data;
};

/**
 * Confirm and save configuration with selected EMIs
 */
export const confirmConfig = async (configData) => {
  const response = await api.post('/salary-sweep/confirm', {
    salary_source: configData.salarySource,
    salary_amount: configData.salaryAmount,
    emi_pattern_ids: configData.emiPatternIds,
    salary_account_rate: configData.salaryAccountRate,
    savings_account_rate: configData.savingsAccountRate
  });
  return response.data;
};

/**
 * Calculate optimization and save results
 */
export const calculateOptimization = async () => {
  const response = await api.post('/salary-sweep/calculate');
  return response.data;
};

/**
 * Update an EMI pattern
 */
export const updateEMI = async (patternId, updates) => {
  const response = await api.patch(`/salary-sweep/emi/${patternId}`, {
    pattern_id: patternId,
    user_label: updates.userLabel,
    emi_amount: updates.emiAmount
  });
  return response.data;
};

/**
 * Delete an EMI pattern
 */
export const deleteEMI = async (patternId) => {
  await api.delete(`/salary-sweep/emi/${patternId}`);
};

/**
 * Delete entire configuration (start fresh)
 */
export const resetConfig = async () => {
  await api.delete('/salary-sweep/config');
};

export default {
  getSavedConfig,
  detectOrRefreshPatterns,
  confirmConfig,
  calculateOptimization,
  updateEMI,
  deleteEMI,
  resetConfig
};
