"""
ICICI Bank Credit Card Statement Parser

Handles ICICI-specific credit card statement formats:
- CSV format with specific column layout
- Masked card number detection
- EMI amortization handling
- Payment detection
"""

import pandas as pd
import re
import logging
import csv
from typing import List, Dict, Optional, Tuple
from pathlib import Path

from ingestion.credit_card.base_credit_card_parser import BaseCreditCardParser

logger = logging.getLogger(__name__)


class ICICICreditCardParser(BaseCreditCardParser):
    """
    ICICI Bank Credit Card Statement Parser
    
    Handles CSV statements with specific format:
    - Metadata rows (Accountno, Customer Name, Address)
    - Transaction Details header
    - Masked card number row
    - Transaction rows with Date, Sr.No., Transaction Details, etc.
    """
    
    def __init__(self):
        super().__init__(bank_name='ICICI Bank')
    
    def parse(self, file_path: str) -> Tuple[List[Dict], Dict]:
        """
        Parse ICICI credit card CSV statement
        
        Args:
            file_path: Path to CSV file
            
        Returns:
            Tuple of (transactions list, metadata dict)
        """
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        logger.info(f"Parsing ICICI credit card statement: {file_path}")
        
        # Extract metadata
        metadata = self._extract_metadata(file_path)
        self.metadata = metadata
        
        # Parse transactions
        transactions = self._parse_transactions(file_path, metadata)
        
        logger.info(f"Extracted {len(transactions)} transactions from ICICI credit card statement")
        return transactions, metadata
    
    def _extract_metadata(self, file_path: str) -> Dict:
        """
        Extract metadata from ICICI credit card CSV
        
        Expected format:
        "Accountno:","0000000009905086"
        "Customer Name:","MR. V NAGARJUN"
        
        Args:
            file_path: Path to CSV file
            
        Returns:
            Metadata dictionary
        """
        metadata = {
            'card_number': None,
            'card_last_4_digits': None,
            'account_number': None,
            'customer_name': None,
            'bank_name': 'ICICI Bank',
            'account_type': 'credit_card',
            'card_holder_address': None
        }
        
        # Read file to extract metadata from first rows
        try:
            # Use csv module to read properly (handles quoted fields)
            
            # Try multiple encodings
            encodings = ['utf-8-sig', 'utf-8', 'latin-1', 'cp1252']
            rows = None
            
            for enc in encodings:
                try:
                    with open(file_path, 'r', encoding=enc) as f:
                        reader = csv.reader(f)
                        rows = [row for row in reader]
                    logger.info(f"Successfully read CSV with encoding: {enc}")
                    break
                except Exception as e:
                    logger.debug(f"Failed with encoding {enc}: {e}")
                    continue
            
            if rows is None or not rows:
                logger.warning("Could not read CSV for metadata extraction")
                return metadata
            
            # Extract metadata from first few rows
            for idx in range(min(10, len(rows))):
                row_values = [val.strip() for val in rows[idx] if val and val.strip()]
                
                if not row_values:
                    continue
                
                # Check for Accountno
                if len(row_values) >= 2 and 'accountno' in row_values[0].lower():
                    metadata['account_number'] = row_values[1]
                    logger.info(f"✅ Extracted account number: {metadata['account_number']}")
                
                # Check for Customer Name
                if len(row_values) >= 2 and 'customer name' in row_values[0].lower():
                    metadata['customer_name'] = row_values[1]
                    logger.info(f"✅ Extracted customer name: {metadata['customer_name']}")
                
                # Check for Address
                if len(row_values) >= 2 and 'address' in row_values[0].lower():
                    metadata['card_holder_address'] = row_values[1]
                    logger.info(f"✅ Extracted address")
            
            # Extract card number from statement (typically row 8)
            card_number = self._extract_card_number_from_statement(file_path)
            if card_number:
                metadata['card_number'] = card_number
                metadata['card_last_4_digits'] = self._extract_last_4_digits(card_number)
                logger.info(f"✅ Extracted card number: {card_number} (last 4: {metadata['card_last_4_digits']})")
        
        except Exception as e:
            logger.error(f"Error extracting metadata: {e}")
        
        return metadata
    
    def _extract_card_number_from_statement(self, file_path: str) -> Optional[str]:
        """
        Extract masked card number from statement
        
        Typically appears as: "4375 XXXX XXXX 7003"
        
        Args:
            file_path: Path to CSV file
            
        Returns:
            Card number string or None
        """
        try:
            # Read first 10 rows to find card number using csv module
            encodings = ['utf-8-sig', 'utf-8', 'latin-1', 'cp1252']
            
            for enc in encodings:
                try:
                    with open(file_path, 'r', encoding=enc) as f:
                        reader = csv.reader(f)
                        rows = [row for row in reader][:10]
                    
                    for row in rows:
                        for val in row:
                            if val and 'XXXX' in val:
                                return val
                    
                    break
                except Exception:
                    continue
        except Exception as e:
            logger.error(f"Error extracting card number: {e}")
        
        return None
    
    def _parse_transactions(self, file_path: str, metadata: Dict) -> List[Dict]:
        """
        Parse transactions from ICICI credit card CSV
        
        Expected format:
        - Transaction Details header at row 7
        - Card number at row 8
        - Transaction rows start at row 9
        
        Args:
            file_path: Path to CSV file
            metadata: Extracted metadata
            
        Returns:
            List of transaction dictionaries
        """
        transactions = []
        
        try:
            # Try multiple encodings
            encodings = ['utf-8-sig', 'utf-8', 'latin-1', 'cp1252']
            rows = None
            
            for enc in encodings:
                try:
                    with open(file_path, 'r', encoding=enc) as f:
                        reader = csv.reader(f)
                        rows = [row for row in reader]
                    logger.info(f"Successfully read CSV with encoding: {enc}")
                    break
                except Exception as e:
                    logger.debug(f"Failed with encoding {enc}: {e}")
                    continue
            
            if rows is None or not rows:
                raise ValueError("Could not read CSV file")
            
            # Find transaction header row (contains "Transaction Details")
            header_row_idx = None
            for idx in range(min(20, len(rows))):
                if not rows[idx]:
                    continue
                row_values = [val.strip() for val in rows[idx] if val]
                
                # Check if this looks like a header row with column names
                if len(row_values) >= 5:  # Header should have at least 5 columns
                    row_text_lower = ' '.join([val.lower() for val in row_values])
                    
                    # Look for specific header indicators
                    if (row_values[0].lower() == 'date' and 
                        any(col in row_values for col in ['Sr.No.', 'Sr.No', 'Transaction Details', 'Amount(in Rs)'])):
                        header_row_idx = idx
                        logger.info(f"Found transaction header at row {header_row_idx}: {row_values}")
                        break
            
            if header_row_idx is None:
                logger.warning("Could not find transaction header row")
                return transactions
            
            # Create column map from header
            header_row = rows[header_row_idx]
            col_map = {val.strip(): i for i, val in enumerate(header_row)}
            
            # Start parsing from row after header (skip card number row)
            start_row = header_row_idx + 2  # Skip header and card number row
            
            for idx in range(start_row, len(rows)):
                try:
                    row = rows[idx]
                    
                    # Skip if row is empty
                    if not row or all(not val.strip() for val in row if val):
                        continue
                    
                    # Extract transaction fields by column index
                    date_idx = col_map.get('Date', -1)
                    desc_idx = col_map.get('Transaction Details', -1)
                    amount_idx = col_map.get('Amount(in Rs)', -1)
                    reward_idx = col_map.get('Reward Point Header', -1)
                    
                    if date_idx < 0 or desc_idx < 0 or amount_idx < 0:
                        logger.warning("Could not find required columns in header")
                        continue
                    
                    date_str = row[date_idx].strip() if date_idx < len(row) else ''
                    description = row[desc_idx].strip() if desc_idx < len(row) else ''
                    amount_str = row[amount_idx].strip() if amount_idx < len(row) else ''
                    
                    # Skip if essential fields are missing
                    if not date_str or not amount_str:
                        # Check if we've reached message section
                        if date_str and 'message' in date_str.lower():
                            break
                        continue
                    
                    # Skip message section rows
                    row_text_lower = ' '.join([val.lower() for val in row if val])
                    if any(kw in row_text_lower for kw in ['message', 'safe banking', 'gstin', 'registered office']):
                        continue
                    
                    # Normalize amount
                    amount = self._normalize_amount(amount_str)
                    
                    # Skip zero amount transactions
                    if amount == 0:
                        continue
                    
                    # Create transaction dict
                    txn = self.create_transaction_dict(
                        date=date_str,
                        description=description,
                        amount=amount,
                        metadata=metadata
                    )
                    
                    if txn:
                        # Extract merchant from description
                        txn['merchant_raw'] = description
                        txn['merchant_canonical'] = self._extract_merchant_name(description)
                        
                        # Add reward points if available
                        if reward_idx >= 0 and reward_idx < len(row):
                            reward_points = row[reward_idx].strip()
                            if reward_points:
                                try:
                                    txn.setdefault('extra_metadata', {})
                                    txn['extra_metadata']['reward_points'] = int(reward_points)
                                except (ValueError, TypeError):
                                    pass
                        
                        transactions.append(txn)
                
                except Exception as e:
                    logger.warning(f"Error parsing row {idx}: {e}")
                    continue
            
            # Consolidate EMI transactions
            transactions = self._parse_emi_amortization(transactions)
        
        except Exception as e:
            logger.error(f"Error parsing transactions: {e}", exc_info=True)
            raise ValueError(f"Failed to parse ICICI credit card statement: {e}")
        
        return transactions
    
    def _extract_merchant_name(self, description: str) -> str:
        """
        Extract merchant name from description
        
        Pattern examples:
        - "PVR INOX LIMITED BANGALORE IN" -> "PVR INOX LIMITED"
        - "INFINITY PAYMENT RECEIVED, THANK YOU" -> "Payment"
        
        Args:
            description: Transaction description
            
        Returns:
            Merchant name
        """
        if not description:
            return "Unknown"
        
        desc = description.strip()
        
        # Payment keywords
        if any(kw in desc.upper() for kw in ['PAYMENT RECEIVED', 'BBPS PAYMENT', 'INFINITY PAYMENT']):
            return "Payment"
        
        # Remove location suffixes (IN, US, SG*, etc.)
        # Pattern: LAST_WORD COUNTRY_CODE -> remove country code
        desc_clean = re.sub(r'\s+(IN|US|SG|UK|AE|SG\*|USA|INDIA)$', '', desc, flags=re.IGNORECASE)
        
        # Remove common suffixes after country
        desc_clean = re.sub(r'\s+[A-Z]{2}\s*$', '', desc_clean)
        
        # Extract first part (usually merchant name)
        # Split by common separators
        parts = re.split(r'\s+(?:LTD|LIMITED|PVT|PVT\.|LLC|INC|CORP|LLP)', desc_clean, maxsplit=1, flags=re.IGNORECASE)
        merchant = parts[0].strip()
        
        # If merchant is too short or looks like noise, return original
        if len(merchant) < 3:
            return desc[:50]  # Return first 50 chars of description
        
        return merchant

