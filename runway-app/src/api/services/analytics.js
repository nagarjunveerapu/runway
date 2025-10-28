/**
 * Analytics API Service
 * 
 * Provides functions to fetch analytics and insights
 */

import api from '../client';

/**
 * Get summary statistics
 * @param {Object} params - Query parameters
 * @param {string} params.start_date - Start date (YYYY-MM-DD)
 * @param {string} params.end_date - End date (YYYY-MM-DD)
 * @returns {Promise<Object>} Summary statistics
 */
export const getSummary = async (params = {}) => {
  try {
    const queryParams = new URLSearchParams();
    if (params.start_date) queryParams.append('start_date', params.start_date);
    if (params.end_date) queryParams.append('end_date', params.end_date);
    
    const response = await api.get(`/analytics/summary?${queryParams.toString()}`);
    return response.data;
  } catch (error) {
    console.error('Error fetching summary:', error);
    throw error;
  }
};

/**
 * Get top merchants by spending
 * @param {Object} params - Query parameters
 * @param {string} params.start_date - Start date (YYYY-MM-DD)
 * @param {string} params.end_date - End date (YYYY-MM-DD)
 * @param {number} params.limit - Number of merchants to return (default: 10)
 * @returns {Promise<Array>} Array of top merchants
 */
export const getTopMerchants = async (params = {}) => {
  try {
    const queryParams = new URLSearchParams();
    if (params.start_date) queryParams.append('start_date', params.start_date);
    if (params.end_date) queryParams.append('end_date', params.end_date);
    if (params.limit) queryParams.append('limit', params.limit);
    
    const response = await api.get(`/analytics/top-merchants?${queryParams.toString()}`);
    return response.data;
  } catch (error) {
    console.error('Error fetching top merchants:', error);
    throw error;
  }
};

/**
 * Get category trends over time
 * @param {Object} params - Query parameters
 * @param {string} params.start_date - Start date (YYYY-MM-DD)
 * @param {string} params.end_date - End date (YYYY-MM-DD)
 * @param {string} params.group_by - Grouping (day/week/month, default: month)
 * @returns {Promise<Array>} Array of category trends
 */
export const getCategoryTrends = async (params = {}) => {
  try {
    const queryParams = new URLSearchParams();
    if (params.start_date) queryParams.append('start_date', params.start_date);
    if (params.end_date) queryParams.append('end_date', params.end_date);
    if (params.group_by) queryParams.append('group_by', params.group_by);
    
    const response = await api.get(`/analytics/category-trends?${queryParams.toString()}`);
    return response.data;
  } catch (error) {
    console.error('Error fetching category trends:', error);
    throw error;
  }
};

/**
 * Get category breakdown
 * @param {Object} params - Query parameters
 * @param {string} params.start_date - Start date (YYYY-MM-DD)
 * @param {string} params.end_date - End date (YYYY-MM-DD)
 * @returns {Promise<Array>} Array of category breakdowns
 */
export const getCategoryBreakdown = async (params = {}) => {
  try {
    const queryParams = new URLSearchParams();
    if (params.start_date) queryParams.append('start_date', params.start_date);
    if (params.end_date) queryParams.append('end_date', params.end_date);
    
    const response = await api.get(`/analytics/categories?${queryParams.toString()}`);
    return response.data;
  } catch (error) {
    console.error('Error fetching category breakdown:', error);
    throw error;
  }
};

