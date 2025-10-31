"""
Transaction Enrichment Service - Business Logic for Transaction Enrichment

Handles merchant normalization, categorization, and deduplication.
"""

import logging
from typing import List, Dict
from deduplication.detector import DeduplicationDetector
from src.merchant_normalizer import MerchantNormalizer
from src.classifier import rule_based_category
from config import Config

logger = logging.getLogger(__name__)


class TransactionEnrichmentService:
    """
    Service for enriching parsed transactions
    
    Handles:
    - Merchant normalization
    - Transaction categorization
    - Duplicate detection and handling
    """
    
    def __init__(self):
        """Initialize enrichment service with required components"""
        self.merchant_normalizer = MerchantNormalizer()
        self.deduplication_detector = DeduplicationDetector(
            time_window_days=Config.DEDUP_TIME_WINDOW_DAYS,
            fuzzy_threshold=Config.DEDUP_FUZZY_THRESHOLD,
            merge_duplicates=Config.DEDUP_MERGE_DUPLICATES
        )
    
    def enrich_transactions(self, transactions: List[Dict]) -> List[Dict]:
        """
        Enrich transactions with merchant normalization and categorization
        
        Args:
            transactions: List of raw transaction dictionaries from parser
            
        Returns:
            List of enriched transaction dictionaries
        """
        enriched = []
        
        for txn in transactions:
            try:
                enriched_txn = self._enrich_single_transaction(txn)
                enriched.append(enriched_txn)
            except Exception as e:
                logger.warning(f"Failed to enrich transaction: {e}")
                # Keep original transaction if enrichment fails
                enriched.append(txn)
                continue
        
        logger.info(f"Enriched {len(enriched)}/{len(transactions)} transactions")
        return enriched
    
    def _enrich_single_transaction(self, txn: Dict) -> Dict:
        """
        Enrich a single transaction
        
        Args:
            txn: Raw transaction dictionary (legacy or new format)
            
        Returns:
            Enriched transaction dictionary
        """
        # Handle different field names from parsers (legacy vs new format)
        # Legacy format: 'remark', 'raw_remark', 'transaction_type'
        # New format: 'description', 'type'
        description = txn.get('remark') or txn.get('description', '')
        merchant_raw = txn.get('merchant_raw') or description
        
        # If merchant_raw already exists (from legacy parser), use it
        # Otherwise, extract from description (from new parser)
        if not merchant_raw or merchant_raw == description:
            # Merchant not extracted yet, will be done by MerchantNormalizer
            pass
        
        # Normalize merchant
        merchant_canonical, score = self.merchant_normalizer.normalize(merchant_raw)
        
        # Categorize
        category = rule_based_category(
            description,
            merchant_canonical
        )
        
        # Add enriched fields
        enriched_txn = txn.copy()
        enriched_txn['merchant_raw'] = merchant_raw
        enriched_txn['merchant_canonical'] = merchant_canonical
        enriched_txn['category'] = category
        
        return enriched_txn
    
    def detect_and_handle_duplicates(self, transactions: List[Dict]) -> tuple[List[Dict], Dict]:
        """
        Detect and handle duplicate transactions
        
        Args:
            transactions: List of enriched transaction dictionaries
            
        Returns:
            Tuple of (cleaned_transactions, duplicate_stats)
            - cleaned_transactions: Transactions with duplicates handled
            - duplicate_stats: Statistics about duplicates found
        """
        # Detect duplicates
        clean_transactions = self.deduplication_detector.detect_duplicates(transactions)
        duplicate_stats = self.deduplication_detector.get_duplicate_stats(clean_transactions)
        
        logger.info(
            f"Deduplication: {len(transactions)} → {len(clean_transactions)} "
            f"({duplicate_stats.get('merged_count', 0)} duplicates merged)"
        )
        
        return clean_transactions, duplicate_stats
    
    def enrich_and_deduplicate(self, transactions: List[Dict]) -> tuple[List[Dict], Dict]:
        """
        Complete enrichment pipeline: enrich + deduplicate
        
        Args:
            transactions: List of raw transaction dictionaries
            
        Returns:
            Tuple of (enriched_transactions, duplicate_stats)
        """
        logger.info("✨ ENRICHMENT SERVICE: Starting enrichment pipeline...")
        logger.info(f"✨ ENRICHMENT SERVICE: Processing {len(transactions)} transactions")
        
        # Step 1: Enrich
        logger.info("✨ ENRICHMENT SERVICE: Step 1 - Enriching transactions (merchant normalization, categorization)...")
        enriched = self.enrich_transactions(transactions)
        logger.info(f"✨ ENRICHMENT SERVICE: ✅ Enriched {len(enriched)} transactions")
        
        # Step 2: Deduplicate
        logger.info("✨ ENRICHMENT SERVICE: Step 2 - Detecting and handling duplicates...")
        cleaned, stats = self.detect_and_handle_duplicates(enriched)
        logger.info(f"✨ ENRICHMENT SERVICE: ✅ Deduplication complete. Duplicates found: {stats.get('merged_count', 0)}")
        
        return cleaned, stats

