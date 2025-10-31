#!/usr/bin/env python3
"""
Test duplicate detection between PDF and CSV uploads
Tests the normalized description matching
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import os
import logging
from config import Config
from storage.database import DatabaseManager
from storage.models import Transaction, Account
from services.parser_service.parser_service import ParserService
from services.parser_service.parser_factory import ParserFactory

# Enable debug logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

def test_duplicate_detection():
    """Test duplicate detection by uploading PDF then CSV"""
    
    # Initialize database and parser service
    db_manager = DatabaseManager(Config.DATABASE_URL)
    parser_service = ParserService(db_manager)
    
    # Test user ID (from reset_and_setup.py)
    test_user_id = "89b73270-352a-47ec-8a9f-eede6f771bd2"
    
    # File paths
    pdf_path = Path(__file__).parent / "Nagarjun Transactions.pdf"
    csv_path = Path(__file__).parent / "Nagarjun Transactions.csv"
    
    if not pdf_path.exists():
        print(f"❌ PDF file not found: {pdf_path}")
        return
    
    if not csv_path.exists():
        print(f"❌ CSV file not found: {csv_path}")
        return
    
    print("=" * 70)
    print("TESTING DUPLICATE DETECTION: PDF → CSV")
    print("=" * 70)
    
    # Step 1: Upload PDF
    print("\n📄 Step 1: Uploading PDF file...")
    print(f"   File: {pdf_path.name}")
    
    try:
        # Create a mock UploadFile-like object
        from fastapi import UploadFile
        from io import BytesIO
        
        with open(pdf_path, 'rb') as f:
            file_content = f.read()
        
        pdf_file = UploadFile(
            filename=pdf_path.name,
            file=BytesIO(file_content)
        )
        
        pdf_result = parser_service.process_uploaded_file(
            file=pdf_file,
            user_id=test_user_id,
            account_id=None,
            auto_create_account=True
        )
        
        print(f"\n✅ PDF Upload Results:")
        print(f"   Transactions found: {pdf_result.get('transactions_found', 0)}")
        print(f"   Transactions imported: {pdf_result.get('transactions_imported', 0)}")
        print(f"   Duplicates skipped: {pdf_result.get('duplicates_skipped', 0)}")
        print(f"   Account ID: {pdf_result.get('account_id', 'None')}")
        
        pdf_account_id = pdf_result.get('account_id')
        pdf_imported = pdf_result.get('transactions_imported', 0)
        
    except Exception as e:
        print(f"❌ Error uploading PDF: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # Verify PDF transactions in database
    session = db_manager.get_session()
    try:
        pdf_txns = session.query(Transaction).filter(
            Transaction.account_id == pdf_account_id,
            Transaction.source == 'pdf_upload'
        ).count()
        print(f"   ✅ Verified in database: {pdf_txns} PDF transactions")
    except Exception as e:
        print(f"   ⚠️  Error verifying: {e}")
    finally:
        session.close()
    
    # Step 2: Upload CSV (should detect all as duplicates)
    print("\n📊 Step 2: Uploading CSV file (same data)...")
    print(f"   File: {csv_path.name}")
    print(f"   Expected: All {pdf_imported} transactions should be detected as duplicates")
    
    try:
        # Create a mock UploadFile-like object
        from fastapi import UploadFile
        from io import BytesIO
        
        with open(csv_path, 'rb') as f:
            file_content = f.read()
        
        csv_file = UploadFile(
            filename=csv_path.name,
            file=BytesIO(file_content)
        )
        
        csv_result = parser_service.process_uploaded_file(
            file=csv_file,
            user_id=test_user_id,
            account_id=None,
            auto_create_account=True
        )
        
        print(f"\n✅ CSV Upload Results:")
        print(f"   Transactions found: {csv_result.get('transactions_found', 0)}")
        print(f"   Transactions imported: {csv_result.get('transactions_imported', 0)}")
        print(f"   Duplicates skipped: {csv_result.get('duplicates_skipped', 0)}")
        print(f"   Account ID: {csv_result.get('account_id', 'None')}")
        
        csv_account_id = csv_result.get('account_id')
        csv_imported = csv_result.get('transactions_imported', 0)
        csv_duplicates = csv_result.get('duplicates_skipped', 0)
        
    except Exception as e:
        print(f"❌ Error uploading CSV: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # Step 3: Analyze results
    print("\n" + "=" * 70)
    print("DUPLICATE DETECTION ANALYSIS")
    print("=" * 70)
    
    session = db_manager.get_session()
    try:
        # Check account matching
        if pdf_account_id == csv_account_id:
            print(f"\n✅ Account Matching: Same account used (expected)")
        else:
            print(f"\n⚠️  Account Matching: Different accounts!")
            print(f"   PDF Account: {pdf_account_id}")
            print(f"   CSV Account: {csv_account_id}")
        
        # Count total transactions
        total_txns = session.query(Transaction).filter(
            Transaction.account_id == pdf_account_id
        ).count()
        
        pdf_txns = session.query(Transaction).filter(
            Transaction.account_id == pdf_account_id,
            Transaction.source == 'pdf_upload'
        ).count()
        
        csv_txns = session.query(Transaction).filter(
            Transaction.account_id == csv_account_id,
            Transaction.source == 'csv_upload'
        ).count()
        
        print(f"\n📊 Transaction Counts:")
        print(f"   PDF transactions: {pdf_txns}")
        print(f"   CSV transactions: {csv_txns}")
        print(f"   Total transactions: {total_txns}")
        
        # Expected vs Actual
        expected_total = pdf_txns  # Should be same as PDF since all CSV are duplicates
        print(f"\n🎯 Expected Result:")
        print(f"   Total transactions: {expected_total} (only PDF, CSV duplicates skipped)")
        print(f"   CSV duplicates skipped: {pdf_txns}")
        
        print(f"\n📈 Actual Result:")
        print(f"   Total transactions: {total_txns}")
        print(f"   CSV duplicates skipped: {csv_duplicates}")
        
        if total_txns == expected_total and csv_imported == 0:
            print(f"\n✅ SUCCESS: Duplicate detection working correctly!")
            print(f"   ✓ Total transactions = PDF transactions only")
            print(f"   ✓ CSV duplicates correctly skipped")
        else:
            print(f"\n❌ FAILURE: Duplicate detection not working correctly")
            print(f"   Expected total: {expected_total}, Got: {total_txns}")
            print(f"   Expected CSV imported: 0, Got: {csv_imported}")
            
            # Sample some transactions to compare
            print(f"\n🔍 Sampling transactions for comparison...")
            sample_pdf = session.query(Transaction).filter(
                Transaction.account_id == pdf_account_id,
                Transaction.source == 'pdf_upload'
            ).limit(3).all()
            
            sample_csv = session.query(Transaction).filter(
                Transaction.account_id == csv_account_id,
                Transaction.source == 'csv_upload'
            ).limit(3).all()
            
            print(f"\n   Sample PDF transactions:")
            for txn in sample_pdf:
                print(f"      Date: {txn.date}, Amount: {txn.amount}")
                print(f"         Description: {txn.description_raw[:60] if txn.description_raw else 'None'}")
            
            print(f"\n   Sample CSV transactions:")
            for txn in sample_csv:
                print(f"      Date: {txn.date}, Amount: {txn.amount}")
                print(f"         Description: {txn.description_raw[:60] if txn.description_raw else 'None'}")
            
    except Exception as e:
        print(f"❌ Error analyzing results: {e}")
        import traceback
        traceback.print_exc()
    finally:
        session.close()
        db_manager.close()
    
    print("\n" + "=" * 70)

if __name__ == "__main__":
    test_duplicate_detection()

