"""
Investment Service - Service Layer for Investment Analysis

Provides business logic for:
- Investment transaction detection
- SIP pattern detection
- Portfolio allocation analysis
- Investment insights and recommendations

This service layer separates business logic from route handlers and database operations.
"""

import logging
from typing import List, Optional, Dict
from datetime import datetime
from collections import defaultdict

from storage.database import DatabaseManager
from storage.models import Transaction, SalarySweepConfig, DetectedEMIPattern
from services.investment_detection import InvestmentDetector
from config import Config

logger = logging.getLogger(__name__)


class InvestmentService:
    """
    Service layer for investment analysis
    
    Coordinates between:
    - InvestmentDetector (transaction filtering)
    - Database operations (pattern retrieval)
    - Business logic (SIP detection, portfolio analysis, insights)
    """
    
    def __init__(self, db_manager: DatabaseManager):
        """
        Initialize investment service
        
        Args:
            db_manager: DatabaseManager instance for database operations
        """
        self.db_manager = db_manager
    
    def extract_platform_name(self, txn: Transaction) -> str:
        """Extract meaningful platform name from transaction.
        
        Tries multiple sources in order:
        1. merchant_canonical (if not generic)
        2. merchant_raw (if available and meaningful)
        3. Extract from description for known investment patterns
        4. Fallback to 'Other' if nothing found
        """
        # If merchant_canonical is meaningful, use it
        if txn.merchant_canonical and txn.merchant_canonical.lower() not in ['other', 'unknown', 'others', '']:
            return txn.merchant_canonical
        
        # Try merchant_raw if available
        if txn.merchant_raw and txn.merchant_raw.lower() not in ['other', 'unknown', 'others', '']:
            # Clean up merchant_raw
            merchant = txn.merchant_raw.strip()
            # If it's a recognizable investment entity, use it
            if any(keyword in merchant.lower() for keyword in ['clearing', 'corp', 'trad', 'invest', 'fund', 'mf']):
                return merchant
        
        # Try to extract from description for known patterns
        desc = (txn.description_raw or '').lower()
        
        # Investment clearing houses
        if 'indian clearing corp' in desc or 'clearing corp' in desc:
            return 'Indian Clearing Corp'
        
        # Extract from UPI patterns: UPI/MERCHANT/...
        if 'upi/' in desc:
            parts = desc.split('/')
            if len(parts) >= 2:
                merchant_part = parts[1].strip()
                if merchant_part and len(merchant_part) > 2:
                    # Capitalize properly
                    return merchant_part.title()
        
        # Extract from ACH patterns: ACH/MERCHANT
        if 'ach/' in desc:
            parts = desc.split('/')
            if len(parts) >= 2:
                merchant_part = parts[1].strip()
                if merchant_part and len(merchant_part) > 2:
                    return merchant_part.title()
        
        # Fallback
        return txn.merchant_canonical or txn.merchant_raw or 'Other'
    
    def get_investment_transactions(self, user_id: str) -> List[Transaction]:
        """Get all investment-related transactions using shared detector."""
        return InvestmentDetector.filter_investment_transactions(user_id)
    
    def get_confirmed_investment_patterns(self, user_id: str) -> List[DetectedEMIPattern]:
        """Get confirmed investment patterns from Salary Sweep configuration."""
        session = self.db_manager.get_session()
        try:
            cfg = session.query(SalarySweepConfig).filter(
                SalarySweepConfig.user_id == user_id,
                SalarySweepConfig.is_active == True
            ).first()
            
            if cfg:
                patterns = session.query(DetectedEMIPattern).filter(
                    DetectedEMIPattern.config_id == cfg.config_id,
                    DetectedEMIPattern.is_confirmed == True,
                    DetectedEMIPattern.category == 'Investment'
                ).all()
                return patterns
            
            return []
        finally:
            session.close()
    
    def detect_sips_from_transactions(self, transactions: List[Transaction]) -> List[Dict]:
        """
        Detect SIP patterns from transactions
        
        Logic:
        1. Group by platform
        2. Group by similar amounts
        3. Check for recurring patterns (monthly, quarterly, etc.)
        4. Identify SIPs based on frequency and consistency
        
        Note: This is a wrapper that uses InvestmentDetector.detect_sips
        and converts the results to dictionaries for consistency.
        """
        # Use InvestmentDetector's detect_sips which returns SIPPattern objects
        sip_objects = InvestmentDetector.detect_sips(transactions)
        
        # Convert to dictionaries for consistency
        return [
            {
                'sip_id': sip.sip_id,
                'platform': sip.platform,
                'amount': sip.amount,
                'frequency': sip.frequency,
                'transaction_count': sip.transaction_count,
                'total_invested': sip.total_invested,
                'start_date': sip.start_date,
                'last_transaction_date': sip.last_transaction_date,
                'category': sip.category or 'equity'
            }
            for sip in sip_objects
        ]
    
    def analyze_portfolio_allocation(self, transactions: List[Transaction]) -> Dict:
        """Analyze portfolio allocation based on platform names and transaction patterns."""
        total = sum(txn.amount for txn in transactions) if transactions else 0.0
        
        # For now, categorize based on platform names
        equity = 0.0
        debt = 0.0
        hybrid = 0.0
        unknown = 0.0
        
        for txn in transactions:
            platform = self.extract_platform_name(txn).lower()
            
            # Known equity platforms
            if any(p in platform for p in ['zerodha', 'groww', 'upstox', 'angel', '5paisa']):
                equity += txn.amount  # Likely equities by default
            else:
                unknown += txn.amount
        
        return {
            'equity': equity,
            'debt': debt,
            'hybrid': hybrid,
            'unknown': unknown,
            'total': total
        }
    
    def generate_insights(self, transactions: List[Transaction], sips: List[Dict]) -> List[Dict]:
        """Generate investment insights and recommendations"""
        insights = []
        
        if not transactions:
            insights.append({
                'type': 'info',
                'title': 'No Investments Detected',
                'message': 'Start building wealth with SIPs in equity mutual funds. Consider platforms like Zerodha or Groww for low-cost investing.',
                'action': 'Explore Investment Platforms'
            })
            return insights
        
        total_invested = sum(txn.amount for txn in transactions)
        
        # Check for SIPs
        if not sips:
            insights.append({
                'type': 'opportunity',
                'title': 'No SIPs Detected',
                'message': f'You have ₹{total_invested:,.0f} in investments. Consider setting up SIPs (₹2,000-5,000/month) for disciplined investing.',
                'action': 'Start SIP'
            })
        
        # Portfolio allocation
        if len([sip for sip in sips if 'equity' in (sip.get('category') or '')]) > 0:
            equity_sips = [sip for sip in sips if 'equity' in (sip.get('category') or '')]
            total_equity = sum(sip.get('total_invested', 0) for sip in equity_sips)
            percentage = (total_equity / total_invested * 100) if total_invested > 0 else 0
            
            if percentage < 50:
                insights.append({
                    'type': 'opportunity',
                    'title': 'Low Equity Exposure',
                    'message': f'Only {percentage:.0f}% of your investments are in equity. For long-term wealth building, aim for 60-80% equity allocation.',
                    'action': 'Rebalance Portfolio'
                })
        
        return insights
    
    def calculate_platform_summary(self, transactions: List[Transaction]) -> List[Dict]:
        """Calculate platform summary from transactions."""
        platform_summary = defaultdict(lambda: {'count': 0, 'total': 0.0})
        for txn in transactions:
            platform = self.extract_platform_name(txn)
            platform_summary[platform]['count'] += 1
            platform_summary[platform]['total'] += txn.amount
        
        return [
            {'name': name, 'transaction_count': data['count'], 'total_invested': data['total']}
            for name, data in platform_summary.items()
        ]
    
    def calculate_platform_summary_from_patterns(self, patterns: List[DetectedEMIPattern]) -> List[Dict]:
        """Calculate platform summary from confirmed patterns."""
        return [
            {
                'name': p.merchant_source,
                'transaction_count': p.occurrence_count,
                'total_invested': p.emi_amount * p.occurrence_count
            }
            for p in patterns
        ]
    
    def analyze_investments(self, user_id: str) -> Dict:
        """
        Analyze user's investment portfolio
        
        Returns complete investment analysis including:
        - Investment summary
        - Detected SIPs
        - Portfolio allocation
        - Insights and recommendations
        
        Args:
            user_id: User ID to analyze
            
        Returns:
            Dictionary with complete investment analysis
        """
        logger.info(f"📊 INVESTMENT SERVICE: Starting investment analysis for user {user_id}")
        
        # Get confirmed investment patterns from Salary Sweep (if exists)
        confirmed_patterns = self.get_confirmed_investment_patterns(user_id)
        has_confirmed_patterns = len(confirmed_patterns) > 0
        
        logger.info(f"📊 Found {len(confirmed_patterns)} confirmed investment patterns")
        
        # Build SIPs from confirmed patterns
        sips_from_patterns = []
        for p in confirmed_patterns:
            sips_from_patterns.append({
                'sip_id': p.pattern_id,
                'platform': p.merchant_source,
                'amount': p.emi_amount,
                'frequency': 'monthly',
                'transaction_count': p.occurrence_count,
                'total_invested': p.emi_amount * p.occurrence_count,
                'start_date': p.first_detected_date,
                'last_transaction_date': p.last_detected_date,
                'category': 'equity'
            })
        
        # Fallback: Get transactions if no confirmed patterns exist
        transactions: List[Transaction] = []
        sips_from_transactions: List[Dict] = []
        
        if not has_confirmed_patterns:
            logger.info("📊 No confirmed patterns found, analyzing transactions directly")
            transactions = self.get_investment_transactions(user_id)
            logger.info(f"📊 Found {len(transactions)} investment transactions")
            
            if transactions:
                # Use service method to detect SIPs from transactions
                sips_from_transactions = self.detect_sips_from_transactions(transactions)
                logger.info(f"📊 Detected {len(sips_from_transactions)} SIP patterns from transactions")
        
        # Use confirmed patterns if available, otherwise use detected SIPs
        sips = sips_from_patterns if has_confirmed_patterns else sips_from_transactions
        
        # Analyze portfolio allocation
        if transactions:
            portfolio = self.analyze_portfolio_allocation(transactions)
        else:
            portfolio = {
                'equity': sum(s.get('total_invested', 0) for s in sips),
                'debt': 0.0,
                'hybrid': 0.0,
                'unknown': 0.0,
                'total': sum(s.get('total_invested', 0) for s in sips)
            }
        
        # Generate insights
        insights = self.generate_insights(transactions, sips)
        
        # Calculate platform summary
        if transactions:
            platforms_list = self.calculate_platform_summary(transactions)
        else:
            platforms_list = self.calculate_platform_summary_from_patterns(confirmed_patterns)
        
        # Calculate summary
        if transactions:
            total_invested = sum(txn.amount for txn in transactions)
            total_transactions = len(transactions)
        else:
            total_invested = sum(p.emi_amount * p.occurrence_count for p in confirmed_patterns)
            total_transactions = sum(p.occurrence_count for p in confirmed_patterns)
        
        summary = {
            'total_invested': total_invested,
            'total_transactions': total_transactions,
            'platforms': platforms_list,
            'sip_count': len(sips),
            'total_sip_investment': sum(s.get('total_invested', 0) for s in sips)
        }
        
        logger.info(f"📊 INVESTMENT SERVICE: Analysis complete")
        logger.info(f"   Total invested: ₹{total_invested:,.2f}")
        logger.info(f"   SIPs detected: {len(sips)}")
        logger.info(f"   Platforms: {len(platforms_list)}")
        
        return {
            'summary': summary,
            'sips': sips,
            'portfolio_allocation': portfolio,
            'insights': insights
        }
    
    def get_sips(self, user_id: str) -> List[Dict]:
        """Get detected SIP patterns for user"""
        logger.info(f"📊 INVESTMENT SERVICE: Getting SIPs for user {user_id}")
        
        # Get confirmed patterns first
        confirmed_patterns = self.get_confirmed_investment_patterns(user_id)
        
        if confirmed_patterns:
            sips = []
            for p in confirmed_patterns:
                sips.append({
                    'sip_id': p.pattern_id,
                    'platform': p.merchant_source,
                    'amount': p.emi_amount,
                    'frequency': 'monthly',
                    'transaction_count': p.occurrence_count,
                    'total_invested': p.emi_amount * p.occurrence_count,
                    'start_date': p.first_detected_date,
                    'last_transaction_date': p.last_detected_date,
                    'category': 'equity'
                })
            return sips
        
        # Fallback to transaction-based detection
        transactions = self.get_investment_transactions(user_id)
        
        # Use InvestmentDetector's detect_sips which returns SIPPattern objects
        sip_objects = InvestmentDetector.detect_sips(transactions)
        
        # Convert to dictionaries for consistency
        return [
            {
                'sip_id': sip.sip_id,
                'platform': sip.platform,
                'amount': sip.amount,
                'frequency': sip.frequency,
                'transaction_count': sip.transaction_count,
                'total_invested': sip.total_invested,
                'start_date': sip.start_date,
                'last_transaction_date': sip.last_transaction_date,
                'category': sip.category or 'equity'
            }
            for sip in sip_objects
        ]
    
    def get_portfolio_allocation(self, user_id: str) -> Dict:
        """Get portfolio allocation breakdown for user"""
        logger.info(f"📊 INVESTMENT SERVICE: Getting portfolio allocation for user {user_id}")
        
        transactions = self.get_investment_transactions(user_id)
        return self.analyze_portfolio_allocation(transactions)

