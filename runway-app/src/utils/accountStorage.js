/**
 * Account LocalStorage Management
 * 
 * Stores account metadata in localStorage for quick access
 */

const ACCOUNTS_STORAGE_KEY = 'runway_accounts_v1';

export const accountStorage = {
  /**
   * Get all accounts from localStorage
   */
  getAccounts: () => {
    try {
      const raw = localStorage.getItem(ACCOUNTS_STORAGE_KEY);
      return raw ? JSON.parse(raw) : [];
    } catch (e) {
      console.error('Error reading accounts from localStorage:', e);
      return [];
    }
  },

  /**
   * Save accounts to localStorage
   */
  setAccounts: (accounts) => {
    try {
      localStorage.setItem(ACCOUNTS_STORAGE_KEY, JSON.stringify(accounts));
    } catch (e) {
      console.error('Error saving accounts to localStorage:', e);
    }
  },

  /**
   * Get a specific account by ID
   */
  getAccount: (accountId) => {
    const accounts = accountStorage.getAccounts();
    return accounts.find(a => a.account_id === accountId);
  },

  /**
   * Add or update an account
   */
  upsertAccount: (account) => {
    const accounts = accountStorage.getAccounts();
    const index = accounts.findIndex(a => a.account_id === account.account_id);
    
    if (index >= 0) {
      accounts[index] = account;
    } else {
      accounts.push(account);
    }
    
    accountStorage.setAccounts(accounts);
    return account;
  },

  /**
   * Remove an account
   */
  removeAccount: (accountId) => {
    const accounts = accountStorage.getAccounts();
    const filtered = accounts.filter(a => a.account_id !== accountId);
    accountStorage.setAccounts(filtered);
  },

  /**
   * Set default account if none exists
   */
  getOrCreateDefault: (user_id) => {
    const accounts = accountStorage.getAccounts();
    
    if (accounts.length === 0) {
      const defaultAccount = {
        account_id: 'default-' + user_id,
        user_id,
        account_type: 'current',
        bank_name: 'Primary Account',
        nickname: 'My Bank Account',
        last_sync: new Date().toISOString()
      };
      accountStorage.upsertAccount(defaultAccount);
      return defaultAccount;
    }
    
    return accounts[0];
  }
};

export default accountStorage;

