"""
Base Credit Card Parser - Abstract Base Class

Defines interface for credit card statement parsers.
Bank-specific parsers inherit from this class.

Key differences from regular account parsers:
- Handles card numbers (masked/partial)
- EMI amortization split detection
- Payment detection (negative amounts)
- Interest/GST parsing
- Reward points tracking
"""

import pandas as pd
import re
import logging
from abc import ABC, abstractmethod
from typing import List, Dict, Optional, Tuple
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)


class BaseCreditCardParser(ABC):
    """
    Abstract base class for credit card statement parsers
    
    Provides common functionality for:
    - File reading (CSV/PDF)
    - Metadata extraction
    - Transaction normalization
    - EMI/payment detection
    """
    
    def __init__(self, bank_name: str):
        """
        Initialize credit card parser
        
        Args:
            bank_name: Bank name (e.g., 'ICICI', 'HDFC', 'Axis')
        """
        self.bank_name = bank_name
        self.metadata = {}
    
    @abstractmethod
    def parse(self, file_path: str) -> Tuple[List[Dict], Dict]:
        """
        Parse credit card statement
        
        Args:
            file_path: Path to statement file (CSV or PDF)
            
        Returns:
            Tuple of (transactions list, metadata dict)
        """
        pass
    
    @abstractmethod
    def _extract_metadata(self, file_path: str) -> Dict:
        """
        Extract metadata from statement header
        
        Returns metadata dict with:
        - card_number (full or masked)
        - card_last_4_digits
        - account_number (linked account)
        - customer_name
        - bank_name
        - billing_period (optional)
        
        Args:
            file_path: Path to file
            
        Returns:
            Metadata dictionary
        """
        pass
    
    @abstractmethod
    def _parse_transactions(self, file_path: str, metadata: Dict) -> List[Dict]:
        """
        Parse transactions from statement
        
        Args:
            file_path: Path to statement file
            metadata: Extracted metadata
            
        Returns:
            List of transaction dictionaries
        """
        pass
    
    def _normalize_date(self, date_str: str) -> Optional[str]:
        """
        Normalize date string to YYYY-MM-DD format
        
        Args:
            date_str: Date string in various formats
            
        Returns:
            Normalized date string or None
        """
        if not date_str or pd.isna(date_str):
            return None
        
        date_str = str(date_str).strip()
        
        # Try multiple date formats
        formats = [
            '%d-%b-%y',      # 26-APR-24
            '%d-%m-%y',      # 26-04-24
            '%d/%m/%Y',      # 26/04/2024
            '%d-%m-%Y',      # 26-04-2024
            '%Y-%m-%d',      # 2024-04-26
            '%d/%b/%Y',      # 26/Apr/2024
            '%d %b %Y',      # 26 Apr 2024
        ]
        
        for fmt in formats:
            try:
                date_obj = datetime.strptime(date_str, fmt)
                return date_obj.strftime('%Y-%m-%d')
            except ValueError:
                continue
        
        logger.warning(f"Could not parse date: {date_str}")
        return None
    
    def _normalize_amount(self, amount_str: str) -> float:
        """
        Normalize amount string to float
        
        Handles:
        - Thousand separators (commas)
        - Decimal points
        - Negative amounts (parentheses or minus sign)
        
        Args:
            amount_str: Amount string
            
        Returns:
            Float amount (negative for credits/payments)
        """
        if not amount_str or pd.isna(amount_str):
            return 0.0
        
        amount_str = str(amount_str).strip()
        
        # Remove thousand separators
        amount_str = amount_str.replace(',', '')
        
        # Handle negative amounts in parentheses: (1000) -> -1000
        if amount_str.startswith('(') and amount_str.endswith(')'):
            amount_str = '-' + amount_str[1:-1]
        
        try:
            return float(amount_str)
        except ValueError:
            logger.warning(f"Could not parse amount: {amount_str}")
            return 0.0
    
    def _identify_transaction_type(self, amount: float, description: str) -> str:
        """
        Identify transaction type from amount and description
        
        Logic:
        - Negative amounts = credit (payment)
        - Positive amounts with EMI keywords = debit (purchase/EMI)
        - Interest/GST = debit (charges)
        
        Args:
            amount: Transaction amount
            description: Transaction description
            
        Returns:
            'debit' or 'credit'
        """
        desc_lower = str(description).lower()
        
        # Payment keywords
        payment_keywords = [
            'payment received', 'bbps payment', 'infinity payment',
            'payment thank you', 'payment'
        ]
        
        if any(kw in desc_lower for kw in payment_keywords):
            return 'credit'  # Payment to credit card
        
        # Amount-based: negative = credit (payment)
        if amount < 0:
            return 'credit'
        
        # Positive amount = debit (expense/purchase)
        return 'debit'
    
    def _extract_card_number_from_text(self, text: str) -> Optional[str]:
        """
        Extract masked card number from text
        
        Patterns:
        - "4375 XXXX XXXX 7003"
        - "XXXX XXXX XXXX 1234"
        
        Args:
            text: Text containing card number
            
        Returns:
            Card number string or None
        """
        if not text:
            return None
        
        # Pattern: XXXX XXXX XXXX 1234 or 1234 XXXX XXXX 1234
        patterns = [
            r'(\d{4}\s*XXXX\s*XXXX\s*\d{4})',  # Last 4 visible
            r'(XXXX\s*XXXX\s*XXXX\s*\d{4})',   # Only last 4 visible
            r'(\d{4}\s*\d{4}\s*\d{4}\s*\d{4})', # Full card (if unmasked)
        ]
        
        for pattern in patterns:
            match = re.search(pattern, str(text))
            if match:
                return match.group(1)
        
        return None
    
    def _extract_last_4_digits(self, card_number: Optional[str]) -> Optional[str]:
        """
        Extract last 4 digits from card number
        
        Args:
            card_number: Full or masked card number
            
        Returns:
            Last 4 digits or None
        """
        if not card_number:
            return None
        
        # Extract numeric digits
        digits = re.findall(r'\d', card_number)
        if len(digits) >= 4:
            return ''.join(digits[-4:])
        
        return None
    
    def _is_emi_transaction(self, description: str) -> bool:
        """
        Check if transaction is related to EMI
        
        Args:
            description: Transaction description
            
        Returns:
            True if EMI-related
        """
        desc_lower = str(description).lower()
        emi_keywords = [
            'emi', 'amortization', 'principal amount',
            'interest amount', 'installment'
        ]
        return any(kw in desc_lower for kw in emi_keywords)
    
    def _is_charge_transaction(self, description: str) -> bool:
        """
        Check if transaction is a charge (interest, GST, fees)
        
        Args:
            description: Transaction description
            
        Returns:
            True if charge-related
        """
        desc_lower = str(description).lower()
        charge_keywords = [
            'interest', 'gst', 'igst', 'cgst', 'sgst',
            'fee', 'charges', 'late fee', 'annual fee'
        ]
        return any(kw in desc_lower for kw in charge_keywords)
    
    def _parse_emi_amortization(self, transactions: List[Dict]) -> List[Dict]:
        """
        Consolidate EMI amortization transactions
        
        EMI transactions are often split into multiple rows:
        - Principal Amount Amortization - <1/3>Merchant Name
        - Interest Amount Amortization - <1/3>Merchant Name
        - IGST-CI@18%
        
        This method consolidates them into a single transaction per installment.
        All EMI-related entries for the same installment are grouped together.
        
        Args:
            transactions: List of transaction dictionaries
            
        Returns:
            Consolidated list of transactions
        """
        consolidated = []
        skip_indices = set()
        
        for idx, txn in enumerate(transactions):
            if idx in skip_indices:
                continue
            
            description = txn.get('description', '')
            txn_date = txn.get('date', '')
            
            # Check if this is part of an EMI amortization
            if self._is_emi_transaction(description):
                # Look ahead to find all related EMI transactions
                emi_group = [txn]
                emi_amounts = [txn.get('amount', 0)]
                
                # Parse merchant name and installment number from EMI description
                # Pattern: "Principal Amount Amortization - <1/3>Merchant Name"
                merchant_match = re.search(r'<[^>]+>(.+?)$', description)
                merchant = merchant_match.group(1).strip() if merchant_match else 'EMI Payment'
                installment_match = re.search(r'<(\d+)/\d+>', description)
                installment_num = installment_match.group(1) if installment_match else None
                
                # First, look backward to find any preceding GST/charges
                # Look back up to 20 rows to catch all GST entries for the same date
                for prev_idx in range(max(0, idx - 20), idx):
                    if prev_idx in skip_indices:
                        continue
                        
                    prev_txn = transactions[prev_idx]
                    prev_desc = prev_txn.get('description', '')
                    prev_date = prev_txn.get('date', '')
                    
                    # Only process entries from the same date
                    if prev_date != txn_date:
                        continue
                    
                    # If it's a charge (GST), add it to the group
                    if self._is_charge_transaction(prev_desc) and not self._is_emi_transaction(prev_desc):
                        emi_group.insert(0, prev_txn)  # Insert at beginning to maintain order
                        emi_amounts.insert(0, prev_txn.get('amount', 0))
                        skip_indices.add(prev_idx)
                
                # Then, look ahead to find all related EMI transactions
                for next_idx in range(idx + 1, min(idx + 11, len(transactions))):
                    if next_idx in skip_indices:
                        continue
                        
                    next_txn = transactions[next_idx]
                    next_desc = next_txn.get('description', '')
                    next_date = next_txn.get('date', '')
                    
                    # Only process entries from the same date to avoid mixing installments
                    if next_date != txn_date:
                        continue
                    
                    # Check if this is part of the same EMI installment
                    is_charge = self._is_charge_transaction(next_desc)
                    is_emi = self._is_emi_transaction(next_desc)
                    
                    if is_charge and not is_emi:
                        # This is a GST/charge - add it if we're still in the same EMI group
                        emi_group.append(next_txn)
                        emi_amounts.append(next_txn.get('amount', 0))
                        skip_indices.add(next_idx)
                    elif is_emi and installment_num:
                        # This is an EMI entry - check if same installment
                        next_installment_match = re.search(r'<(\d+)/\d+>', next_desc)
                        next_installment_num = next_installment_match.group(1) if next_installment_match else None
                        
                        # Also check if same merchant (extract from description)
                        next_merchant_match = re.search(r'<[^>]+>(.+?)$', next_desc)
                        next_merchant = next_merchant_match.group(1).strip() if next_merchant_match else ''
                        
                        # Only add if same installment number AND same merchant
                        if (next_installment_num == installment_num and 
                            next_merchant.lower() == merchant.lower()):
                            emi_group.append(next_txn)
                            emi_amounts.append(next_txn.get('amount', 0))
                            skip_indices.add(next_idx)
                
                # Consolidate EMI transactions
                total_amount = sum(emi_amounts)
                
                # Preserve original raw description for reference
                original_desc = txn.get('description', description)
                
                consolidated_txn = {
                    **txn,  # Keep original fields
                    'description': f'{merchant} EMI',
                    'amount': total_amount,
                    'merchant_raw': merchant,  # Use extracted merchant name
                    'merchant_canonical': merchant,  # Use extracted merchant name
                    'category': 'EMI & Loans',
                    'labels': ['EMI', 'Amortization'],
                    'extra_metadata': {
                        'emi_installments': len(emi_group),
                        'emi_breakdown': [
                            {'type': e.get('description', ''), 'amount': e.get('amount', 0)}
                            for e in emi_group
                        ],
                        'original_description': original_desc
                    }
                }
                consolidated.append(consolidated_txn)
            else:
                # Regular transaction, add as-is
                consolidated.append(txn)
        
        return consolidated
    
    def create_transaction_dict(
        self,
        date: str,
        description: str,
        amount: float,
        metadata: Dict
    ) -> Dict:
        """
        Create standardized transaction dictionary
        
        Args:
            date: Transaction date (will be normalized)
            description: Transaction description
            amount: Transaction amount
            metadata: Metadata from statement
            
        Returns:
            Transaction dictionary in legacy format
        """
        from ingestion.transaction_formatter import create_transaction_dict as _create_dict
        
        # Normalize date
        normalized_date = self._normalize_date(date)
        if not normalized_date:
            return None
        
        # Identify transaction type
        txn_type = self._identify_transaction_type(amount, description)
        
        # Use absolute amount for legacy format
        abs_amount = abs(amount)
        
        # Create base transaction dict
        txn_dict = {
            'transaction_id': self._generate_transaction_id(),
            'date': normalized_date,
            'description': description,
            'amount': abs_amount,
            'type': txn_type,
            'source': 'credit_card_csv',
            'bank_name': self.bank_name,
            'account_type': 'credit_card',
        }
        
        # Add metadata
        if metadata.get('card_last_4_digits'):
            txn_dict['extra_metadata'] = {
                'card_last_4': metadata['card_last_4_digits']
            }
        
        # Add debit/credit fields for legacy compatibility
        if txn_type == 'debit':
            txn_dict['withdrawal'] = abs_amount
            txn_dict['deposit'] = 0.0
        else:
            txn_dict['withdrawal'] = 0.0
            txn_dict['deposit'] = abs_amount
        
        return txn_dict
    
    def _generate_transaction_id(self) -> str:
        """
        Generate unique transaction ID
        
        Returns:
            UUID string
        """
        import uuid
        return str(uuid.uuid4())
    
    def get_metadata(self) -> Dict:
        """
        Get extracted metadata
        
        Returns:
            Metadata dictionary
        """
        return self.metadata

