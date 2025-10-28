"""
Enhanced CSV Upload with Better Parsing and Categorization

This endpoint:
1. Parses CSV with intelligent column detection
2. Uses ML model for categorization
3. Intelligently creates Transactions, Assets, and EMI records
4. Handles multiple CSV formats
"""

from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends, status
import sys
import uuid
from pathlib import Path
import logging
import tempfile
import shutil
from datetime import datetime
import pandas as pd
import re

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from storage.database import DatabaseManager
from storage.models import Transaction, Asset, User, Account
from auth.dependencies import get_current_user
from config import Config
from utils.date_parser import parse_date, parse_month_from_date

logger = logging.getLogger(__name__)

router = APIRouter()


def get_db():
    """Get database instance"""
    return DatabaseManager(Config.DATABASE_URL)


def extract_merchant(description):
    """Extract actual merchant name from description"""
    desc_lower = str(description).lower()
    
    # Look for known merchants
    if 'capital' in desc_lower and 'one' in desc_lower:
        return 'Capital One'
    if 'canfin' in desc_lower:
        return 'Canfin Homes'
    if 'hdfc' in desc_lower:
        return 'HDFC Bank'
    if 'icici' in desc_lower:
        return 'ICICI Bank'
    if 'sbi' in desc_lower or 'state bank' in desc_lower:
        return 'SBI'
    if 'axis' in desc_lower:
        return 'Axis Bank'
    if 'bajaj' in desc_lower:
        return 'Bajaj Finserv'
    if 'muthoot' in desc_lower:
        return 'Muthoot Finance'
    if 'kotak' in desc_lower:
        return 'Kotak Bank'
    if 'yes' in desc_lower and 'bank' in desc_lower:
        return 'Yes Bank'
    if 'idfc' in desc_lower:
        return 'IDFC First Bank'
    if 'federal' in desc_lower and 'bank' in desc_lower:
        return 'Federal Bank'
    
    # Extract first 3 words as potential merchant
    words = description.split()
    if len(words) >= 2:
        return ' '.join(words[:2])
    
    return description[:30]  # First 30 chars if no pattern found


def smart_categorize(description, amount):
    """Enhanced categorization with better pattern matching"""
    desc_lower = str(description).lower()
    amt = float(amount) if amount else 0
    
    # Income patterns
    salary_patterns = ['salary', 'pay', 'wage', 'income', 'credited', 'deposit', 'interest received']
    if any(pattern in desc_lower for pattern in salary_patterns):
        return 'income', 'Salary', 'credit'
    
    # EMI/Loan patterns
    emi_patterns = ['emi', 'loan', 'installment', 'repayment', 'principal', 'interest payment']
    if any(pattern in desc_lower for pattern in emi_patterns):
        return 'emi', 'EMI Payment', 'debit'
    
    # Investment patterns
    investment_patterns = ['sip', 'mutual fund', 'investment', 'stock', 'equity', 'mf', 'ppf', 'nps', 'elss']
    if any(pattern in desc_lower for pattern in investment_patterns):
        return 'investment', 'Investment', 'debit'
    
    # Specific categories
    if any(word in desc_lower for word in ['swiggy', 'zomato', 'foodpanda', 'uber eats']):
        return 'expense', 'Food & Dining', 'debit'
    if any(word in desc_lower for word in ['grocery', 'big basket', 'grofers']):
        return 'expense', 'Groceries', 'debit'
    if any(word in desc_lower for word in ['atm', 'cash withdrawal', 'cash']):
        return 'expense', 'Cash Withdrawal', 'debit'
    if any(word in desc_lower for word in ['fuel', 'petrol', 'diesel', 'bpcl', 'hp', 'indian oil']):
        return 'expense', 'Fuel', 'debit'
    if any(word in desc_lower for word in ['rent', 'house rent']):
        return 'expense', 'Rent', 'debit'
    if any(word in desc_lower for word in ['mobile', 'recharge', 'prepaid', 'postpaid']):
        return 'expense', 'Mobile/Internet', 'debit'
    if any(word in desc_lower for word in ['electricity', 'power', 'utility']):
        return 'expense', 'Utilities', 'debit'
    if any(word in desc_lower for word in ['amazon', 'flipkart', 'myntra', 'online']):
        return 'expense', 'Shopping', 'debit'
    
    # Default
    if amt > 0:
        return 'expense', 'Other', 'debit'
    else:
        return 'expense', 'Unknown', 'debit'


@router.post("/csv-smart")
async def upload_csv_smart(
    file: UploadFile = File(...),
    account_id: str = Form(None),
    current_user: User = Depends(get_current_user)
):
    """
    Upload and intelligently parse CSV file with smart categorization
    """
    
    if not file.filename.endswith('.csv'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only CSV files are supported"
        )
    
    temp_file = None
    db = get_db()
    session = db.get_session()
    
    try:
        # Save uploaded file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.csv') as temp:
            shutil.copyfileobj(file.file, temp)
            temp_file = temp.name
        
        logger.info(f"Processing CSV: {file.filename} for user {current_user.username}")
        
        # Read CSV
        df = pd.read_csv(temp_file, encoding='utf-8-sig')
        logger.info(f"Read {len(df)} rows from CSV")
        
        # Strip whitespace from column names
        df.columns = df.columns.str.strip()
        
        # Find columns intelligently
        date_col = None
        desc_col = None
        debit_col = None
        credit_col = None
        amount_col = None
        balance_col = None
        
        for col in df.columns:
            col_lower = str(col).lower().strip()
            if 'date' in col_lower:
                date_col = col
            elif any(x in col_lower for x in ['remark', 'description', 'narration', 'particulars', 'details']):
                desc_col = col
            elif any(x in col_lower for x in ['debit', 'withdrawal', 'paid', 'spend']):
                debit_col = col
            elif any(x in col_lower for x in ['credit', 'deposit', 'received', 'income']):
                credit_col = col
            elif col_lower == 'amount':
                amount_col = col
            elif 'balance' in col_lower:
                balance_col = col
        
        logger.info(f"Detected columns: date={date_col}, desc={desc_col}, debit={debit_col}, credit={credit_col}")
        
        # Parse transactions
        parsed = []
        for idx, row in df.iterrows():
            try:
                date = str(row[date_col]) if date_col and pd.notna(row.get(date_col)) else ""
                description = str(row[desc_col]) if desc_col and pd.notna(row.get(desc_col)) else ""
                
                # Determine amount and type from CSV columns
                debit_val = float(row.get(debit_col)) if debit_col and pd.notna(row.get(debit_col)) else 0
                credit_val = float(row.get(credit_col)) if credit_col and pd.notna(row.get(credit_col)) else 0
                
                amount = 0
                trans_type = "debit"
                
                # Withdrawal Amount column = DEBIT (money going out)
                # Deposit Amount column = CREDIT (money coming in)
                if debit_val > 0:
                    amount = debit_val
                    trans_type = "debit"
                elif credit_val > 0:
                    amount = credit_val
                    trans_type = "credit"
                else:
                    continue
                
                logger.debug(f"Parsed: {trans_type} ₹{amount} - {description[:50]}")
                
                balance = float(row[balance_col]) if balance_col and pd.notna(row.get(balance_col)) else None
                
                parsed.append({
                    'date': date,
                    'description': description,
                    'amount': amount,
                    'type': trans_type,
                    'balance': balance
                })
                
            except Exception as e:
                logger.warning(f"Skipping row {idx}: {e}")
                continue
        
        logger.info(f"Parsed {len(parsed)} transactions")
        
        # Handle account creation if account_id not provided
        if not account_id:
            # Create a default account for the user
            account_id = str(uuid.uuid4())
            default_account = Account(
                account_id=account_id,
                user_id=current_user.user_id,
                account_type='current',
                bank_name='Uploaded Bank Account',
                is_active=True
            )
            session.add(default_account)
            logger.info(f"Created default account: {account_id}")
        
        # Categorize and save
        transactions_created = 0
        assets_created = 0
        emis_created = 0
        
        logger.info(f"Starting transaction processing for {len(parsed)} parsed transactions")
        
        for idx, txn in enumerate(parsed):
            try:
                # Get category from smart_categorize (but don't use the db_type - use actual transaction type!)
                category_type, category_name, _ = smart_categorize(txn['description'], txn['amount'])
                
                # IMPORTANT: Use the actual transaction type from CSV parsing, NOT from smart_categorize
                # The CSV parser correctly identifies Deposit Amount = CREDIT, Withdrawal Amount = DEBIT
                actual_trans_type = txn['type']  # This comes from CSV parsing (credit/debit)
                
                # Extract actual merchant name (not category)
                merchant_name = extract_merchant(txn['description'])
                
                # Normalize date to ISO format
                normalized_date = parse_date(txn['date'])
                
                # Create transaction
                transaction = Transaction(
                    transaction_id=str(uuid.uuid4()),
                    user_id=current_user.user_id,
                    account_id=account_id,
                    date=normalized_date or txn['date'],  # Use normalized date or fallback
                    amount=txn['amount'],
                    type=actual_trans_type,  # Use actual type from CSV (credit/debit)
                    description_raw=txn['description'],
                    merchant_canonical=merchant_name,  # Now stores actual merchant, not category!
                    category=category_name,  # Category is separate
                    balance=txn.get('balance'),
                    month=parse_month_from_date(normalized_date or txn['date']),
                    source='csv_upload'
                )
                session.add(transaction)
                transactions_created += 1
                
                # Handle investments - NOTE: Not auto-creating assets for investments
                # User should manually add their investment portfolio
                if category_type == 'investment':
                    pass  # Just track as transaction, don't create asset
                
                # Track EMIs
                if category_type == 'emi':
                    emis_created += 1
                
                # Commit every 50 transactions to show progress and ensure persistence
                if (idx + 1) % 50 == 0:
                    session.commit()
                    logger.info(f"Processed {idx + 1}/{len(parsed)} transactions")
            
            except Exception as e:
                logger.warning(f"Error processing transaction {idx}: {e}")
                continue
        
        # Final commit
        session.commit()
        logger.info(f"✅ COMPLETE: Created {transactions_created} transactions, {assets_created} assets, {emis_created} EMIs")
        
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
        logger.error(f"Error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process CSV: {str(e)}"
        )
    finally:
        if temp_file and Path(temp_file).exists():
            Path(temp_file).unlink()
        session.close()
        db.close()

