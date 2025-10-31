from __future__ import annotations

from typing import List
from datetime import datetime
from collections import defaultdict

from sqlalchemy import func, or_

from storage.database import DatabaseManager
from storage.models import Transaction
from config import Config


class InvestmentDetector:
    """Shared investment detection utilities used by Salary Sweep and Optimizer."""

    @staticmethod
    def investment_keywords() -> List[str]:
        return [
            'invest', 'investment', 'mutual fund', 'fund', 'sip', 'systematic',
            'zerodha', 'groww', 'upstox', '5paisa', 'angel', 'icici direct', 'hdfc securities', 'axis direct',
            'paytm money', 'et money', 'kuvera', 'coin', 'coin dcb', 'smallcase',
            'hdfc mf', 'icici prudential mf', 'sbi mf', 'axis mf', 'nippon', 'franklin', 'motilal', 'mirae', 'uti', 'kotak mf', 'parag parikh', 'canara robeco',
            'cams', 'kfin', 'karvy', 'mfutility', 'bse', 'nse', 'billdesk'
        ]

    @staticmethod
    def exclusion_keywords() -> List[str]:
        # Avoid FASTag/toll/parking false positives that contain SIP-like tokens
        return ['fastag', 'fast tag', 'toll', 'parking', 'npci fastag', 'recharge fastag']

    @classmethod
    def is_investment_text(cls, text: str) -> bool:
        t = (text or '').lower()
        if any(x in t for x in cls.exclusion_keywords()):
            return False
        return any(k in t for k in cls.investment_keywords())

    @classmethod
    def is_investment_txn(cls, txn: Transaction) -> bool:
        fields = ' '.join([
            (txn.category or ''), (txn.description_raw or ''), (txn.clean_description or ''),
            (txn.merchant_canonical or ''), (txn.merchant_raw or '')
        ])
        # Normalize transaction types: handle both 'withdrawal'/'deposit' and 'debit'/'credit'
        txn_type = (txn.type or '').lower()
        is_debit = txn_type in ['debit', 'withdrawal']
        return is_debit and cls.is_investment_text(fields)

    @classmethod
    def filter_investment_transactions(cls, user_id: str) -> List[Transaction]:
        db = DatabaseManager(Config.DATABASE_URL)
        session = db.get_session()
        try:
            like_terms = [f"%{k}%" for k in cls.investment_keywords()]
            exclude_terms = [f"%{k}%" for k in cls.exclusion_keywords()]

            conds = []
            for term in like_terms:
                conds.append(func.lower(Transaction.category).like(term))
                conds.append(func.lower(Transaction.description_raw).like(term))
                conds.append(func.lower(Transaction.clean_description).like(term))
                conds.append(func.lower(Transaction.merchant_canonical).like(term))
                conds.append(func.lower(Transaction.merchant_raw).like(term))

            ex_conds = []
            for term in exclude_terms:
                ex_conds.append(func.lower(Transaction.description_raw).like(term))
                ex_conds.append(func.lower(Transaction.merchant_canonical).like(term))
                ex_conds.append(func.lower(Transaction.merchant_raw).like(term))

            # Normalize transaction types: handle both 'withdrawal'/'deposit' and 'debit'/'credit'
            q = session.query(Transaction).filter(
                Transaction.user_id == user_id,
                func.lower(Transaction.type).in_(['debit', 'withdrawal']),
                or_(*conds),
                ~or_(*ex_conds)
            ).order_by(Transaction.date)
            return q.all()
        finally:
            session.close()
            db.close()

    @staticmethod
    def detect_sips(transactions: List[Transaction]):
        """Detect SIPs by grouping platform and similar amounts with monthly cadence."""
        sips = []
        platform_groups = defaultdict(list)
        for txn in transactions:
            # Use improved platform extraction if available
            # For now, use merchant_canonical or extract from description
            platform = txn.merchant_canonical or 'Unknown'
            if platform == 'Unknown' or platform == 'Other':
                # Try to extract from description
                desc = (txn.description_raw or '').lower()
                if 'indian clearing corp' in desc or 'clearing corp' in desc:
                    platform = 'Indian Clearing Corp'
                elif 'upi/' in desc:
                    parts = desc.split('/')
                    if len(parts) >= 2:
                        platform = parts[1].strip().title()
                elif 'ach/' in desc:
                    parts = desc.split('/')
                    if len(parts) >= 2:
                        platform = parts[1].strip().title()
            platform_groups[platform].append(txn)

        from api.routes.investment_optimizer import SIPPattern  # local import to avoid cycle on import time

        for platform, txns in platform_groups.items():
            if len(txns) < 2:
                continue
            amount_groups = defaultdict(list)
            for txn in txns:
                placed = False
                for key in list(amount_groups.keys()):
                    base = float(key)
                    if base > 0 and abs(txn.amount - base) / base <= 0.05:
                        amount_groups[key].append(txn)
                        placed = True
                        break
                if not placed:
                    amount_groups[str(txn.amount)] = [txn]

            for amount_key, group in amount_groups.items():
                if len(group) < 2:
                    continue
                sorted_txns = sorted(group, key=lambda x: x.date)
                dates = [datetime.strptime(t.date, '%Y-%m-%d') for t in sorted_txns if t.date]
                is_monthly = all(25 <= (dates[i] - dates[i-1]).days <= 40 for i in range(1, len(dates))) if len(dates) >= 2 else False
                sips.append(SIPPattern(
                    sip_id=f"sip_{platform}_{amount_key}".replace('.', '_'),
                    platform=platform,
                    amount=float(amount_key),
                    frequency='monthly' if is_monthly else 'irregular',
                    transaction_count=len(group),
                    total_invested=sum(t.amount for t in group),
                    start_date=sorted_txns[0].date,
                    last_transaction_date=sorted_txns[-1].date
                ))
        return sips


