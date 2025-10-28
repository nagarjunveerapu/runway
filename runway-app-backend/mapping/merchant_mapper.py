"""
Merchant Mapper with Fuzzy Matching

Maps raw merchant names from bank statements to canonical merchant names.
Uses rapidfuzz for fuzzy string matching to handle variations.
"""

import json
import logging
from typing import Dict, Optional, Tuple
from pathlib import Path
from rapidfuzz import fuzz, process

logger = logging.getLogger(__name__)


class MerchantMapper:
    """
    Maps raw merchant names to canonical names using fuzzy matching

    Example:
        "SWIGGY BANGALORE" → "Swiggy"
        "AMAZON PAY INDIA" → "Amazon"
        "HDFC NETBANKING" → "HDFC Bank"
    """

    def __init__(self, mapping_file: str = "data/merchant_mappings.json"):
        """
        Initialize merchant mapper

        Args:
            mapping_file: Path to merchant mappings JSON file
        """
        self.mapping_file = Path(mapping_file)
        self.mappings: Dict[str, Dict] = {}
        self.canonical_names = set()

        # Load mappings if file exists
        self.load_mappings()

        # Build default mappings
        self._build_default_mappings()

    def load_mappings(self):
        """Load merchant mappings from file"""
        if self.mapping_file.exists():
            try:
                with open(self.mapping_file, 'r') as f:
                    data = json.load(f)
                    self.mappings = data.get('mappings', {})
                    logger.info(f"Loaded {len(self.mappings)} merchant mappings from {self.mapping_file}")
            except Exception as e:
                logger.warning(f"Failed to load mappings from {self.mapping_file}: {e}")
        else:
            logger.info(f"Mappings file not found: {self.mapping_file}, using defaults only")

        # Update canonical names set
        self.canonical_names = set(m['canonical'] for m in self.mappings.values())

    def save_mappings(self):
        """Save merchant mappings to file"""
        self.mapping_file.parent.mkdir(parents=True, exist_ok=True)

        data = {
            'mappings': self.mappings,
            'metadata': {
                'total_mappings': len(self.mappings),
                'canonical_merchants': len(self.canonical_names),
            }
        }

        with open(self.mapping_file, 'w') as f:
            json.dump(data, f, indent=2)

        logger.info(f"Saved {len(self.mappings)} merchant mappings to {self.mapping_file}")

    def _build_default_mappings(self):
        """Build default merchant mappings for common Indian merchants"""
        defaults = {
            # Food delivery
            'swiggy': {'canonical': 'Swiggy', 'category': 'Food & Dining'},
            'zomato': {'canonical': 'Zomato', 'category': 'Food & Dining'},
            'dominos': {'canonical': 'Dominos Pizza', 'category': 'Food & Dining'},
            'mcdonald': {'canonical': 'McDonalds', 'category': 'Food & Dining'},
            'kfc': {'canonical': 'KFC', 'category': 'Food & Dining'},
            'starbucks': {'canonical': 'Starbucks', 'category': 'Food & Dining'},

            # E-commerce
            'amazon': {'canonical': 'Amazon', 'category': 'Shopping'},
            'flipkart': {'canonical': 'Flipkart', 'category': 'Shopping'},
            'myntra': {'canonical': 'Myntra', 'category': 'Shopping'},
            'ajio': {'canonical': 'Ajio', 'category': 'Shopping'},
            'meesho': {'canonical': 'Meesho', 'category': 'Shopping'},

            # Transport
            'uber': {'canonical': 'Uber', 'category': 'Transport'},
            'ola': {'canonical': 'Ola', 'category': 'Transport'},
            'rapido': {'canonical': 'Rapido', 'category': 'Transport'},
            'irctc': {'canonical': 'IRCTC', 'category': 'Travel'},

            # Entertainment
            'netflix': {'canonical': 'Netflix', 'category': 'Entertainment'},
            'prime video': {'canonical': 'Amazon Prime Video', 'category': 'Entertainment'},
            'hotstar': {'canonical': 'Disney+ Hotstar', 'category': 'Entertainment'},
            'spotify': {'canonical': 'Spotify', 'category': 'Entertainment'},
            'bookmyshow': {'canonical': 'BookMyShow', 'category': 'Entertainment'},

            # Groceries
            'bigbasket': {'canonical': 'BigBasket', 'category': 'Groceries'},
            'blinkit': {'canonical': 'Blinkit', 'category': 'Groceries'},
            'zepto': {'canonical': 'Zepto', 'category': 'Groceries'},
            'instamart': {'canonical': 'Swiggy Instamart', 'category': 'Groceries'},

            # Utilities
            'jio': {'canonical': 'Reliance Jio', 'category': 'Bills & Utilities'},
            'airtel': {'canonical': 'Airtel', 'category': 'Bills & Utilities'},
            'vodafone': {'canonical': 'Vodafone Idea', 'category': 'Bills & Utilities'},
            'paytm': {'canonical': 'Paytm', 'category': 'Transfer'},
            'phonepe': {'canonical': 'PhonePe', 'category': 'Transfer'},
            'googlepay': {'canonical': 'Google Pay', 'category': 'Transfer'},
            'gpay': {'canonical': 'Google Pay', 'category': 'Transfer'},

            # Banks (for transfers)
            'hdfc': {'canonical': 'HDFC Bank', 'category': 'Transfer'},
            'icici': {'canonical': 'ICICI Bank', 'category': 'Transfer'},
            'sbi': {'canonical': 'State Bank of India', 'category': 'Transfer'},
            'axis': {'canonical': 'Axis Bank', 'category': 'Transfer'},
            'kotak': {'canonical': 'Kotak Mahindra Bank', 'category': 'Transfer'},
        }

        # Add defaults if not already in mappings
        for key, value in defaults.items():
            if key.lower() not in self.mappings:
                self.mappings[key.lower()] = value

        # Update canonical names
        self.canonical_names = set(m['canonical'] for m in self.mappings.values())

    def map_merchant(self, merchant_raw: str, threshold: int = 80) -> Tuple[str, Optional[str], float]:
        """
        Map raw merchant name to canonical name

        Args:
            merchant_raw: Raw merchant name from statement
            threshold: Fuzzy match threshold (0-100)

        Returns:
            Tuple of (canonical_name, category, confidence)
        """
        if not merchant_raw:
            return merchant_raw, None, 0.0

        merchant_raw = str(merchant_raw).strip()
        merchant_lower = merchant_raw.lower()

        # Check for exact match
        if merchant_lower in self.mappings:
            mapping = self.mappings[merchant_lower]
            return mapping['canonical'], mapping.get('category'), 1.0

        # Try fuzzy matching
        best_match = self._fuzzy_match(merchant_raw, threshold)

        if best_match:
            canonical, category, confidence = best_match
            return canonical, category, confidence / 100.0

        # No match found - return raw name
        return merchant_raw, None, 0.0

    def _fuzzy_match(self, merchant_raw: str, threshold: int) -> Optional[Tuple[str, Optional[str], float]]:
        """
        Perform fuzzy matching against known merchant names

        Args:
            merchant_raw: Raw merchant name
            threshold: Minimum similarity threshold (0-100)

        Returns:
            Tuple of (canonical_name, category, confidence) or None
        """
        # Extract all mapping keys (raw merchant patterns)
        keys = list(self.mappings.keys())

        if not keys:
            return None

        # Use rapidfuzz to find best match
        # token_sort_ratio handles word order variations
        result = process.extractOne(
            merchant_raw.lower(),
            keys,
            scorer=fuzz.token_sort_ratio
        )

        if result and result[1] >= threshold:
            matched_key, score, _ = result
            mapping = self.mappings[matched_key]
            return mapping['canonical'], mapping.get('category'), score

        return None

    def add_mapping(self, merchant_raw: str, merchant_canonical: str, category: Optional[str] = None):
        """
        Add a new merchant mapping

        Args:
            merchant_raw: Raw merchant name pattern
            merchant_canonical: Canonical merchant name
            category: Transaction category
        """
        key = merchant_raw.lower().strip()

        self.mappings[key] = {
            'canonical': merchant_canonical,
            'category': category,
        }

        self.canonical_names.add(merchant_canonical)
        logger.info(f"Added mapping: '{merchant_raw}' → '{merchant_canonical}' ({category})")

    def remove_mapping(self, merchant_raw: str):
        """Remove a merchant mapping"""
        key = merchant_raw.lower().strip()

        if key in self.mappings:
            del self.mappings[key]
            logger.info(f"Removed mapping: '{merchant_raw}'")
        else:
            logger.warning(f"Mapping not found: '{merchant_raw}'")

    def get_stats(self) -> Dict:
        """Get mapping statistics"""
        return {
            'total_mappings': len(self.mappings),
            'canonical_merchants': len(self.canonical_names),
            'categories': len(set(m.get('category') for m in self.mappings.values() if m.get('category'))),
        }


# Example usage
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    mapper = MerchantMapper()

    # Test mappings
    test_merchants = [
        "SWIGGY BANGALORE",
        "AMAZON PAY INDIA",
        "UPI PHONEPE MERCHANT",
        "NETFLIX.COM",
        "IRCTC RAIL TICKET",
        "UNKNOWN MERCHANT XYZ",
    ]

    print("\nMerchant Mapping Examples:")
    print("-" * 80)
    for merchant in test_merchants:
        canonical, category, confidence = mapper.map_merchant(merchant, threshold=70)
        print(f"{merchant:30} → {canonical:20} ({category:15}) [conf: {confidence:.2f}]")

    print(f"\nMapper stats: {mapper.get_stats()}")
