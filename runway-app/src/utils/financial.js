// src/utils/financial.js
export function formatMonth(dateStr){
  if(!dateStr) return '';
  const d = new Date(dateStr);
  if (isNaN(d)) {
    // fallback if already YYYY-MM-DD or YYYY-MM
    return dateStr.slice(0,7);
  }
  const y = d.getFullYear();
  const m = String(d.getMonth()+1).padStart(2,'0');
  return `${y}-${m}`;
}

/**
 * trailingAverages(transactions, months=3)
 * returns { avgIncome, avgOutflow, avgNet }
 */
export function trailingAverages(transactions = [], months = 3){
  if(!transactions || transactions.length===0) return { avgIncome:0, avgOutflow:0, avgNet:0 };
  const map = {};
  for(const t of transactions){
    const m = t.month || formatMonth(t.date) || 'unknown';
    if(!map[m]) map[m] = { income:0, outflow:0 };
    const amt = Number(t.amount || 0);
    if(t.type === 'income') map[m].income += amt;
    else if(t.type === 'investment'){
      // by default treat investments as outflow (user can toggle)
      map[m].outflow += amt;
    } else map[m].outflow += amt;
  }
  const monthsSorted = Object.keys(map).sort().slice(-months);
  if(monthsSorted.length===0) return { avgIncome:0, avgOutflow:0, avgNet:0 };
  const sums = monthsSorted.reduce((acc,m)=>{
    acc.income += map[m].income||0;
    acc.outflow += map[m].outflow||0;
    return acc;
  }, { income:0, outflow:0 });
  const avgIncome = Math.round(sums.income / monthsSorted.length);
  const avgOutflow = Math.round(sums.outflow / monthsSorted.length);
  const avgNet = avgIncome - avgOutflow;
  return { avgIncome, avgOutflow, avgNet };
}

/**
 * totalLiquidAssets(assets)
 * Return total of assets considered liquid
 */
export function totalLiquidAssets(assets = []){
  if(!assets || assets.length===0) return 0;
  return assets
    .filter(a => !a.disposed && (a.liquid || ['Bank Account','Mutual Fund','Stock','Gold','Crypto'].includes(a.type) || !!a.liquid))
    .reduce((s,a) => s + Number(a.current_value || a.purchase_value || 0), 0);
}

/**
 * computeRunway({ liquidAssets, avgNetOutflow })
 * returns { months, status } where status is 'UNKNOWN'|'GREEN'|'RED'
 */
export function computeRunway({ liquidAssets = 0, avgNetOutflow = 0, minMonths = 6 }){
  // if not enough info
  if(typeof avgNetOutflow !== 'number') return { months: null, status: 'UNKNOWN', message: 'Insufficient data' };
  // if avgNetOutflow >=0, positive net => runway infinite in theory (liquid grows)
  if(avgNetOutflow >= 0){
    return { months: Infinity, status: 'GREEN', message: 'You are generating surplus. Consider investing excess or raising goals.' };
  }
  const monthlyBurn = Math.abs(avgNetOutflow);
  if(monthlyBurn === 0) return { months: null, status: 'UNKNOWN', message: 'Not enough transaction history to compute runway.' };
  const months = liquidAssets / monthlyBurn;
  const status = months >= minMonths ? 'GREEN' : 'RED';
  const message = status === 'GREEN' ? 'You are on track.' : 'Reduce outflows or increase income to extend runway.';
  return { months, status, message };
}