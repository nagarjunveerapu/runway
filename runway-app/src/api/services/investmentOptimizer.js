// src/api/services/investmentOptimizer.js
import api from '../client';

/**
 * Investment Optimizer API Services
 */

/**
 * Get complete investment analysis
 */
export async function analyzeInvestments() {
  const response = await api.get('/investment-optimizer/analyze');
  return response.data;
}

/**
 * Get detected SIP patterns
 */
export async function getSIPs() {
  const response = await api.get('/investment-optimizer/sips');
  return response.data;
}

/**
 * Get portfolio allocation breakdown
 */
export async function getPortfolioAllocation() {
  const response = await api.get('/investment-optimizer/portfolio');
  return response.data;
}

