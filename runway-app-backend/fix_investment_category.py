"""
Fix investment transaction categorization
"""

import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.classifier import rule_based_category

def fix_investment_categories():
    db_path = "data/finance.db"
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Get all transactions (use description_raw if clean_description is null)
    cursor.execute("""
        SELECT transaction_id, 
               COALESCE(clean_description, description_raw, '') as description, 
               merchant_canonical, 
               category, 
               user_id
        FROM transactions
    """)
    
    transactions = cursor.fetchall()
    print(f"Found {len(transactions)} transactions to recategorize")
    
    updated_count = 0
    for txn_id, description, merchant, old_category, user_id in transactions:
        new_category = rule_based_category(description, merchant)
        
        if new_category != old_category:
            cursor.execute(
                "UPDATE transactions SET category = ? WHERE transaction_id = ?",
                (new_category, txn_id)
            )
            updated_count += 1
            print(f"Updated {txn_id}: '{old_category}' -> '{new_category}'")
            print(f"  Description: {description}")
            print(f"  Merchant: {merchant}")
    
    conn.commit()
    conn.close()
    
    print(f"\n✅ Recategorized {updated_count} transactions")

if __name__ == "__main__":
    fix_investment_categories()

