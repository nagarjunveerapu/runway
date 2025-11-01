"""
Recategorize transactions to improve retail/shopping categorization

Updates transactions with improved categorization rules for:
- Ample Technologies (Apple retailer)
- Reliance Retail and other retail chains
- General retail store patterns
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from storage.database import DatabaseManager
from storage.models import User, Transaction, TransactionCategory
from config import Config
from src.classifier import rule_based_category

def recategorize_transactions(user_id: str = None):
    """
    Recategorize transactions using updated classifier rules
    
    Args:
        user_id: Specific user ID to update (None = all users)
    """
    db = DatabaseManager(Config.DATABASE_URL)
    session = db.get_session()
    
    try:
        # Build query
        query = session.query(Transaction)
        if user_id:
            query = query.filter(Transaction.user_id == user_id)
        
        transactions = query.all()
        print(f"Found {len(transactions)} transactions to recategorize")
        
        updated_count = 0
        category_changes = {}
        
        for txn in transactions:
            # Get description and merchant
            description = txn.description_raw or txn.clean_description or ''
            merchant = txn.merchant_canonical or txn.merchant_raw or ''
            
            # Get old category
            old_category = txn.category
            if hasattr(old_category, 'value'):
                old_category_str = old_category.value
            else:
                old_category_str = str(old_category) if old_category else 'Unknown'
            
            # Categorize using updated rules
            new_category_str, sub_type = rule_based_category(description, merchant)
            
            # Map to TransactionCategory enum if needed
            try:
                # Try to find matching enum
                new_category_enum = None
                for cat in TransactionCategory:
                    if cat.value == new_category_str or cat.value.lower() == new_category_str.lower():
                        new_category_enum = cat
                        break
                
                # If no match, use default
                if not new_category_enum:
                    if new_category_str == 'Shopping':
                        new_category_enum = TransactionCategory.SHOPPING
                    elif new_category_str == 'Food':
                        new_category_enum = TransactionCategory.FOOD_DINING
                    else:
                        # Try to find closest match or use OTHER
                        new_category_enum = TransactionCategory.OTHER
            except:
                new_category_enum = TransactionCategory.OTHER
            
            # Update if category changed
            if old_category_str != new_category_str:
                txn.category = new_category_enum.value  # Store as enum value
                if sub_type:
                    txn.transaction_sub_type = sub_type
                
                updated_count += 1
                change_key = f"{old_category_str} -> {new_category_str}"
                category_changes[change_key] = category_changes.get(change_key, 0) + 1
                
                if updated_count <= 10:  # Show first 10 updates
                    print(f"  Updated: {old_category_str} -> {new_category_str} (Sub: {sub_type})")
                    print(f"    Merchant: {merchant[:50]}")
                    print(f"    Description: {description[:60]}")
        
        session.commit()
        
        print(f"\n✅ Recategorized {updated_count} transactions")
        print("\nCategory Changes Summary:")
        for change, count in sorted(category_changes.items(), key=lambda x: x[1], reverse=True):
            print(f"  {change}: {count} transactions")
        
        return updated_count
        
    except Exception as e:
        session.rollback()
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        session.close()
        db.close()


if __name__ == "__main__":
    from storage.database import DatabaseManager
    from storage.models import User
    from config import Config
    
    db = DatabaseManager(Config.DATABASE_URL)
    session = db.get_session()
    
    try:
        # Get test user
        user = session.query(User).filter(User.email == 'test@example.com').first()
        if user:
            print(f"Recategorizing transactions for user: {user.email}")
            recategorize_transactions(user_id=user.user_id)
        else:
            print("Test user not found")
    finally:
        session.close()
        db.close()

