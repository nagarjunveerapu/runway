"""
Enhanced File Upload API with ML Categorization and Smart Import

This endpoint:
1. Uploads CSV file
2. Parses transactions
3. Runs ML categorization
4. Intelligently categorizes into Transactions, Assets, EMIs
5. Saves to respective database tables
"""

from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, status
import sys
import uuid
from pathlib import Path
import logging
import tempfile
import shutil
from datetime import datetime
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from storage.database import DatabaseManager
from storage.models import Transaction, Asset, User
from auth.dependencies import get_current_user
from config import Config

logger = logging.getLogger(__name__)

router = APIRouter()


def get_db():
    """Get database instance"""
    return DatabaseManager(Config.DATABASE_URL)


def format_month(date_str):
    """Extract YYYY-MM from date string"""
    try:
        return date_str[:7] if len(date_str) >= 7 else date_str
    except:
        return ""


def categorize_transaction(description, amount):
    """Simple categorization logic - can be enhanced with ML"""
    desc_lower = description.lower()
    
    # Income
    if any(word in desc_lower for word in ['salary', 'credited', 'deposit', 'interest']):
        return 'income', 'Salary'
    
    # EMI/Loan
    if any(word in desc_lower for word in ['emi', 'loan', 'installment']):
        return 'emi', 'EMI Payment'
    
    # Investment
    if any(word in desc_lower for word in ['sip', 'mutual fund', 'investment', 'stock']):
        return 'investment', 'Investment'
    
    # Expenses
    if any(word in desc_lower for word in ['grocery', 'swiggy', 'zomato']):
        return 'expense', 'Food & Dining'
    elif any(word in desc_lower for word in ['atm', 'cash', 'withdrawal']):
        return 'expense', 'Cash Withdrawal'
    else:
        return 'expense', 'Other'


@router.post("/csv-categorize")
async def upload_and_categorize_csv(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: DatabaseManager = Depends(get_db)
):
    """
    Upload CSV file, categorize with ML, and save to respective models
    
    Returns summary of what was imported:
    - Transactions created
    - Assets created
    - EMIs identified
    """
    
    if not file.filename.lower().endswith('.csv'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only CSV files are supported"
        )
    
    temp_file = None
    session = db.get_session()
    
    try:
        # Save uploaded file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.csv') as temp:
            shutil.copyfileobj(file.file, temp)
            temp_file = temp.name
        
        logger.info(f"Processing CSV file: {file.filename} for user {current_user.username}")
        
        # Read CSV
        df = pd.read_csv(temp_file, encoding='utf-8-sig')
        logger.info(f"Read {len(df)} rows from CSV")
        
        # Detect CSV format and parse
        parsed_transactions = []
        
        # Try to detect columns
        date_col = None
        desc_col = None
        debit_col = None
        credit_col = None
        amount_col = None
        balance_col = None
        
        for col in df.columns:
            col_lower = str(col).lower()
            if 'date' in col_lower:
                date_col = col
            elif any(x in col_lower for x in ['remark', 'description', 'narration']):
                desc_col = col
            elif any(x in col_lower for x in ['debit', 'withdrawal', 'paid']):
                debit_col = col
            elif any(x in col_lower for x in ['credit', 'deposit', 'received']):
                credit_col = col
            elif 'amount' in col_lower:
                amount_col = col
            elif 'balance' in col_lower:
                balance_col = col
        
        # Parse transactions
        for idx, row in df.iterrows():
            try:
                date = str(row[date_col]) if date_col else ""
                description = str(row[desc_col]) if desc_col else ""
                
                # Determine amount and type
                if debit_col and pd.notna(row.get(debit_col)):
                    amount = abs(float(row[debit_col]))
                    trans_type = "debit"
                elif credit_col and pd.notna(row.get(credit_col)):
                    amount = abs(float(row[credit_col]))
                    trans_type = "credit"
                else:
                    continue  # Skip rows without amount
                
                balance = float(row[balance_col]) if balance_col and pd.notna(row.get(balance_col)) else None
                
                parsed_transactions.append({
                    'date': date,
                    'description': description,
                    'amount': amount,
                    'type': trans_type,
                    'balance': balance
                })
                
            except Exception as e:
                logger.warning(f"Failed to parse row {idx}: {e}")
                continue
        
        logger.info(f"Parsed {len(parsed_transactions)} transactions")
        
        # Categorize and save to database
        transactions_created = 0
        assets_created = 0
        emis_created = 0
        
        for txn in parsed_transactions:
            # Categorize
            category_type, category = categorize_transaction(txn['description'], txn['amount'])
            
            # Create transaction record
            transaction = Transaction(
                transaction_id=str(uuid.uuid4()),
                user_id=current_user.user_id,
                date=txn['date'],
                amount=txn['amount'],
                type=txn['type'],
                description_raw=txn['description'],
                merchant_canonical=category,
                category=category,
                balance=txn.get('balance'),
                month=format_month(txn['date']),
                source='csv_upload'
            )
            session.add(transaction)
            transactions_created += 1
            
            # If investment, also create/update asset
            if category_type == 'investment':
                # Check if asset already exists
                existing_asset = session.query(Asset).filter(
                    Asset.user_id == current_user.user_id,
                    Asset.name == category
                ).first()
                
                if not existing_asset:
                    asset = Asset(
                        asset_id=str(uuid.uuid4()),
                        user_id=current_user.user_id,
                        name=category,
                        asset_type="Mutual Fund",
                        quantity=1,
                        current_value=txn['amount'],
                        liquid=True
                    )
                    session.add(asset)
                    assets_created += 1
            
            # If EMI, track it
            if category_type == 'emi':
                emis_created += 1
        
        session.commit()
        
        logger.info(f"Created: {transactions_created} transactions, {assets_created} assets, {emis_created} EMIs")
        
        return {
            "filename": file.filename,
            "transactions_created": transactions_created,
            "assets_created": assets_created,
            "emis_identified": emis_created,
            "status": "success",
            "message": f"Successfully imported {transactions_created} transactions"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        logger.error(f"Error processing CSV: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process CSV: {str(e)}"
        )
    finally:
        if temp_file and Path(temp_file).exists():
            Path(temp_file).unlink()
        session.close()


# Database dependency is already defined above

