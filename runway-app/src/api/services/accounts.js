import api from '../client';

/**
 * Account API services
 */

export const getAccounts = async () => {
  const response = await api.get('/accounts');
  return response.data;
};

export const createAccount = async (accountData) => {
  const response = await api.post('/accounts', accountData);
  return response.data;
};

export const deleteAccount = async (accountId) => {
  await api.delete(`/accounts/${accountId}`);
};

export const resetAccountData = async (accountId) => {
  const response = await api.delete(`/accounts/${accountId}/data`);
  return response.data;
};

export default {
  getAccounts,
  createAccount,
  deleteAccount,
  resetAccountData,
};

