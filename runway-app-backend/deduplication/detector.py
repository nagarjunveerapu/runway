"""
Transaction Deduplication with Explicit Thresholds

Rules:
1. Same date ± N day window (configurable, default 1)
2. Exact amount match (±0.01 tolerance)
3. Fuzzy merchant similarity ≥ threshold % (default 85%)
4. Keep earliest transaction, flag/merge duplicates

Configuration via config.py or direct params:
- time_window_days: Date tolerance (default: 1)
- amount_tolerance: Amount difference tolerance (default: 0.01)
- fuzzy_threshold: Merchant similarity 0-100 (default: 85)
- merge_duplicates: True = merge, False = flag only (default: True)

Usage:
    from deduplication import DeduplicationDetector
    from config import Config

    detector = DeduplicationDetector(
        time_window_days=Config.DEDUP_TIME_WINDOW_DAYS,
        fuzzy_threshold=Config.DEDUP_FUZZY_THRESHOLD
    )
    clean_txns = detector.detect_duplicates(raw_transactions)
"""

from typing import List, Dict, Optional
from datetime import datetime, timedelta
from rapidfuzz import fuzz
import logging

logger = logging.getLogger(__name__)


class DeduplicationDetector:
    """Detect and merge duplicate transactions with configurable rules"""

    def __init__(self,
                 time_window_days: int = 1,
                 amount_tolerance: float = 0.01,
                 fuzzy_threshold: int = 85,
                 merge_duplicates: bool = True):
        """
        Initialize deduplication detector

        Args:
            time_window_days: Date tolerance window (±N days)
            amount_tolerance: Amount difference tolerance (default 0.01 = 1 paisa)
            fuzzy_threshold: Merchant similarity threshold 0-100 (default 85%)
            merge_duplicates: If True, merge duplicates; if False, only flag
        """
        self.time_window_days = time_window_days
        self.amount_tolerance = amount_tolerance
        self.fuzzy_threshold = fuzzy_threshold
        self.merge_duplicates = merge_duplicates

        logger.info(f"Deduplication initialized: ±{time_window_days}d window, "
                   f"amount_tol={amount_tolerance}, fuzzy≥{fuzzy_threshold}%, "
                   f"merge={merge_duplicates}")

    def detect_duplicates(self, transactions: List[Dict]) -> List[Dict]:
        """
        Detect and handle duplicates in transaction list

        Args:
            transactions: List of transaction dictionaries

        Returns:
            List of transactions with duplicates handled (flagged or merged)
        """
        if not transactions:
            logger.info("No transactions to deduplicate")
            return []

        logger.info(f"Starting deduplication on {len(transactions)} transactions")

        # Sort by date to process chronologically (keeps earliest)
        try:
            sorted_txns = sorted(transactions, key=lambda t: t.get('date', ''))
        except Exception as e:
            logger.error(f"Error sorting transactions: {e}")
            return transactions

        processed = []
        skipped_count = 0

        for i, txn in enumerate(sorted_txns):
            is_duplicate = False

            # Check against previous transactions within reasonable window
            # Limit search to last 100 txns for performance (configurable)
            search_window = min(100, i)
            start_idx = max(0, i - search_window)

            for j in range(start_idx, i):
                prev_txn = sorted_txns[j]

                if self._is_duplicate(txn, prev_txn):
                    # Found duplicate
                    is_duplicate = True
                    skipped_count += 1

                    if self.merge_duplicates:
                        # Merge into existing transaction (increment count)
                        existing = next((t for t in processed
                                       if t.get('transaction_id') == prev_txn.get('transaction_id')),
                                      None)
                        if existing:
                            existing['duplicate_count'] = existing.get('duplicate_count', 0) + 1
                            logger.debug(f"Merged duplicate txn {txn.get('transaction_id', 'unknown')[:8]} "
                                       f"into {prev_txn.get('transaction_id', 'unknown')[:8]}")
                    else:
                        # Flag as duplicate but keep in list
                        txn['is_duplicate'] = True
                        txn['duplicate_of'] = prev_txn.get('transaction_id')
                        txn['duplicate_count'] = 0
                        processed.append(txn)
                        logger.debug(f"Flagged duplicate: {txn.get('transaction_id', 'unknown')[:8]}")

                    break  # Found duplicate, stop searching

            if not is_duplicate:
                # Not a duplicate, add to processed list
                txn['is_duplicate'] = False
                txn['duplicate_count'] = 0
                processed.append(txn)

        logger.info(f"Deduplication complete: {len(transactions)} → {len(processed)} transactions "
                   f"({skipped_count} duplicates {'merged' if self.merge_duplicates else 'flagged'})")

        return processed

    def _is_duplicate(self, txn1: Dict, txn2: Dict) -> bool:
        """
        Check if two transactions are duplicates

        Returns True only if ALL rules match:
        1. Date within time window
        2. Amount matches (within tolerance)
        3. Merchant similarity ≥ threshold

        Args:
            txn1: First transaction
            txn2: Second transaction

        Returns:
            True if duplicate, False otherwise
        """
        # Rule 1: Date within time window (±N days)
        try:
            date1_str = txn1.get('date', '')
            date2_str = txn2.get('date', '')

            if not date1_str or not date2_str:
                return False

            # Handle both YYYY-MM-DD and full ISO 8601 format
            # Split on 'T' to get just the date part
            date1 = datetime.fromisoformat(date1_str.split('T')[0])
            date2 = datetime.fromisoformat(date2_str.split('T')[0])

            date_diff_days = abs((date1 - date2).days)

            if date_diff_days > self.time_window_days:
                return False  # Outside time window

        except (ValueError, AttributeError) as e:
            logger.debug(f"Date parsing error: {e}")
            return False

        # Rule 2: Amount match (within tolerance for float comparison)
        amount1 = float(txn1.get('amount', 0.0))
        amount2 = float(txn2.get('amount', 0.0))

        amount_diff = abs(amount1 - amount2)
        if amount_diff > self.amount_tolerance:
            return False  # Amounts don't match

        # Rule 3: Fuzzy merchant similarity
        # Try multiple fields for merchant identification (in priority order)
        merchant1 = (txn1.get('merchant_canonical') or
                    txn1.get('merchant_raw') or
                    txn1.get('clean_description') or
                    txn1.get('raw_description', ''))
        merchant2 = (txn2.get('merchant_canonical') or
                    txn2.get('merchant_raw') or
                    txn2.get('clean_description') or
                    txn2.get('raw_description', ''))

        if not merchant1 or not merchant2:
            # No merchant info to compare
            return False

        # Use token_sort_ratio for robust fuzzy matching
        # This handles word order differences and extra words
        similarity = fuzz.token_sort_ratio(merchant1, merchant2)

        if similarity < self.fuzzy_threshold:
            return False  # Not similar enough

        # All rules passed - this is a duplicate!
        logger.debug(f"Duplicate detected: {date_diff_days}d apart, "
                    f"₹{amount1:.2f}, {similarity}% similarity "
                    f"({merchant1[:30]}... vs {merchant2[:30]}...)")

        return True

    def get_duplicate_stats(self, transactions: List[Dict]) -> Dict:
        """
        Get statistics about duplicates in transaction list

        Args:
            transactions: List of processed transactions

        Returns:
            Dictionary with duplicate statistics
        """
        if not transactions:
            return {
                'total_transactions': 0,
                'flagged_duplicates': 0,
                'merged_count': 0,
                'unique_transactions': 0,
                'duplicate_rate': 0.0
            }

        total = len(transactions)
        duplicates = sum(1 for t in transactions if t.get('is_duplicate', False))
        merged = sum(t.get('duplicate_count', 0) for t in transactions)

        return {
            'total_transactions': total,
            'flagged_duplicates': duplicates,
            'merged_count': merged,
            'unique_transactions': total - duplicates,
            'duplicate_rate': round(duplicates / total, 4) if total > 0 else 0.0,
            'dedup_config': {
                'time_window_days': self.time_window_days,
                'fuzzy_threshold': self.fuzzy_threshold,
                'merge_mode': self.merge_duplicates
            }
        }


# Usage Example
if __name__ == "__main__":
    # Example usage
    logging.basicConfig(level=logging.INFO)

    detector = DeduplicationDetector(
        time_window_days=1,
        fuzzy_threshold=85,
        merge_duplicates=True
    )

    # Sample transactions
    transactions = [
        {
            'transaction_id': '1',
            'date': '2025-10-26',
            'amount': 100.0,
            'merchant_raw': 'Swiggy Ltd'
        },
        {
            'transaction_id': '2',
            'date': '2025-10-26',
            'amount': 100.0,
            'merchant_raw': 'Swiggy'  # Duplicate - same day, amount, similar merchant
        },
        {
            'transaction_id': '3',
            'date': '2025-10-27',
            'amount': 200.0,
            'merchant_raw': 'Zomato'
        },
        {
            'transaction_id': '4',
            'date': '2025-10-27',
            'amount': 200.0,
            'merchant_raw': 'Zomato Ltd'  # Duplicate
        },
    ]

    print(f"Original: {len(transactions)} transactions")

    # Detect and handle duplicates
    clean = detector.detect_duplicates(transactions)

    print(f"After deduplication: {len(clean)} transactions")

    # Get statistics
    stats = detector.get_duplicate_stats(clean)
    print(f"\nStatistics:")
    for key, value in stats.items():
        print(f"  {key}: {value}")

    # Show results
    print(f"\nProcessed transactions:")
    for txn in clean:
        dup_info = f" [+{txn['duplicate_count']} duplicates]" if txn.get('duplicate_count', 0) > 0 else ""
        print(f"  {txn['transaction_id']}: ₹{txn['amount']} - {txn.get('merchant_raw', 'N/A')}{dup_info}")
