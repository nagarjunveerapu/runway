#!/usr/bin/env python3
"""Test loan EMI detection from credit card transactions"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from storage.database import DatabaseManager
from storage.models import BankTransaction, CreditCardTransaction, TransactionType
from config import Config

def test_loan_detection():
    db = DatabaseManager(Config.DATABASE_URL)
    session = db.get_session()

    try:
        # Get user ID
        from storage.models import User
        user = session.query(User).filter(User.username == 'test@example.com').first()
        if not user:
            print("❌ User not found")
            return

        print(f"✅ Testing for user: {user.username} ({user.user_id})")

        # Get credit card debits
        cc_debits = session.query(CreditCardTransaction).filter(
            CreditCardTransaction.user_id == user.user_id,
            CreditCardTransaction.type == TransactionType.DEBIT
        ).all()

        print(f"\n📊 Found {len(cc_debits)} credit card debit transactions")

        # Filter substantial debits
        substantial = [t for t in cc_debits if float(t.amount) >= 10000]
        print(f"📊 Found {len(substantial)} substantial debits (>= 10000)")

        # Group by merchant
        merchants = {}
        for txn in substantial:
            merchant = txn.merchant_canonical or 'Unknown'
            if merchant not in merchants:
                merchants[merchant] = []
            merchants[merchant].append({
                'date': txn.date,
                'amount': float(txn.amount),
                'metadata': txn.extra_metadata
            })

        print(f"\n🏪 Merchants with substantial debits:")
        for merchant, txns in merchants.items():
            print(f"\n  {merchant}: {len(txns)} transactions")
            for txn in sorted(txns, key=lambda x: x['date']):
                emi_converted = txn['metadata'].get('emi_converted', False) if txn['metadata'] else False
                print(f"    {txn['date']}: ₹{txn['amount']:,.2f} {'[EMI CONVERTED]' if emi_converted else ''}")

            # Check for recurring patterns
            if len(txns) >= 3:
                amounts = [t['amount'] for t in txns]
                avg_amt = sum(amounts) / len(amounts)
                print(f"    ✅ RECURRING PATTERN DETECTED: {len(txns)} payments, avg ₹{avg_amt:,.2f}")

    finally:
        session.close()

if __name__ == '__main__':
    test_loan_detection()
