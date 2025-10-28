#!/usr/bin/env python3
"""
Test script to parse Aarish.pdf and diagnose issues
"""

import sys
import json
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from ingestion.pdf_parser import PDFParser

def test_parse_aarish():
    """Test parsing Aarish.pdf"""
    pdf_path = Path(__file__).parent / "Aarish.pdf"

    if not pdf_path.exists():
        print(f"❌ File not found: {pdf_path}")
        return

    print(f"📄 Parsing: {pdf_path}")
    print("=" * 80)

    parser = PDFParser()

    try:
        transactions = parser.parse(str(pdf_path))

        print(f"\n✅ Success! Extracted {len(transactions)} transactions")
        print(f"Strategy used: {parser.success_strategy}")
        print(f"Strategies attempted: {', '.join(parser.strategies_attempted)}")
        print("\n" + "=" * 80)

        # Show first 10 transactions
        print("\nFirst 10 transactions:")
        for i, txn in enumerate(transactions[:10], 1):
            print(f"\n{i}. {json.dumps(txn, indent=2)}")

        # Analyze transaction types
        credit_count = sum(1 for t in transactions if t.get('type') == 'credit')
        debit_count = sum(1 for t in transactions if t.get('type') == 'debit')

        print("\n" + "=" * 80)
        print(f"\nTransaction Type Breakdown:")
        print(f"  Credits: {credit_count}")
        print(f"  Debits:  {debit_count}")

        # Look for salary-like transactions
        print("\n" + "=" * 80)
        print("\nLooking for SALARY keywords:")
        salary_txns = []
        for txn in transactions:
            desc = txn.get('description', '').upper()
            if any(keyword in desc for keyword in ['SALARY', 'INFY', 'INFOSYS', 'PAYROLL']):
                salary_txns.append(txn)

        if salary_txns:
            print(f"Found {len(salary_txns)} transactions with salary keywords:")
            for txn in salary_txns:
                print(f"  - {txn.get('date')}: {txn.get('description')} - {txn.get('amount')} ({txn.get('type')})")
        else:
            print("❌ No transactions found with SALARY/INFY/INFOSYS/PAYROLL keywords")

        # Show sample descriptions to understand the format
        print("\n" + "=" * 80)
        print("\nSample descriptions (first 20):")
        for i, txn in enumerate(transactions[:20], 1):
            print(f"{i}. {txn.get('description', 'N/A')[:100]}")

    except Exception as e:
        print(f"❌ Parsing failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_parse_aarish()
