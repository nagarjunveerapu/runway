/**
 * FIRE Calculator API Service
 * Financial Independence, Retire Early (FIRE) calculations
 */

import api from '../client';

/**
 * Get FIRE runway calculations
 * @returns {Promise<Object>} FIRE metrics including months to FIRE, target corpus, etc.
 */
export const getFIREMetrics = async () => {
  try {
    const response = await api.get('/fire/runway');
    return response.data;
  } catch (error) {
    console.error('Error fetching FIRE metrics:', error);
    throw error;
  }
};

export default {
  getFIREMetrics
};

