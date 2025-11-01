#!/usr/bin/env python3
"""Test loan EMI detection with the fix"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from storage.database import DatabaseManager
from storage.models import BankTransaction, CreditCardTransaction, TransactionType, User
from config import Config

def test_loan_detection_fixed():
    db = DatabaseManager(Config.DATABASE_URL)
    session = db.get_session()

    try:
        user = session.query(User).filter(User.username == 'test@example.com').first()
        if not user:
            print("❌ User not found")
            return

        print(f"✅ Testing FIXED logic for user: {user.username}")

        # Get all transactions
        cc_debits = session.query(CreditCardTransaction).filter(
            CreditCardTransaction.user_id == user.user_id,
            CreditCardTransaction.type == TransactionType.DEBIT
        ).all()

        # Find EMI-converted (to exclude)
        emi_converted_ids = set()
        emi_converted_txns = {}
        for txn in cc_debits:
            metadata = txn.extra_metadata or {}
            if metadata.get('emi_converted', False):
                emi_converted_ids.add(txn.transaction_id)
                emi_converted_txns[txn.merchant_canonical] = {
                    'date': txn.date,
                    'amount': float(txn.amount),
                    'emi_amount': metadata.get('emi_amount')
                }
                print(f"\n🔍 Found EMI-converted purchase:")
                print(f"   Merchant: {txn.merchant_canonical}")
                print(f"   Original amount: ₹{txn.amount:,.2f}")
                print(f"   EMI amount: ₹{metadata.get('emi_amount'):,.2f}")
                print(f"   ❌ EXCLUDING from pattern detection")

        # Filter: >= 10k AND NOT emi-converted
        substantial = [
            t for t in cc_debits
            if float(t.amount) >= 10000 and t.transaction_id not in emi_converted_ids
        ]

        print(f"\n📊 After filtering:")
        print(f"   Total CC debits: {len(cc_debits)}")
        print(f"   EMI-converted (excluded): {len(emi_converted_ids)}")
        print(f"   Substantial debits for pattern matching: {len(substantial)}")

        # Group by merchant
        merchants = {}
        for txn in substantial:
            merchant = txn.merchant_canonical or 'Unknown'
            if merchant not in merchants:
                merchants[merchant] = []
            merchants[merchant].append({
                'date': txn.date,
                'amount': float(txn.amount)
            })

        print(f"\n🎯 Recurring EMI patterns detected:")
        for merchant, txns in merchants.items():
            if len(txns) >= 3:
                amounts = [t['amount'] for t in txns]
                avg_amt = sum(amounts) / len(amounts)
                print(f"\n  ✅ {merchant}:")
                print(f"     Payments: {len(txns)}")
                print(f"     Average EMI: ₹{avg_amt:,.2f}")
                if merchant in emi_converted_txns:
                    orig = emi_converted_txns[merchant]
                    print(f"     Original purchase: ₹{orig['amount']:,.2f} on {orig['date']}")
                    print(f"     Expected EMI: ₹{orig['emi_amount']:,.2f}")
                print(f"     Actual EMIs:")
                for txn in sorted(txns, key=lambda x: x['date']):
                    print(f"       {txn['date']}: ₹{txn['amount']:,.2f}")

    finally:
        session.close()

if __name__ == '__main__':
    test_loan_detection_fixed()
