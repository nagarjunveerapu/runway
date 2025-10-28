"""Create reports/summary.json from parsed transactions."""
from typing import List, Dict, Any
import json
import os
from collections import defaultdict, Counter
import logging

logger = logging.getLogger(__name__)


def compute_summary(transactions: List[Dict[str, Any]], out_path: str) -> Dict[str, Any]:
    total_transactions = len(transactions)

    # Only count withdrawals as spend (not deposits)
    # Check if we have withdrawal/deposit fields (from CSV) or just amount (from text)
    total_spend = 0.0
    for t in transactions:
        # If we have explicit withdrawal field (from CSV), use that
        if 'withdrawal' in t and t.get('withdrawal'):
            total_spend += t.get('withdrawal', 0.0)
        # Otherwise, if transaction_type indicates withdrawal, use amount
        elif t.get('transaction_type') == 'withdrawal':
            total_spend += t.get('amount', 0.0)
        # For text-parsed transactions without transaction_type, use amount
        elif 'transaction_type' not in t:
            total_spend += t.get('amount', 0.0)

    upi_transactions = [t for t in transactions if t.get('channel') == 'UPI']
    upi_count = len(upi_transactions)
    upi_spend = 0.0
    for t in upi_transactions:
        if 'withdrawal' in t and t.get('withdrawal'):
            upi_spend += t.get('withdrawal', 0.0)
        elif t.get('transaction_type') == 'withdrawal':
            upi_spend += t.get('amount', 0.0)
        elif 'transaction_type' not in t:
            upi_spend += t.get('amount', 0.0)

    # spend by merchant (only withdrawals)
    spend_by_merchant = defaultdict(float)
    for t in transactions:
        m = t.get('merchant') or 'Other'
        amount_to_add = 0.0
        if 'withdrawal' in t and t.get('withdrawal'):
            amount_to_add = t.get('withdrawal', 0.0)
        elif t.get('transaction_type') == 'withdrawal':
            amount_to_add = t.get('amount', 0.0)
        elif 'transaction_type' not in t:
            amount_to_add = t.get('amount', 0.0)
        spend_by_merchant[m] += amount_to_add

    top_10 = sorted(spend_by_merchant.items(), key=lambda x: x[1], reverse=True)[:10]

    # spend by category (only withdrawals)
    spend_by_cat = defaultdict(float)
    for t in transactions:
        amount_to_add = 0.0
        if 'withdrawal' in t and t.get('withdrawal'):
            amount_to_add = t.get('withdrawal', 0.0)
        elif t.get('transaction_type') == 'withdrawal':
            amount_to_add = t.get('amount', 0.0)
        elif 'transaction_type' not in t:
            amount_to_add = t.get('amount', 0.0)
        spend_by_cat[t.get('category') or 'Other'] += amount_to_add

    # recurring detection: merchants with recurrence_count>=2
    recurring = [
        {'merchant': t['merchant'] or 'Other', 'count': t.get('recurrence_count', 0)}
        for t in transactions if t.get('recurrence_count', 0) >= 2
    ]
    # aggregate recurring by merchant
    rec_map = defaultdict(int)
    for r in recurring:
        rec_map[r['merchant']] += r['count']

    recurring_list = sorted([{'merchant': k, 'count': v} for k, v in rec_map.items()], key=lambda x: x['count'], reverse=True)

    summary = {
        'total_transactions': total_transactions,
        'total_spend': total_spend,
        'upi_transactions_count': upi_count,
        'upi_spend': upi_spend,
        'top_10_merchants_by_spend': [{'merchant': m, 'spend': s} for m, s in top_10],
        'spend_by_category': dict(spend_by_cat),
        'recurring_payments': recurring_list,
    }

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2)

    return summary
