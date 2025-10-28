/**
 * API Services Index
 *
 * Central export point for all API service modules
 */

export * from './transactions';
export * from './assets';
export * from './liquidations';
export * from './analytics';
export * from './fire';
export { getDashboardSummary, getMonthlyTrends, detectAssetsFromEMIs } from './dashboard';

