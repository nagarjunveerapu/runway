#!/usr/bin/env python3
"""
Test EMI detection with ML model
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from ml.categorizer import MLCategorizer

# Initialize categorizer
categorizer = MLCategorizer()

# Test transactions
test_transactions = [
    {'merchant_canonical': 'Canfin Homes', 'description': 'EMI payment'},
    {'merchant_canonical': 'Bajaj Finserv', 'description': 'loan installment'},
    {'merchant_canonical': 'HDFC Home Loan', 'description': 'monthly emi'},
    {'merchant_canonical': 'SBI Personal Loan', 'description': 'emi deduction'},
    {'merchant_canonical': 'Swiggy', 'description': 'food delivery'},
    {'merchant_canonical': 'Amazon', 'description': 'online shopping'},
    {'merchant_canonical': 'Netflix', 'description': 'subscription'},
]

print("=" * 60)
print("Testing ML-based EMI Detection")
print("=" * 60)

for txn in test_transactions:
    category, confidence = categorizer.predict(txn)
    is_emi = category == 'EMI & Loans'
    status = "✅ EMI" if is_emi else "❌ NOT EMI"

    print(f"\n{status}")
    print(f"  Merchant: {txn['merchant_canonical']}")
    print(f"  Predicted: {category} (confidence: {confidence:.2f})")

print("\n" + "=" * 60)
