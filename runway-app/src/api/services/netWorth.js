// src/api/services/netWorth.js
import api from '../client';

/**
 * Net Worth Timeline API Service
 * Fetches historical net worth data for visualization
 */

/**
 * Get net worth timeline data (static snapshots)
 * @param {number} months - Number of months to fetch (default: 12)
 * @returns {Promise} Timeline data with assets, liabilities, net_worth per month
 */
export const getNetWorthTimeline = async (months = 12) => {
  try {
    const response = await api.get('/net-worth/timeline', {
      params: { months }
    });
    return response.data;
  } catch (error) {
    console.error('Failed to fetch net worth timeline:', error);
    throw error;
  }
};

/**
 * Get DYNAMIC net worth timeline (calculates EMI reductions, SIP growth)
 * @param {number} months - Number of months to calculate
 * @param {boolean} projection - If true, projects into future
 * @returns {Promise} Dynamic timeline with crossover point
 */
export const getNetWorthTimelineDynamic = async (months = 12, projection = false) => {
  try {
    const response = await api.get('/net-worth/timeline/dynamic', {
      params: { months, projection }
    });
    return response.data;
  } catch (error) {
    console.error('Failed to fetch dynamic net worth timeline:', error);
    throw error;
  }
};

/**
 * Get future net worth projection
 * @param {number} years - Number of years to project (default: 5)
 * @returns {Promise} Projection data with loan payoff schedule
 */
export const getNetWorthProjection = async (years = 5) => {
  try {
    const response = await api.get('/net-worth/projection', {
      params: { years }
    });
    return response.data;
  } catch (error) {
    console.error('Failed to fetch net worth projection:', error);
    throw error;
  }
};

/**
 * Get current net worth summary
 * @returns {Promise} Current net worth breakdown
 */
export const getCurrentNetWorth = async () => {
  try {
    const response = await api.get('/net-worth/current');
    return response.data;
  } catch (error) {
    console.error('Failed to fetch current net worth:', error);
    throw error;
  }
};

/**
 * Trigger manual net worth snapshot
 * @returns {Promise} Snapshot confirmation
 */
export const createNetWorthSnapshot = async () => {
  try {
    const response = await api.post('/net-worth/snapshot');
    return response.data;
  } catch (error) {
    console.error('Failed to create net worth snapshot:', error);
    throw error;
  }
};
