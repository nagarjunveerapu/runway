"""
Generate comprehensive training data for ML Categorizer

This script helps you create a larger, better training dataset.
Run it to generate more samples for each category.

Usage:
    python3 ml/generate_training_data.py
    python3 ml/generate_training_data.py --samples-per-category 100
"""

import json
import argparse
from pathlib import Path
from datetime import datetime
import random


# Comprehensive merchant mappings by category
MERCHANTS_BY_CATEGORY = {
    'Food & Dining': [
        'Swiggy', 'Zomato', 'Uber Eats', 'Domino\'s Pizza', 'Pizza Hut',
        'KFC', 'McDonald\'s', 'Subway', 'Café Coffee Day', 'Starbucks',
        'Dunzo', 'Food Panda', 'Faasos', 'Freshmenu', 'BOX8',
        'Freshify', 'Burger King', 'Barbeque Nation', 'Mainland China',
        'Anytime Chicken', 'Natural Ice Cream', 'Baskin Robbins'
    ],
    
    'Shopping': [
        'Amazon', 'Flipkart', 'Myntra', 'Nykaa', 'FirstCry',
        'Purplle', 'Ajio', 'Tata Cliq', 'Croma', 'Reliance Digital',
        'Spar', 'Metro Cash', 'Decathlon', 'D Mart', 'More',
        'ShopClues', 'Snapdeal', 'Paytm Mall', 'Jabong', 'Koovs'
    ],
    
    'Transport': [
        'Uber', 'Ola', 'Rapido', 'Zoomcar', 'Drivezy',
        'RedBus', 'MakeMyTrip', 'Yatra', 'ixigo', 'Goibibo',
        'Meru', 'Auto', 'Rickshaw', 'Bike Taxi'
    ],
    
    'Entertainment': [
        'Netflix', 'Amazon Prime', 'Spotify', 'YouTube Premium',
        'Hotstar', 'Disney+', 'Voot', 'Zee5', 'SonyLiv',
        'Apple Music', 'BookMyShow', 'PVR', 'INOX', 'Cinepolis',
        'Game Center', 'PUBG', 'Free Fire', 'Call of Duty'
    ],
    
    'Healthcare': [
        'Apollo Pharmacy', 'MedPlus', '1mg', 'Netmeds', 'Pharmeasy',
        'Apollo Hospitals', 'Fortis', 'Max Healthcare', 'Manipal',
        'Practo', 'Cure.fit', 'TruHealth', 'Dental Clinic',
        'Eye Clinic', 'Diagnostic Lab'
    ],
    
    'Bills & Utilities': [
        'Airtel', 'Jio', 'BSNL', 'Vodafone', 'Idea',
        'Electricity Board', 'BSES', 'TATA Power', 'Adani Power',
        'Indane', 'HP Gas', 'Bharat Gas', 'Municipal Corporation',
        'Water Board', 'Housing Society'
    ],
    
    'Groceries': [
        'Big Bazaar', 'Reliance Fresh', 'DMart', 'Spencer\'s',
        'More', 'Star Bazaar', 'Grofers', 'BigBasket', 'Nature\'s Basket',
        'Hypercity', 'Spar', 'Metro Cash', 'Food Hall', 'Food World'
    ],
    
    'Travel': [
        'MakeMyTrip', 'Goibibo', 'Yatra', 'Cleartrip', 'ixigo',
        'Air India', 'IndiGo', 'SpiceJet', 'GoAir', 'Vistara',
        'OYO', 'Fab Hotels', 'Treebo', 'OYO Rooms', 'Zomato Hotels',
        'Uber', 'Ola', 'RedBus', 'Railway', 'IRCTC'
    ],
    
    'Transfer': [
        'UPI', 'NEFT', 'RTGS', 'IMPS', 'BHIM',
        'Google Pay', 'PhonePe', 'Paytm', 'Amazon Pay',
        'Bank Transfer', 'HDFC', 'ICICI', 'SBI', 'Axis',
        'Kotak', 'Paytm Bank', 'PayPal', 'Razorpay'
    ],

    'EMI & Loans': [
        'HDFC Home Loan', 'ICICI Home Loan', 'SBI Home Loan', 'Axis Home Loan',
        'Canfin Homes', 'LIC Housing Finance', 'DHFL', 'Indiabulls Housing',
        'PNB Housing', 'Bajaj Finserv', 'Bajaj Finance', 'Tata Capital',
        'Fullerton India', 'Capital First', 'IIFL Finance', 'Mahindra Finance',
        'Cholamandalam Finance', 'L&T Finance', 'HDFC Car Loan', 'ICICI Car Loan',
        'SBI Car Loan', 'Kotak Car Loan', 'HDFC Personal Loan', 'ICICI Personal Loan',
        'SBI Personal Loan', 'Axis Personal Loan', 'Yes Bank Loan', 'IndusInd Loan',
        'RBL Bank Loan', 'IDFC Loan', 'Kotak Mahindra Loan', 'Standard Chartered Loan',
        'Citibank Loan', 'HSBC Loan', 'Barclays Loan', 'DBS Loan'
    ],

    'Insurance': [
        'SBI Life Insurance', 'LIC', 'HDFC Life', 'ICICI Prudential',
        'Max Life Insurance', 'Bajaj Allianz', 'Tata AIA', 'Birla Sun Life',
        'Kotak Life Insurance', 'Reliance Nippon Life', 'PNB MetLife', 'Aegon Life',
        'Future Generali', 'Aviva Life', 'Bharti AXA', 'Edelweiss Tokio',
        'IDBI Federal', 'IndiaFirst Life', 'Star Union Dai-ichi', 'Sahara Life',
        'New India Assurance', 'Oriental Insurance', 'United India Insurance',
        'National Insurance', 'HDFC Ergo', 'ICICI Lombard', 'Bajaj Allianz General',
        'Reliance General', 'TATA AIG', 'Royal Sundaram', 'Star Health',
        'Care Health Insurance', 'Niva Bupa', 'Manipal Cigna', 'Aditya Birla Health'
    ],

    'Mutual Funds & Investments': [
        'HDFC Mutual Fund', 'ICICI Prudential MF', 'SBI Mutual Fund', 'Axis Mutual Fund',
        'Aditya Birla MF', 'UTI Mutual Fund', 'Kotak Mutual Fund', 'Nippon India MF',
        'DSP Mutual Fund', 'Franklin Templeton', 'IDFC Mutual Fund', 'Tata Mutual Fund',
        'Mirae Asset MF', 'Motilal Oswal MF', 'L&T Mutual Fund', 'PPFAS Mutual Fund',
        'Zerodha Coin', 'Groww', 'Paytm Money', 'ET Money', 'Kuvera', 'INDMoney',
        'Systematic Investment Plan', 'SIP Payment', 'Mutual Fund SIP'
    ],

    'Government Schemes': [
        'APY Atal Pension Yojana', 'NPS National Pension', 'PPF Public Provident Fund',
        'SSY Sukanya Samriddhi', 'SCSS Senior Citizen Savings', 'NSC National Savings',
        'Kisan Vikas Patra', 'Post Office Savings', 'PMJJBY Jan Dhan', 'PMSBY Suraksha Bima',
        'Pradhan Mantri Jeevan Jyoti', 'EPF Employee Provident Fund', 'ESI Employee State Insurance',
        'Postal Life Insurance', 'RPF Railway Provident Fund'
    ]
}


# Common transaction descriptions by category
DESCRIPTIONS_BY_CATEGORY = {
    'Food & Dining': [
        'food delivery', 'restaurant bill', 'online food order',
        'dine in', 'take away', 'fast food', 'coffee', 'beverages',
        'lunch', 'dinner', 'breakfast', 'cafe', 'bakery', 'grocery'
    ],
    
    'Shopping': [
        'online shopping', 'electronics', 'fashion', 'apparel',
        'books', 'toys', 'furniture', 'home decor', 'kitchen items',
        'mobile', 'laptop', 'watch', 'accessories', 'cosmetics'
    ],
    
    'Transport': [
        'cab ride', 'auto rickshaw', 'bus ticket', 'metro',
        'airport taxi', 'bike taxi', 'train', 'flight booking'
    ],
    
    'Entertainment': [
        'streaming subscription', 'movie ticket', 'game purchase',
        'music', 'concert', 'events', 'sports', 'gaming'
    ],
    
    'Healthcare': [
        'medicine', 'pharmacy', 'hospital', 'doctor fee', 'lab test',
        'dental', 'physiotherapy', 'health checkup', 'vaccination'
    ],
    
    'Bills & Utilities': [
        'mobile recharge', 'electricity bill', 'gas cylinder',
        'internet bill', 'water bill', 'maintenance', 'insurance',
        'credit card', 'loan emi', 'investment'
    ],
    
    'Groceries': [
        'grocery shopping', 'vegetables', 'fruits', 'dairy products',
        'household items', 'cleaning supplies', 'food grains'
    ],
    
    'Travel': [
        'hotel booking', 'flight ticket', 'train ticket', 'bus ticket',
        'taxi', 'travel package', 'sightseeing', 'rental car'
    ],
    
    'Transfer': [
        'bank transfer', 'upi payment', 'neft', 'imps', 'wallet',
        'refund', 'cashback', 'salary credit', 'interest credit'
    ],

    'EMI & Loans': [
        'emi', 'loan repayment', 'home loan emi', 'car loan emi',
        'personal loan emi', 'loan installment', 'monthly emi',
        'housing finance', 'auto loan', 'two wheeler loan',
        'education loan', 'business loan', 'gold loan', 'loan payment',
        'equated monthly installment', 'finance emi', 'nbfc emi',
        'mortgage payment', 'vehicle finance', 'consumer loan'
    ],

    'Insurance': [
        'insurance premium', 'life insurance', 'health insurance', 'term insurance',
        'policy premium', 'insurance renewal', 'medical insurance', 'vehicle insurance',
        'motor insurance', 'car insurance', 'bike insurance', 'home insurance',
        'fire insurance', 'general insurance', 'endowment policy', 'ulip premium',
        'group insurance', 'family floater', 'critical illness', 'accident insurance'
    ],

    'Mutual Funds & Investments': [
        'sip', 'systematic investment', 'mutual fund', 'equity fund', 'debt fund',
        'liquid fund', 'elss', 'index fund', 'investment', 'portfolio',
        'monthly sip', 'investment plan', 'wealth creation', 'fund investment',
        'asset management', 'equity investment', 'growth fund', 'balanced fund'
    ],

    'Government Schemes': [
        'atal pension', 'apy', 'nps', 'national pension', 'ppf', 'provident fund',
        'epf', 'employee provident', 'sukanya samriddhi', 'senior citizen savings',
        'national savings', 'postal savings', 'government scheme', 'pension scheme',
        'social security', 'jeevan jyoti', 'suraksha bima', 'kisan vikas'
    ]
}


def generate_training_samples(category: str, count: int) -> list:
    """Generate training samples for a category"""
    merchants = MERCHANTS_BY_CATEGORY.get(category, [])
    descriptions = DESCRIPTIONS_BY_CATEGORY.get(category, [])
    
    if not merchants or not descriptions:
        return []
    
    samples = []
    for i in range(count):
        merchant = random.choice(merchants)
        description = random.choice(descriptions)
        
        # Add variety: sometimes use merchant only, sometimes combine
        if random.random() < 0.7:
            text = merchant
        else:
            text = f"{merchant} {description}"
        
        samples.append({
            'merchant_canonical': merchant,
            'description': description,
            'category': category
        })
    
    return samples


def create_training_dataset(samples_per_category: int = 50):
    """Create comprehensive training dataset"""
    all_samples = []
    
    for category in MERCHANTS_BY_CATEGORY.keys():
        category_samples = generate_training_samples(category, samples_per_category)
        all_samples.extend(category_samples)
        print(f"Generated {len(category_samples)} samples for {category}")
    
    # Shuffle for randomness
    random.shuffle(all_samples)
    
    print(f"\nTotal samples generated: {len(all_samples)}")
    print(f"Categories: {len(MERCHANTS_BY_CATEGORY)}")
    print(f"Average per category: {len(all_samples) // len(MERCHANTS_BY_CATEGORY)}")
    
    return all_samples


def save_training_data(samples: list, output_file: Path):
    """Save training data to JSONL file"""
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_file, 'w') as f:
        for sample in samples:
            f.write(json.dumps(sample) + '\n')
    
    print(f"\nSaved to: {output_file}")


def load_existing_data(file_path: Path) -> list:
    """Load existing training data"""
    if not file_path.exists():
        return []
    
    samples = []
    with open(file_path, 'r') as f:
        for line in f:
            samples.append(json.loads(line.strip()))
    
    return samples


def main():
    parser = argparse.ArgumentParser(
        description='Generate training data for ML Categorizer'
    )
    parser.add_argument(
        '--samples-per-category',
        type=int,
        default=50,
        help='Number of samples to generate per category (default: 50)'
    )
    parser.add_argument(
        '--output',
        type=str,
        default='ml/training_data/labeled_transactions.jsonl',
        help='Output file path'
    )
    parser.add_argument(
        '--append',
        action='store_true',
        help='Append to existing data instead of overwriting'
    )
    
    args = parser.parse_args()
    
    output_file = Path(args.output)
    
    # Load existing data if appending
    existing_samples = []
    if args.append and output_file.exists():
        existing_samples = load_existing_data(output_file)
        print(f"Loaded {len(existing_samples)} existing samples")
    
    # Generate new samples
    print(f"\nGenerating {args.samples_per_category} samples per category...")
    new_samples = create_training_dataset(args.samples_per_category)
    
    # Combine with existing if appending
    if args.append:
        all_samples = existing_samples + new_samples
        print(f"\nTotal samples (including existing): {len(all_samples)}")
    else:
        all_samples = new_samples
    
    # Save
    save_training_data(all_samples, output_file)


if __name__ == "__main__":
    main()

