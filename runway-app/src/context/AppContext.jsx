// src/context/AppContext.jsx
import React, { createContext, useContext, useState, useEffect, useCallback, useMemo } from 'react';
import { useAuth } from './AuthContext';
import * as transactionServices from '../api/services/transactions';
import * as assetServices from '../api/services/assets';
import * as liquidationServices from '../api/services/liquidations';
import { DEFAULT_LOOKUPS } from '../lookups.js';
import { formatMonth, classifyTransaction } from '../utils/helpers';

const AppContext = createContext(null);

export function useApp() {
  return useContext(AppContext);
}

export function AppProvider({ children }) {
  const { isAuthenticated } = useAuth();
  
  // State management
  const [transactions, setTransactions] = useState([]);
  const [assets, setAssets] = useState([]);
  const [liquidations, setLiquidations] = useState([]);
  const [lookups, setLookups] = useState(() => {
    try {
      const raw = localStorage.getItem('pf_lookups_v1');
      return raw ? JSON.parse(raw) : DEFAULT_LOOKUPS;
    } catch (e) {
      return DEFAULT_LOOKUPS;
    }
  });
  
  // Loading and error states
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);

  // Fetch transactions from API - Optimized with pagination
  const fetchTransactions = useCallback(async () => {
    if (!isAuthenticated) return;
    
    setIsLoading(true);
    setError(null);
    try {
      // Get all transactions for dashboard calculations
      const response = await transactionServices.getTransactions({
        page: 1,
        page_size: 1000,  // Get enough data for accurate dashboard
        sort_by: 'date',
        sort_order: 'desc'
      });
      // Transform backend format to frontend format
      const transformed = response.transactions.map(t => ({
        ...t,
        id: t.transaction_id,
        type: t.type || 'debit',
        month: t.month || (t.date ? formatMonth(t.date) : '')
      }));
      setTransactions(transformed);
    } catch (err) {
      console.error('Error fetching transactions:', err);
      setError('Failed to load transactions');
    } finally {
      setIsLoading(false);
    }
  }, [isAuthenticated]);

  // Fetch assets from API
  const fetchAssets = useCallback(async () => {
    if (!isAuthenticated) return;
    
    setIsLoading(true);
    setError(null);
    try {
      const response = await assetServices.getAssets();
      // Transform backend format to frontend format
      const transformed = response.map(a => ({
        ...a,
        id: a.asset_id,
        type: a.asset_type,
        purchase_value: a.purchase_price || a.purchase_value // Map purchase_price to purchase_value for frontend
      }));
      setAssets(transformed);
    } catch (err) {
      console.error('Error fetching assets:', err);
      setError('Failed to load assets');
    } finally {
      setIsLoading(false);
    }
  }, [isAuthenticated]);

  // Fetch liquidations from API
  const fetchLiquidations = useCallback(async () => {
    if (!isAuthenticated) return;
    
    setIsLoading(true);
    setError(null);
    try {
      const response = await liquidationServices.getLiquidations();
      // Transform backend format to frontend format
      const transformed = response.map(l => ({
        ...l,
        id: l.liquidation_id
      }));
      setLiquidations(transformed);
    } catch (err) {
      console.error('Error fetching liquidations:', err);
      setError('Failed to load liquidations');
    } finally {
      setIsLoading(false);
    }
  }, [isAuthenticated]);

  // Load data on mount and when authenticated
  // Load data in parallel for faster initial load
  useEffect(() => {
    if (isAuthenticated) {
      // Use Promise.all to fetch in parallel
      Promise.all([
        fetchTransactions(),
        fetchAssets(),
        fetchLiquidations()
      ]).catch(err => {
        console.error('Error loading data:', err);
        setError('Failed to load some data');
      });
    }
  }, [isAuthenticated, fetchTransactions, fetchAssets, fetchLiquidations]);

  // Transform transactions to ensure 'type' field exists
  const transformedTransactions = useMemo(() => {
    return (transactions || []).map(t => ({
      ...t,
      type: t.user_forced_type || t.type || classifyTransaction(t, lookups)
    }));
  }, [transactions, lookups]);

  // Helper function to add transaction (with optimistic update)
  const addTransaction = useCallback(async (tx) => {
    if (!isAuthenticated) {
      setError('You must be logged in to add transactions');
      return null;
    }

    try {
      setError(null);
      
      // Optimistic update
      const tempId = `temp_${Date.now()}`;
      const tempTransaction = {
        ...tx,
        id: tempId,
        transaction_id: tempId,
        month: tx.month || (tx.date ? formatMonth(tx.date) : ''),
        amount: Number(tx.amount || 0),
        type: tx.type || classifyTransaction(tx, lookups),
        user_forced_type: tx.type
      };
      setTransactions(prev => [tempTransaction, ...prev]);

      // Call API
      const response = await transactionServices.createTransaction({
        date: tx.date,
        amount: Math.abs(Number(tx.amount || 0)),
        type: tx.type === 'income' ? 'credit' : 'debit',
        description_raw: tx.description_raw || tx.notes || '',
        merchant_canonical: tx.merchant_canonical,
        category: tx.category || 'Other',
        month: tx.month || formatMonth(tx.date),
        linked_asset_id: tx.linked_asset_id,
        liquidation_event_id: tx.liquidation_event_id
      });

      // Replace temp with real transaction
      setTransactions(prev => {
        const filtered = prev.filter(t => t.id !== tempId);
        return [{
          ...response,
          id: response.transaction_id,
          type: response.type || 'debit',
          month: response.month || formatMonth(response.date)
        }, ...filtered];
      });

      return response;
    } catch (err) {
      console.error('Error adding transaction:', err);
      setError('Failed to add transaction');
      // Rollback optimistic update
      setTransactions(prev => prev.filter(t => !t.id.startsWith('temp_')));
      return null;
    }
  }, [isAuthenticated, lookups]);

  // Helper function to add asset (with optimistic update)
  const addAsset = useCallback(async (asset) => {
    if (!isAuthenticated) {
      setError('You must be logged in to add assets');
      return null;
    }

    try {
      setError(null);
      
      // Optimistic update
      const tempId = `temp_${Date.now()}`;
      const tempAsset = {
        ...asset,
        id: tempId,
        asset_id: tempId,
        created_at: new Date().toISOString()
      };
      setAssets(prev => [tempAsset, ...prev]);

      // Call API
      const response = await assetServices.createAsset({
        name: asset.name,
        asset_type: asset.type || asset.asset_type,
        quantity: asset.quantity,
        purchase_price: asset.purchase_price || asset.purchase_value,
        current_value: asset.current_value,
        purchase_date: asset.purchase_date,
        liquid: asset.liquid,
        disposed: asset.disposed,
        notes: asset.notes
      });

      // Replace temp with real asset
      setAssets(prev => {
        const filtered = prev.filter(a => a.id !== tempId);
        return [{
          ...response,
          id: response.asset_id,
          type: response.asset_type
        }, ...filtered];
      });

      return response;
    } catch (err) {
      console.error('Error adding asset:', err);
      setError('Failed to add asset');
      // Rollback optimistic update
      setAssets(prev => prev.filter(a => !a.id.startsWith('temp_')));
      return null;
    }
  }, [isAuthenticated]);

  // Helper function to record liquidation (with optimistic update)
  const recordLiquidation = useCallback(async (assetId, { date, gross_proceeds, fees, quantity_sold, notes }) => {
    if (!isAuthenticated) {
      setError('You must be logged in to record liquidations');
      return null;
    }

    try {
      setError(null);
      
      const asset = assets.find(a => a.id === assetId);
      const gross = Number(gross_proceeds || 0);
      const f = Number(fees || 0);
      const qty = Number(quantity_sold || asset?.quantity || 0);
      const net = gross - f;

      // Optimistic updates
      const tempLiquidationId = `temp_${Date.now()}`;
      const tempIncomeId = `temp_tx_${Date.now()}`;
      
      const tempLiquidation = {
        id: tempLiquidationId,
        liquidation_id: tempLiquidationId,
        asset_id: assetId,
        date,
        gross_proceeds: gross,
        fees: f,
        net_received: net,
        quantity_sold: qty,
        notes
      };
      const tempIncomeTxn = {
        id: tempIncomeId,
        transaction_id: tempIncomeId,
        date,
        category: `Liquidation: ${asset?.name || assetId}`,
        amount: net,
        type: 'income',
        month: formatMonth(date)
      };
      
      setLiquidations(prev => [tempLiquidation, ...prev]);
      setTransactions(prev => [tempIncomeTxn, ...prev]);

      // Call API
      const response = await liquidationServices.createLiquidation({
        asset_id: assetId,
        date,
        gross_proceeds: gross,
        fees: f,
        quantity_sold: qty,
        notes
      });

      // Update asset quantity
      const updatedAsset = await assetServices.updateAsset(assetId, {
        quantity: Math.max(0, (asset.quantity || 0) - qty),
        disposed: Math.max(0, (asset.quantity || 0) - qty) === 0
      });

      // Replace temp liquidation with real
      setLiquidations(prev => {
        const filtered = prev.filter(l => l.id !== tempLiquidationId);
        return [{...response, id: response.liquidation_id}, ...filtered];
      });

      // Replace temp transaction with real
      setTransactions(prev => {
        const filtered = prev.filter(t => t.id !== tempIncomeId);
        return [{
          ...tempIncomeTxn,
          liquidation_event_id: response.liquidation_id
        }, ...filtered];
      });

      // Update asset in state
      setAssets(prev => prev.map(a => a.id === assetId ? updatedAsset : a));

      return { event: response, incomeTxn: tempIncomeTxn };
    } catch (err) {
      console.error('Error recording liquidation:', err);
      setError('Failed to record liquidation');
      // Rollback optimistic updates
      setLiquidations(prev => prev.filter(l => !l.id.startsWith('temp_')));
      setTransactions(prev => prev.filter(t => !t.id.startsWith('temp_tx_')));
      return null;
    }
  }, [isAuthenticated, assets]);

  const updateLookups = useCallback((next) => {
    setLookups(next);
    localStorage.setItem('pf_lookups_v1', JSON.stringify(next));
  }, []);

  // Provide everything explicitly
  const value = {
    transactions: transformedTransactions,
    setTransactions,
    addTransaction,
    lookups,
    updateLookups,
    assets,
    setAssets,
    addAsset,
    liquidations,
    setLiquidations,
    recordLiquidation,
    isLoading,
    error,
    refetch: fetchTransactions
  };

  // Debug: print once on mount
  useEffect(() => {
    console.info('AppProvider mounted — context ready. Authenticated:', isAuthenticated);
  }, [isAuthenticated]);

  return <AppContext.Provider value={value}>{children}</AppContext.Provider>;
}
