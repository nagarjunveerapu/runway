#!/usr/bin/env python3
"""Test if credit card EMIs are being included in detection"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from storage.database import DatabaseManager
from storage.models import BankTransaction, CreditCardTransaction, TransactionType, User
from config import Config

def test_cc_emi_in_detection():
    db = DatabaseManager(Config.DATABASE_URL)
    session = db.get_session()

    try:
        user = session.query(User).filter(User.username == 'test@example.com').first()

        # Simulate what /detect endpoint does
        bank_transactions = session.query(BankTransaction).filter(
            BankTransaction.user_id == user.user_id
        ).all()

        cc_transactions = session.query(CreditCardTransaction).filter(
            CreditCardTransaction.user_id == user.user_id
        ).all()

        print(f"✅ Bank transactions: {len(bank_transactions)}")
        print(f"✅ Credit card transactions: {len(cc_transactions)}")

        # Convert CC to adapters
        all_transactions = []
        for ct in cc_transactions:
            txn_type = ct.type.value if hasattr(ct.type, 'value') else str(ct.type)
            if isinstance(txn_type, str):
                txn_type = txn_type.lower()

            adapter = type('Transaction', (), {
                'transaction_id': ct.transaction_id,
                'date': ct.date,
                'amount': ct.amount,
                'type': txn_type,
                'description_raw': ct.description_raw,
                'merchant_canonical': ct.merchant_canonical,
                'category': ct.category.value if hasattr(ct.category, 'value') else str(ct.category),
            })()
            all_transactions.append(adapter)

        print(f"\n📦 Total adapters created: {len(all_transactions)}")

        # Check EMI patterns
        print(f"\n🔍 Checking for EMI-like patterns in CC transactions:")
        emi_merchants = {}
        for txn in all_transactions:
            if txn.amount >= 10000 and txn.type == 'debit':
                merchant = txn.merchant_canonical or 'Unknown'
                if merchant not in emi_merchants:
                    emi_merchants[merchant] = []
                emi_merchants[merchant].append({
                    'date': txn.date,
                    'amount': txn.amount,
                    'category': txn.category
                })

        for merchant, txns in emi_merchants.items():
            if len(txns) >= 3:
                print(f"\n  ✅ {merchant}: {len(txns)} recurring payments")
                for t in txns[:3]:
                    print(f"     {t['date']}: ₹{t['amount']:,.2f} [{t['category']}]")

    finally:
        session.close()

if __name__ == '__main__':
    test_cc_emi_in_detection()
