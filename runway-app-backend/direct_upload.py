#!/usr/bin/env python3
"""
Direct database upload of Aarish.pdf transactions for test2@example.com
Bypasses API authentication for testing purposes
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from ingestion.pdf_parser import PDFParser
from src.merchant_normalizer import MerchantNormalizer
from src.classifier import rule_based_category
from storage.database import DatabaseManager
from storage.models import Transaction, User
from config import Config
import uuid
from datetime import datetime
from sqlalchemy import text

def main():
    print("=" * 80)
    print("Direct Upload: Aarish.pdf → test2@example.com")
    print("=" * 80)

    # Parse PDF
    print("\n1. Parsing PDF...")
    pdf_parser = PDFParser()
    transactions = pdf_parser.parse("Aarish.pdf")
    print(f"   ✅ Parsed {len(transactions)} transactions")

    # Enrich transactions
    print("\n2. Enriching transactions...")
    merchant_norm = MerchantNormalizer()

    for txn in transactions:
        description = txn.get('description', '')
        merchant_raw = txn.get('merchant_raw') or description
        merchant_canonical, score = merchant_norm.normalize(merchant_raw)
        txn['merchant_canonical'] = merchant_canonical

        category = rule_based_category(description, merchant_canonical)
        txn['category'] = category

    print(f"   ✅ Enriched all transactions")

    # Get user_id for test2@example.com
    db = DatabaseManager(Config.DATABASE_URL)
    session = db.get_session()

    try:
        user = session.query(User).filter(User.email == 'test2@example.com').first()

        if not user:
            print("   ❌ User test2@example.com not found")
            return

        user_id = user.user_id
        print(f"   ✅ Found user: {user_id}")

        # Insert transactions
        print("\n3. Inserting transactions into database...")
        inserted = 0

        for txn in transactions:
            try:
                txn_date = txn.get('date', datetime.now().strftime('%Y-%m-%d'))
                txn_type = txn.get('type', 'debit')
                description = txn.get('description', '')

                db_transaction = Transaction(
                    transaction_id=str(uuid.uuid4()),
                    user_id=user_id,
                    date=txn_date,
                    timestamp=datetime.now(),
                    amount=float(txn.get('amount', 0)),
                    type=txn_type,
                    description_raw=description[:255] if description else None,
                    clean_description=description[:255] if description else None,
                    merchant_raw=txn.get('merchant_raw', '')[:255] or None,
                    merchant_canonical=txn.get('merchant_canonical', '')[:255] or None,
                    category=txn.get('category', 'Unknown')[:100],
                    balance=float(txn.get('balance', 0)) if txn.get('balance') else None,
                    source='pdf_upload',
                    is_duplicate=False,
                    duplicate_count=0
                )

                session.add(db_transaction)
                inserted += 1

                if inserted % 100 == 0:
                    print(f"   ... {inserted} transactions inserted")

            except Exception as e:
                print(f"   ⚠️  Failed to insert transaction: {e}")
                continue

        session.commit()
        print(f"   ✅ Inserted {inserted}/{len(transactions)} transactions")

        # Verify credit transactions with INFY SALARY
        print("\n4. Verifying INFY SALARY transactions...")
        result = session.execute("""
            SELECT COUNT(*)
            FROM transactions
            WHERE user_id = :user_id
            AND type = 'credit'
            AND (
                UPPER(description_raw) LIKE '%INFY%SALARY%'
                OR UPPER(clean_description) LIKE '%INFY%SALARY%'
            )
        """, {"user_id": user_id}).fetchone()

        salary_count = result[0]
        print(f"   ✅ Found {salary_count} INFY SALARY credit transactions")

        # Show sample
        samples = session.execute("""
            SELECT date, description_raw, amount, type
            FROM transactions
            WHERE user_id = :user_id
            AND type = 'credit'
            AND (
                UPPER(description_raw) LIKE '%INFY%'
                OR UPPER(clean_description) LIKE '%INFY%'
            )
            ORDER BY date DESC
            LIMIT 5
        """, {"user_id": user_id}).fetchall()

        if samples:
            print("\n   Sample INFY transactions:")
            for s in samples:
                print(f"     - {s[0]}: {s[1]} - ₹{s[2]:,.0f} ({s[3]})")

    except Exception as e:
        session.rollback()
        print(f"   ❌ Error: {e}")
        import traceback
        traceback.print_exc()

    finally:
        session.close()
        db.close()

    print("\n" + "=" * 80)
    print("✅ Upload complete! Salary sweep should now detect INFY SALARY.")
    print("=" * 80)

if __name__ == "__main__":
    main()
