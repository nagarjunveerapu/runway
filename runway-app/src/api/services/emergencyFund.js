import apiClient from '../client';

/**
 * Emergency Fund Health Check API
 */

export const getEmergencyFundHealth = async () => {
  try {
    const response = await apiClient.get('/emergency-fund/emergency-fund');
    return response.data;
  } catch (error) {
    console.error('Error fetching emergency fund health:', error);
    throw error;
  }
};

export default {
  getEmergencyFundHealth,
};
