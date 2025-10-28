/**
 * Asset API Service
 * 
 * Provides functions to interact with asset-related endpoints
 * Note: Currently assets are stored in localStorage (via AppContext)
 * This service provides a consistent API interface for future backend integration
 */

import api from '../client';

/**
 * Get all assets
 * @returns {Promise<Array>} Array of assets
 */
export const getAssets = async () => {
  try {
    // For now, assets are in localStorage via AppContext
    // TODO: Replace with backend API call when asset endpoints are available
    const response = await api.get('/assets');
    return response.data;
  } catch (error) {
    console.error('Error fetching assets:', error);
    throw error;
  }
};

/**
 * Get a single asset by ID
 * @param {string} id - Asset ID
 * @returns {Promise<Object>} Asset object
 */
export const getAsset = async (id) => {
  try {
    const response = await api.get(`/assets/${id}`);
    return response.data;
  } catch (error) {
    console.error(`Error fetching asset ${id}:`, error);
    throw error;
  }
};

/**
 * Create a new asset
 * @param {Object} data - Asset data
 * @param {string} data.name - Asset name
 * @param {string} data.type - Asset type
 * @param {number} data.quantity - Quantity
 * @param {number} data.purchase_value - Purchase value
 * @param {number} data.current_value - Current value
 * @param {boolean} data.liquid - Is liquid asset
 * @returns {Promise<Object>} Created asset
 */
export const createAsset = async (data) => {
  try {
    const response = await api.post('/assets', data);
    return response.data;
  } catch (error) {
    console.error('Error creating asset:', error);
    throw error;
  }
};

/**
 * Update an existing asset
 * @param {string} id - Asset ID
 * @param {Object} data - Update data
 * @returns {Promise<Object>} Updated asset
 */
export const updateAsset = async (id, data) => {
  try {
    const response = await api.patch(`/assets/${id}`, data);
    return response.data;
  } catch (error) {
    console.error(`Error updating asset ${id}:`, error);
    throw error;
  }
};

/**
 * Delete an asset
 * @param {string} id - Asset ID
 * @returns {Promise<void>}
 */
export const deleteAsset = async (id) => {
  try {
    await api.delete(`/assets/${id}`);
  } catch (error) {
    console.error(`Error deleting asset ${id}:`, error);
    throw error;
  }
};

