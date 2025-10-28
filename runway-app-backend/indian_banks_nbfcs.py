"""
Indian Banks and NBFCs Database

This module contains comprehensive lists of Indian banks and NBFCs
for accurate EMI and loan transaction categorization.
"""

# Major Public Sector Banks
PUBLIC_SECTOR_BANKS = [
    'State Bank of India', 'SBI', 'Bank of Baroda', 'Canara Bank', 'Union Bank of India',
    'Indian Bank', 'Punjab National Bank', 'PNB', 'Bank of India', 'Central Bank of India',
    'Oriental Bank of Commerce', 'OBC', 'UCO Bank', 'Indian Overseas Bank', 'IOB',
    'Punjab & Sind Bank', 'State Bank of Bikaner', 'State Bank of Hyderabad'
]

# Major Private Sector Banks
PRIVATE_BANKS = [
    'HDFC Bank', 'HDFC', 'ICICI Bank', 'ICICI', 'Axis Bank', 'Kotak Mahindra', 'Kotak',
    'IndusInd Bank', 'Yes Bank', 'IDFC First Bank', 'IDFC', 'Federal Bank',
    'RBL Bank', 'South Indian Bank', 'City Union Bank', 'Karur Vysya Bank',
    'DCB Bank', 'Dhanlaxmi Bank', 'Bandhan Bank', 'AU Small Finance Bank'
]

# Home Loan Companies (HFCs)
HFC_HOUSING_FINANCE = [
    'HDFC', 'LIC Housing Finance', 'LIC Housing', 'DHFL', 'Dewan Housing',
    'Can Fin Homes', 'CanFin Homes', 'Canfinhomes', 'Canfin', 'Repco Home Finance',
    'Sundaram Finance', 'Adani Capital', 'Poonawalla Finance', 'Muthoot Finance'
]

# Major NBFCs
NBFC_MAJOR = [
    'Bajaj Finserv', 'Bajaj Finance', 'Bajaj', 'Tata Capital', 'Tata Finance',
    'Mahindra Finance', 'Mahindra Rural', 'Shriram Finance', 'Shriram',
    'Muthoot Finance', 'Manappuram Finance', 'Manappuram', 'Cholamandalam',
    'Sundaram Finance', 'First Choice Finance', 'Magma Fincorp', 'Fullerton'
]

# Credit Card Companies
CREDIT_CARD = [
    'American Express', 'Amex', 'HSBC', 'Standard Chartered', 'Standard Charter',
    'Citi Bank', 'Citibank', 'Capital One', 'Discover', 'Diners Club'
]

# Loan Specific Keywords
LOAN_KEYWORDS = [
    'personal loan', 'home loan', 'car loan', 'education loan', 'gold loan',
    'business loan', 'loan', 'emi', 'installment', 'repayment', 'principal',
    'interest', 'foreclosure', 'prepayment', 'outstanding', 'credit limit'
]

# Merchant Names for Loans
LOAN_MERCHANTS = [
    'ajio', 'myntra', 'flipkart', 'amazon', 'paytm', 'phonepe', 'zerodha',
    'groww', 'paytm money', 'tata capital', 'bajaj finserv'
]

# Function to check if transaction is EMI related
def is_emi_transaction(description):
    """
    Check if a transaction is related to EMI/Loan based on description
    
    Args:
        description: Transaction description/remarks
        
    Returns:
        bool: True if EMI, False otherwise
    """
    desc_lower = str(description).lower()
    
    # Check for loan keywords
    if any(keyword in desc_lower for keyword in LOAN_KEYWORDS):
        return True
    
    # Check for banks/NBFCs
    all_banks = PUBLIC_SECTOR_BANKS + PRIVATE_BANKS + HFC_HOUSING_FINANCE + NBFC_MAJOR
    
    # Check if description contains any bank/NBFC name
    for bank in all_banks:
        if bank.lower() in desc_lower:
            return True
    
    # Check for large regular payments (likely EMI)
    # This should be checked with amount in context
    
    return False

# Function to categorize transaction
def categorize_transaction(description, amount, transaction_type):
    """
    Categorize a transaction based on description and amount
    
    Returns:
        tuple: (category_type, category_name)
            category_type: 'emi', 'investment', 'expense', etc.
            category_name: Specific category
    """
    desc_lower = str(description).lower()
    
    # Income
    if transaction_type == 'credit':
        if 'salary' in desc_lower and 'credit' in desc_lower:
            return 'income', 'Salary'
        if 'capital one' in desc_lower or 'neft' in desc_lower:
            return 'income', 'Income'
        return 'income', 'Income'
    
    # EMI/Loans
    if is_emi_transaction(description):
        # Determine loan type
        if any(x in desc_lower for x in ['home', 'housing', 'mortgage', 'canfin']):
            return 'emi', 'Home Loan EMI'
        elif 'personal' in desc_lower or 'personal loan' in desc_lower:
            return 'emi', 'Personal Loan EMI'
        elif 'car' in desc_lower or 'vehicle' in desc_lower:
            return 'emi', 'Car Loan EMI'
        elif 'education' in desc_lower or 'student' in desc_lower:
            return 'emi', 'Education Loan EMI'
        else:
            return 'emi', 'Loan EMI'
    
    # Investments
    if any(x in desc_lower for x in ['sip', 'mutual fund', 'investment', 'fortune', 'apy_']):
        return 'investment', 'Investment'
    
    # Food
    if any(x in desc_lower for x in ['swiggy', 'zomato', 'uber eats', 'uber eats', 'mcdonald']):
        return 'expense', 'Food & Dining'
    
    # Cash
    if any(x in desc_lower for x in ['cash wdl', 'atm', 'nfs/cash', 'cash withdrawal']):
        return 'expense', 'Cash Withdrawal'
    
    # Transport
    if any(x in desc_lower for x in ['fastag', 'toll', 'fuel', 'petrol', 'hp pay', 'indianoil', 'bpcl']):
        return 'expense', 'Transport'
    
    # Insurance
    if any(x in desc_lower for x in ['insurance', 'premium', 'sbi life', 'life insurance', 'life insurance co', 'lic']):
        return 'expense', 'Insurance'
    
    # Medical
    if any(x in desc_lower for x in ['medical', 'pharmacy', 'apollo', 'hospital', 'clinic']):
        return 'expense', 'Medical'
    
    # Groceries
    if any(x in desc_lower for x in ['grocery', 'big basket', 'dmart', 'safal']):
        return 'expense', 'Groceries'
    
    # Shopping
    if any(x in desc_lower for x in ['amazon', 'flipkart', 'myntra', 'ajio', 'shopping', 'online']):
        return 'expense', 'Shopping'
    
    return 'expense', 'Other'


# Export functions
__all__ = ['is_emi_transaction', 'categorize_transaction']

