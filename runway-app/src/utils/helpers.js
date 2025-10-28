import { parseMonth } from './dateParser';

export function formatMonth(dateStr) {
  return parseMonth(dateStr);
}
export function classifyTransaction(txn, lookups){ if (txn.user_forced_type) return txn.user_forced_type; const cat = (txn.category||"").toLowerCase(); if (cat.startsWith("investments-")) return "investment"; if (cat.startsWith("emi-")) return "expense"; if (lookups && lookups.incomeCategories && lookups.incomeCategories.map(x=>x.toLowerCase()).includes(cat)) return "income"; if (lookups && lookups.expenseCategories && lookups.expenseCategories.map(x=>x.toLowerCase()).includes(cat)) return "expense"; return "expense"; }
