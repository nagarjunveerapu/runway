/**
 * Dashboard API Service
 *
 * Provides comprehensive financial dashboard data including:
 * - Financial health score
 * - Monthly metrics and trends
 * - Asset summary
 * - Personalized insights
 */

import api from '../client';

/**
 * Get comprehensive dashboard summary
 *
 * @returns {Promise} Dashboard summary with health score, metrics, assets, and insights
 */
export const getDashboardSummary = async () => {
  const response = await api.get('/dashboard/summary');
  return response.data;
};

/**
 * Get monthly trends for specified number of months
 *
 * @param {number} months - Number of months to include (default: 6)
 * @returns {Promise} Monthly trend data with income, expenses, savings
 */
export const getMonthlyTrends = async (months = 6) => {
  const response = await api.get('/analytics/trends', {
    params: { months }
  });
  return response.data;
};

/**
 * Detect potential assets from EMI patterns
 *
 * @returns {Promise} Detected assets with confidence scores
 */
export const detectAssetsFromEMIs = async () => {
  const response = await api.get('/assets/detect-from-emis');
  return response.data;
};

export default {
  getDashboardSummary,
  getMonthlyTrends,
  detectAssetsFromEMIs
};
