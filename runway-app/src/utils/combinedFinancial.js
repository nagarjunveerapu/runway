// src/utils/combinedFinancial.js
// Utilities used by the Dashboard header and other UI components.
// Exports:
//  - trailingAverages(transactions, months = 3)
//  - totalLiquidAssets(assets, assetTypes = [])
//  - computeRunway({ liquidAssets, avgNetOutflow, minMonths = 6 })

/**
 * Build month key from a transaction (YYYY-MM)
 */
function txMonth(tx) {
  if (!tx) return 'unknown';
  if (tx.month) return tx.month;
  if (tx.date && typeof tx.date === 'string') {
    return tx.date.slice(0, 7);
  }
  if (tx.date instanceof Date) {
    const d = tx.date;
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`;
  }
  return 'unknown';
}

/**
 * Compute trailing averages over the last `months` months.
 *
 * transactions: array of { date, month, amount, type, category }
 * months: integer (last N months)
 *
 * returns: { avgIncome, avgOutflow, avgNet, months: [..ordered list], monthly: Map }
 */
export function trailingAverages(transactions = [], months = 3) {
  // aggregate by month
  const map = {}; // month -> { income, outflow }
  for (const t of transactions || []) {
    const m = txMonth(t);
    map[m] = map[m] || { income: 0, outflow: 0 };
    const amt = Number(t.amount || 0);
    // classify transaction: allow explicit t.type, else naive category regex
    const isIncome =
      t.type === 'income' ||
      /salary|dividend|interest|capital gains|income/i.test(t.category || '');
    const isInvestment =
      t.type === 'investment' || /invest|sip|mutual fund|mf|sip/i.test(t.category || '');
    if (isIncome) {
      map[m].income += amt;
    } else if (isInvestment) {
      // treat investments as neither income nor expense (ignore for burn)
      // you may change this if you want investments considered outflow
    } else {
      map[m].outflow += amt;
    }
  }

  // sort months chronologically
  const monthKeys = Object.keys(map).sort();
  const last = monthKeys.slice(-months);

  let iSum = 0;
  let oSum = 0;
  for (const m of last) {
    iSum += (map[m] && map[m].income) || 0;
    oSum += (map[m] && map[m].outflow) || 0;
  }
  const denom = Math.max(1, last.length);
  const avgIncome = iSum / denom;
  const avgOutflow = oSum / denom;
  const avgNet = avgIncome - avgOutflow;

  return {
    avgIncome,
    avgOutflow,
    avgNet,
    months: monthKeys,
    monthly: map
  };
}

/**
 * Sum total liquid assets.
 * Heuristic:
 *  - If asset object has boolean `liquid` use it
 *  - Else if assetTypes array is provided and contains an entry with name === asset.type
 *    and that entry has `liquid: true`, use that
 *  - Else consider typical bank/cash names as liquid.
 *
 * assets: array of { type, current_value, purchase_value, disposed?, liquid? }
 * assetTypes: optional array of { name, liquid:boolean }
 */
export function totalLiquidAssets(assets = [], assetTypes = []) {
  const banky = /bank|cash|savings|current|cash account|liquid/i;
  const typeMap = (assetTypes || []).reduce((acc, t) => {
    if (t && t.name) acc[t.name] = t;
    return acc;
  }, {});

  return (assets || [])
    .filter((a) => !!a) // guard
    .filter((a) => !a.disposed)
    .reduce((sum, a) => {
      const val = Number(a.current_value ?? a.purchase_value ?? 0);
      let isLiquid = false;
      if (a.hasOwnProperty('liquid')) {
        isLiquid = !!a.liquid;
      } else if (a.type && typeMap[a.type] && typeof typeMap[a.type].liquid !== 'undefined') {
        isLiquid = !!typeMap[a.type].liquid;
      } else if (typeof a.type === 'string' && banky.test(a.type)) {
        isLiquid = true;
      } else if (typeof a.name === 'string' && banky.test(a.name)) {
        isLiquid = true;
      }
      return sum + (isLiquid ? val : 0);
    }, 0);
}

/**
 * Compute runway and status.
 *
 * liquidAssets: number
 * avgNetOutflow: number (NOTE: this should be avgIncome - avgOutflow; we treat negative avgNet as burn)
 * minMonths: user's target months (default 6)
 *
 * returns:
 * {
 *   months: number | Infinity | null,   // months of runway (null if unknown)
 *   status: 'GREEN'|'YELLOW'|'RED'|'UNKNOWN',
 *   message: string
 * }
 */
export function computeRunway({ liquidAssets = 0, avgNetOutflow = 0, minMonths = 6 } = {}) {
  // avgNetOutflow in our calling code is avgNet (income - outflow).
  // If avgNet > 0 => surplus (no burn). If avgNet < 0 => burn of |avgNet|.
  const result = { months: null, status: 'UNKNOWN', message: '' };

  // Not enough data: treat near-zero net as unknown
  if (Math.abs(avgNetOutflow) < 1) {
    result.months = null;
    result.status = 'UNKNOWN';
    result.message = 'Not enough transaction history to compute runway. Add incomes/expenses for accurate estimate.';
    return result;
  }

  if (avgNetOutflow > 0) {
    // surplus, not burning cash
    result.months = Infinity;
    result.status = 'GREEN';
    result.message = 'You are generating surplus. Consider investing excess or raising goals.';
    return result;
  }

  // avgNetOutflow < 0 => we have burn = abs(avgNetOutflow)
  const monthlyBurn = Math.abs(avgNetOutflow);
  if (monthlyBurn <= 0.000001) {
    result.months = null;
    result.status = 'UNKNOWN';
    result.message = 'Monthly burn is zero or too small to compute runway.';
    return result;
  }

  const months = liquidAssets / monthlyBurn;
  result.months = Number.isFinite(months) ? months : null;

  if (result.months === null) {
    result.status = 'UNKNOWN';
    result.message = 'Unable to compute runway.';
    return result;
  }

  if (result.months >= minMonths) {
    result.status = 'GREEN';
    result.message = 'You are generating surplus. Consider investing excess or raising goals.';
  } else if (result.months >= 1) {
    result.status = 'YELLOW';
    result.message = `You have limited runway. Consider cutting expenses or building liquid reserves.`;
  } else {
    result.status = 'RED';
    result.message = `Low runway — less than one month. Take action to increase liquidity or reduce burn.`;
  }

  return result;
}

export default {
  trailingAverages,
  totalLiquidAssets,
  computeRunway
};