#!/usr/bin/env python3
"""
Parse CSV file and load data into the database with proper categorization
"""

import sys
import uuid
from pathlib import Path
from datetime import datetime
import pandas as pd
import logging

sys.path.insert(0, str(Path(__file__).parent))

from storage.database import DatabaseManager
from storage.models import Transaction, Asset, User
from config import Config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def format_month(date_str):
    """Extract YYYY-MM from date string"""
    try:
        date_str = str(date_str).strip()
        # Handle different date formats
        if '/' in date_str:
            parts = date_str.split('/')
            if len(parts) == 3:
                day, month, year = parts
                # Handle 2-digit years
                if len(year) == 2:
                    year = '20' + year
                return f"{year}-{month.zfill(2)}"
        # If already in YYYY-MM-DD format
        if '-' in date_str and len(date_str) >= 7:
            return date_str[:7]
        # If in DD/MM/YYYY format without split
        if len(date_str) >= 10 and '/' in date_str:
            return date_str[-7:].replace('/', '-')
        return date_str
    except:
        return ""


def categorize_transaction_smart(description, amount):
    """Enhanced categorization with Indian Banks & NBFCs"""
    desc_lower = str(description).lower()
    
    # Income patterns
    income_patterns = [
        'capital one', 'credited', 'neft', 'nft', 'salary credited', 
        'payment from', 'received', 'self transfer in', 'imt', 'ift',
        'sweep from', 'rev sweep', 'cms/', 'inf/inft'
    ]
    if any(pattern in desc_lower for pattern in income_patterns):
        return 'income', 'Income'
    
    # Large credits are likely income
    if amount > 10000 and 'credit' in desc_lower:
        return 'income', 'Income'
    
    # EMI/Loan detection for Indian banks and NBFCs
    # Major Indian Banks (public sector)
    public_banks = ['state bank', 'sbi', 'bank of baroda', 'canara bank', 'union bank', 
                    'indian bank', 'pnb', 'punjab national', 'bank of india', 'central bank',
                    'oriental bank', 'obc', 'uco bank', 'iob', 'indian overseas']
    
    # Private banks
    private_banks = ['hdfc bank', 'hdfc', 'icici bank', 'icici', 'axis bank', 'kotak',
                     'indusind', 'yes bank', 'idfc first', 'idfc', 'federal bank', 'rbl']
    
    # HFCs (Housing Finance Companies)
    hfcs = ['canfin homes', 'canfin', 'canfinhomes', 'lic housing', 'dhfl', 'dewan housing',
            'repco home', 'adani capital', 'poonawalla']
    
    # NBFCs
    nbfcs = ['bajaj finserv', 'bajaj finance', 'bajaj', 'tata capital', 'tata finance',
             'mahindra finance', 'shriram', 'muthoot', 'manappuram', 'cholamandalam',
             'sundaram finance', 'fullerton']
    
    # Check if transaction involves any bank/HFC/NBFC (likely EMI if debit)
    all_financial = public_banks + private_banks + hfcs + nbfcs
    is_financial = any(bank in desc_lower for bank in all_financial)
    
    # Check for EMI keywords
    emi_keywords = ['emi', 'loan', 'personal loan', 'installment', 'repayment', 'principal']
    has_emi_keyword = any(keyword in desc_lower for keyword in emi_keywords)
    
    # If it's a financial institution debit with EMI keywords or large amount
    if is_financial and (has_emi_keyword or amount > 30000):
        # Determine specific loan type
        if any(x in desc_lower for x in ['home', 'housing', 'mortgage', 'canfin']):
            return 'emi', 'Home Loan EMI'
        elif 'personal' in desc_lower or 'personal loan' in desc_lower:
            return 'emi', 'Personal Loan EMI'
        else:
            return 'emi', 'Loan EMI'
    
    # Investment
    if any(x in desc_lower for x in ['sip', 'sipg', 'mutual fund', 'investment', 'apy_', 'fortune']):
        return 'investment', 'Investment'
    
    # Insurance
    if any(x in desc_lower for x in ['insurance', 'premium', 'sbi life', 'life insurance', 'lic']):
        return 'expense', 'Insurance'
    
    # Food expenses
    if any(x in desc_lower for x in ['swiggy', 'zomato', 'uber eats', 'food', 'restaurant']):
        return 'expense', 'Food & Dining'
    
    # Cash withdrawals
    if any(x in desc_lower for x in ['nfs/cash', 'cash wdl', 'atm', 'cash withdrawal']):
        return 'expense', 'Cash Withdrawal'
    
    # Transport
    if any(x in desc_lower for x in ['fastag', 'toll', 'fuel', 'petrol', 'hp pay', 'indianoil']):
        return 'expense', 'Transport'
    
    # Medical
    if any(x in desc_lower for x in ['medical', 'pharmacy', 'apollo', 'hospital']):
        return 'expense', 'Medical'
    
    # Groceries
    if any(x in desc_lower for x in ['grocery', 'bigbasket', 'dmart']):
        return 'expense', 'Groceries'
    
    # Shopping/Retail
    if any(x in desc_lower for x in ['amazon', 'flipkart', 'myntra', 'ajio', 'nykaa', 'meesho']):
        return 'expense', 'Shopping'
    
    # Subscription services  
    if any(x in desc_lower for x in ['netflix', 'spotify', 'disney', 'prime', 'youtube premium', 'subscription']):
        return 'expense', 'Subscriptions'
    
    # Banking/Fees
    if any(x in desc_lower for x in ['charges', 'fee', 'penalty', 'service charge', 'gst']):
        return 'expense', 'Banking & Fees'
    
    # Utilities
    if any(x in desc_lower for x in ['electricity', 'water', 'broadband', 'internet', 'wifi', 'spectra', 'act', 'reliance jio']):
        return 'expense', 'Utilities'
    
    # Rent
    if any(x in desc_lower for x in ['rent', 'rental', 'housing', 'accommodation']):
        return 'expense', 'Rent'
    
    # Education
    if any(x in desc_lower for x in ['school', 'college', 'education', 'tuition', 'course']):
        return 'expense', 'Education'
    
    # UPI/Rewards
    if any(x in desc_lower for x in ['cashback', 'reward', 'discount', 'vouchers']):
        return 'income', 'Rewards & Cashback'
    
    return 'expense', 'Other'


def load_csv_to_db(csv_path, user_id):
    """Load CSV transactions to database"""
    db = DatabaseManager(Config.DATABASE_URL)
    session = db.get_session()
    
    try:
        # Read CSV
        df = pd.read_csv(csv_path, encoding='utf-8-sig')
        logger.info(f"Reading {len(df)} rows from CSV")
        
        # Clean column names
        df.columns = df.columns.str.strip()
        
        # Detect columns
        date_col = None
        desc_col = None
        debit_col = None
        credit_col = None
        
        for col in df.columns:
            col_lower = str(col).lower()
            if 'date' in col_lower and not date_col:
                date_col = col
            elif any(x in col_lower for x in ['remark', 'description', 'narration', 'particulars']):
                desc_col = col
            elif any(x in col_lower for x in ['withdrawal', 'debit', 'paid']):
                debit_col = col
            elif any(x in col_lower for x in ['deposit', 'credit', 'received']):
                credit_col = col
        
        logger.info(f"Detected columns: date={date_col}, desc={desc_col}, debit={debit_col}, credit={credit_col}")
        
        transactions_count = 0
        assets_count = 0
        
        for idx, row in df.iterrows():
            try:
                date = str(row[date_col]).strip() if date_col and pd.notna(row.get(date_col)) else ""
                description = str(row[desc_col]).strip() if desc_col and pd.notna(row.get(desc_col)) else ""
                
                # Get amount and type
                amount = 0
                trans_type = "debit"
                
                if debit_col and pd.notna(row.get(debit_col)) and float(row[debit_col]) > 0:
                    amount = float(row[debit_col])
                    trans_type = "debit"
                elif credit_col and pd.notna(row.get(credit_col)) and float(row[credit_col]) > 0:
                    amount = float(row[credit_col])
                    trans_type = "credit"
                else:
                    continue  # Skip rows without valid amounts
                
                # Categorize
                category_type, category_name = categorize_transaction_smart(description, amount)
                
                # Create transaction
                transaction = Transaction(
                    transaction_id=str(uuid.uuid4()),
                    user_id=user_id,
                    date=date,
                    amount=amount,
                    type=trans_type,
                    description_raw=description,
                    merchant_canonical=category_name,
                    category=category_name,
                    month=format_month(date),
                    source='csv_import'
                )
                session.add(transaction)
                transactions_count += 1
                
                # NOTE: Don't create assets for investments automatically
                # Assets should be manually added by user for their actual portfolio
                # Investment transactions are tracked separately
                
            except Exception as e:
                logger.warning(f"Error processing row {idx}: {e}")
                continue
        
        session.commit()
        logger.info(f"✅ Loaded {transactions_count} transactions and {assets_count} assets")
        
    except Exception as e:
        session.rollback()
        logger.error(f"Error: {e}", exc_info=True)
        raise
    finally:
        session.close()
        db.close()


def main():
    """Main function"""
    print("\n" + "="*60)
    print("Load CSV Data to Database")
    print("="*60 + "\n")
    
    csv_path = Path(__file__).parent / 'data' / 'Transactions.csv'
    
    if not csv_path.exists():
        print(f"❌ CSV file not found: {csv_path}")
        print("\nPlease place your CSV file at:")
        print(f"  {csv_path.absolute()}")
        return
    
    db = DatabaseManager(Config.DATABASE_URL)
    session = db.get_session()
    
    try:
        # Get test user
        user = session.query(User).filter(User.username == "testuser").first()
        
        if not user:
            print("❌ Test user not found")
            return
        
        user_id = user.user_id
        
        # Clear existing data
        print("🗑️  Clearing existing transactions and assets...")
        session.query(Transaction).filter(Transaction.user_id == user_id).delete()
        session.query(Asset).filter(Asset.user_id == user_id).delete()
        session.commit()
        
        # Load CSV data
        print("📊 Loading CSV data...")
        load_csv_to_db(csv_path, user_id)
        
        print("\n" + "="*60)
        print("✅ DATA LOADED SUCCESSFULLY!")
        print("="*60 + "\n")
        
    finally:
        session.close()
        db.close()


if __name__ == "__main__":
    main()

