// src/testdata/loadSampleData.js
import sample from './sampleData.json';

// These keys must match the ones used in your AppContext
const KEYS = {
  transactions: 'pf_transactions_v1',
  lookups: 'pf_lookups_v1',
  assets: 'pf_assets_v1',
  liquidations: 'pf_liquidations_v1'
};

export function loadSampleData({ force = false } = {}) {
  try {
    // only load in development by default
    if (process.env.NODE_ENV !== 'development' && !force) {
      console.log('loadSampleData: skipping (not dev env)');
      return;
    }

    // if any key exists and force is false, skip (don't override user data)
    const anyExists = Object.values(KEYS).some(k => localStorage.getItem(k));
    if (anyExists && !force) {
      console.log('loadSampleData: data already present in localStorage; skipping.');
      return;
    }

    // Transform transactions: map user_forced_type to type, and add month field
    const transformedTransactions = (sample.transactions || []).map(t => ({
      ...t,
      type: t.user_forced_type || t.type,
      month: t.month || (t.date ? t.date.slice(0, 7) : ''),
    }));

    // write each piece to the correct key
    localStorage.setItem(KEYS.transactions, JSON.stringify(transformedTransactions));
    localStorage.setItem(KEYS.lookups, JSON.stringify(sample.lookups || {}));
    localStorage.setItem(KEYS.assets, JSON.stringify(sample.assets || []));
    localStorage.setItem(KEYS.liquidations, JSON.stringify(sample.liquidations || []));
    console.log('loadSampleData: sample data written to localStorage.', transformedTransactions.length, 'transactions');
  } catch (err) {
    console.error('loadSampleData error', err);
  }
}