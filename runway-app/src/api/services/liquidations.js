/**
 * Liquidation API Service
 * 
 * Provides functions to interact with liquidation-related endpoints
 * Note: Currently liquidations are stored in localStorage (via AppContext)
 * This service provides a consistent API interface for future backend integration
 */

import api from '../client';

/**
 * Get all liquidations
 * @returns {Promise<Array>} Array of liquidations
 */
export const getLiquidations = async () => {
  try {
    const response = await api.get('/liquidations');
    return response.data;
  } catch (error) {
    console.error('Error fetching liquidations:', error);
    throw error;
  }
};

/**
 * Get a single liquidation by ID
 * @param {string} id - Liquidation ID
 * @returns {Promise<Object>} Liquidation object
 */
export const getLiquidation = async (id) => {
  try {
    const response = await api.get(`/liquidations/${id}`);
    return response.data;
  } catch (error) {
    console.error(`Error fetching liquidation ${id}:`, error);
    throw error;
  }
};

/**
 * Create a new liquidation event
 * @param {Object} data - Liquidation data
 * @param {string} data.asset_id - Asset ID being liquidated
 * @param {string} data.date - Liquidation date (YYYY-MM-DD)
 * @param {number} data.gross_proceeds - Gross proceeds
 * @param {number} data.fees - Fees
 * @param {number} data.quantity_sold - Quantity sold
 * @param {string} data.notes - Notes
 * @returns {Promise<Object>} Created liquidation
 */
export const createLiquidation = async (data) => {
  try {
    const response = await api.post('/liquidations', data);
    return response.data;
  } catch (error) {
    console.error('Error creating liquidation:', error);
    throw error;
  }
};

/**
 * Delete a liquidation
 * @param {string} id - Liquidation ID
 * @returns {Promise<void>}
 */
export const deleteLiquidation = async (id) => {
  try {
    await api.delete(`/liquidations/${id}`);
  } catch (error) {
    console.error(`Error deleting liquidation ${id}:`, error);
    throw error;
  }
};

