"""Merchant normalization using fuzzy matching (rapidfuzz).

Contains a small canonical merchant list and logic to map messy merchant strings to canonical names.
"""
from typing import Tuple, Optional, List, Dict
from rapidfuzz import process, fuzz

CANONICAL_MERCHANTS: List[str] = [
    # Food & Delivery
    "Apollo Pharmacy",
    "Swiggy",
    "Zomato",
    "Burger King",
    "Zepto",

    # Streaming & Entertainment
    "Netflix",

    # Financial Services
    "Finzoom",
    "Indmoney",
    "Groww",
    "CanfinHomes",
    "CRED",
    "Kotak Mahindra",
    "SBI Life",
    "State Bank Life",
    "Life Insurance",
    "Payment",
    "BBPS Payment",
    "Infinity Payment",

    # IT Companies & Employers (for salary identification)
    "Infosys",
    "TCS",
    "Tata Consultancy Services",
    "Wipro",
    "HCL Technologies",
    "HCL",
    "Tech Mahindra",
    "Cognizant",
    "Accenture",
    "Capgemini",
    "IBM",
    "Microsoft",
    "Google",
    "Amazon",
    "Flipkart",
    "Paytm",
    "PhonePe",
    "Razorpay",

    # Fuel & Petroleum
    "HP",
    "Hindustan Petroleum",
    "Hindustan Petroleum Corporation",
    "HP Petro",
    "HP Pay Dir",
    "HPCL",
    "Indian Oil",
    "Indian Oil Corporation",
    "BPCL",
    "Bharat Petroleum",
    "Bharat Petroleum Corporation",
    "Reliance Petroleum",
    "Reliance Industries",
    "Shell India",
    "Shell",
    "Essar Oil",
    "Essar",
    "Total Oil",
    "Total",
    "Chevron",
    "Castrol",
    "Gulf Oil",
    "Gulf",
    "IOC",
    "IndianOil",
    "BPCL Petro",
    "Bharat Gas",
    
    # Education
    "HDFC School",
    "Ample Technologies",
    "VFS Global",
    "Tutorials Dojo",
    "PVR INOX",
    
    # Retail
    "Reliance Retail",
]


class MerchantNormalizer:
    def __init__(self, canonicals: Optional[List[str]] = None, threshold: int = 85):
        self.canonicals = canonicals or CANONICAL_MERCHANTS
        self.threshold = threshold  # Increased from 70 to 85 for better accuracy

    def normalize(self, raw: Optional[str]) -> Tuple[str, int]:
        if not raw:
            return "Other", 0

        # First check for exact substring matches (case-insensitive)
        raw_lower = raw.lower()
        for canonical in self.canonicals:
            canonical_lower = canonical.lower()
            # Check if canonical name is in raw string
            if canonical_lower in raw_lower:
                return canonical, 100
            # Check if ANY significant word from canonical starts the raw string
            # (for cases like "Apollo Dia" matching "Apollo Pharmacy")
            # But skip common generic words that cause false matches
            common_words = {'indian', 'national', 'state', 'city', 'bank', 'limited', 'ltd', 'corp', 'corporation'}
            canonical_words = [w for w in canonical_lower.split() if w not in common_words and len(w) >= 3]

            # Check if the first significant word of canonical matches start of raw
            # Use word boundaries to avoid false matches (e.g., "tech" in "technology")
            if canonical_words:
                first_word = canonical_words[0]
                raw_words = raw_lower.split()
                
                # Only match if there are at least 2 significant words in canonical
                # to avoid false matches (e.g., "Reliance" matching "Reliance Petroleum" when actual is "Reliance Retail")
                if len(canonical_words) >= 2 and raw_words:
                    # Check if at least 2 words match (not just the first)
                    matching_words = sum(1 for w in canonical_words if w in raw_words)
                    if matching_words >= 2:
                        return canonical, 90
                # For single-word canonicals, only match if it's exact first word
                elif raw_words and raw_words[0] == first_word:
                    return canonical, 90

        # use rapidfuzz to get best match
        match = process.extractOne(raw, self.canonicals, scorer=fuzz.token_sort_ratio)
        if not match:
            return "Other", 0
        name, score, _ = match
        if score >= self.threshold:
            return name, int(score)
        # try partial ratio with higher threshold
        partial = process.extractOne(raw, self.canonicals, scorer=fuzz.partial_ratio)
        if partial and partial[1] >= self.threshold:
            return partial[0], int(partial[1])
        return "Other", int(score)
