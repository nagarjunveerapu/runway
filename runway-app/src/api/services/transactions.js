/**
 * Transaction API Service
 * 
 * Provides functions to interact with transaction-related endpoints
 */

import api from '../client';

/**
 * Get paginated list of transactions with optional filters
 * @param {Object} filters - Query parameters
 * @param {number} filters.page - Page number (default: 1)
 * @param {number} filters.page_size - Items per page (default: 50)
 * @param {string} filters.start_date - Start date (YYYY-MM-DD)
 * @param {string} filters.end_date - End date (YYYY-MM-DD)
 * @param {string} filters.category - Filter by category
 * @param {number} filters.min_amount - Minimum amount
 * @param {number} filters.max_amount - Maximum amount
 * @returns {Promise<Object>} Response with transactions and metadata
 */
export const getTransactions = async (filters = {}) => {
  try {
    const params = new URLSearchParams();
    
    // Add pagination
    if (filters.page) params.append('page', filters.page);
    if (filters.page_size) params.append('page_size', filters.page_size);
    
    // Add date filters
    if (filters.start_date) params.append('start_date', filters.start_date);
    if (filters.end_date) params.append('end_date', filters.end_date);
    
    // Add other filters
    if (filters.category) params.append('category', filters.category);
    if (filters.min_amount !== undefined) params.append('min_amount', filters.min_amount);
    if (filters.max_amount !== undefined) params.append('max_amount', filters.max_amount);
    
    const response = await api.get(`/transactions?${params.toString()}`);
    return response.data;
  } catch (error) {
    console.error('Error fetching transactions:', error);
    throw error;
  }
};

/**
 * Get a single transaction by ID
 * @param {string} id - Transaction ID
 * @returns {Promise<Object>} Transaction object
 */
export const getTransaction = async (id) => {
  try {
    const response = await api.get(`/transactions/${id}`);
    return response.data;
  } catch (error) {
    console.error(`Error fetching transaction ${id}:`, error);
    throw error;
  }
};

/**
 * Create a new transaction
 * @param {Object} data - Transaction data
 * @param {string} data.date - Transaction date (YYYY-MM-DD)
 * @param {number} data.amount - Amount (must be positive)
 * @param {string} data.type - Transaction type (debit/credit)
 * @param {string} data.description_raw - Description
 * @param {string} data.merchant_canonical - Canonical merchant name
 * @param {string} data.category - Category
 * @param {Object} data.account_id - Account ID (optional)
 * @returns {Promise<Object>} Created transaction
 */
export const createTransaction = async (data) => {
  try {
    const response = await api.post('/transactions', data);
    return response.data;
  } catch (error) {
    console.error('Error creating transaction:', error);
    throw error;
  }
};

/**
 * Update an existing transaction
 * @param {string} id - Transaction ID
 * @param {Object} data - Update data
 * @param {string} data.category - New category (optional)
 * @param {string} data.merchant_canonical - New merchant (optional)
 * @returns {Promise<Object>} Updated transaction
 */
export const updateTransaction = async (id, data) => {
  try {
    const response = await api.patch(`/transactions/${id}`, data);
    return response.data;
  } catch (error) {
    console.error(`Error updating transaction ${id}:`, error);
    throw error;
  }
};

/**
 * Delete a transaction
 * @param {string} id - Transaction ID
 * @returns {Promise<void>}
 */
export const deleteTransaction = async (id) => {
  try {
    await api.delete(`/transactions/${id}`);
  } catch (error) {
    console.error(`Error deleting transaction ${id}:`, error);
    throw error;
  }
};

/**
 * Categorize a transaction using ML
 * @param {Object} data - Transaction data to categorize
 * @param {string} data.description - Transaction description
 * @param {string} data.merchant - Merchant name (optional)
 * @returns {Promise<Object>} Category prediction with confidence
 */
export const categorizeTransaction = async (data) => {
  try {
    const response = await api.post('/ml/categorize', data);
    return response.data;
  } catch (error) {
    console.error('Error categorizing transaction:', error);
    throw error;
  }
};

/**
 * Batch categorize multiple transactions
 * @param {Array<Object>} transactions - Array of transactions to categorize
 * @returns {Promise<Object>} Results with categories for each transaction
 */
export const batchCategorizeTransactions = async (transactions) => {
  try {
    const response = await api.post('/ml/categorize-batch', { transactions });
    return response.data;
  } catch (error) {
    console.error('Error batch categorizing transactions:', error);
    throw error;
  }
};

/**
 * Re-categorize all transactions based on detected patterns (salary, EMI, etc.)
 * @returns {Promise<Object>} Result with patterns detected and transactions updated
 */
export const recategorizeTransactions = async () => {
  try {
    const response = await api.post('/transactions/re-categorize');
    return response.data;
  } catch (error) {
    console.error('Error re-categorizing transactions:', error);
    throw error;
  }
};

