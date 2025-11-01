"""
Analytics API Routes

Summary statistics and insights
"""

from fastapi import APIRouter, HTTPException, Query, Depends, status
from typing import Optional
import sys
from pathlib import Path
import logging
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from api.models.schemas import (
    SummaryStats,
    CategoryBreakdown,
    TopMerchant,
    AnalyticsResponse
)
from storage.database import DatabaseManager
from storage.models import User, TransactionType, TransactionCategory
from auth.dependencies import get_current_user
from config import Config

logger = logging.getLogger(__name__)

router = APIRouter()


def get_db():
    """Get database instance"""
    return DatabaseManager(Config.DATABASE_URL)


@router.get("/summary", response_model=SummaryStats)
async def get_summary(
    start_date: Optional[str] = Query(None, description="Start date filter (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date filter (YYYY-MM-DD)"),
    current_user: User = Depends(get_current_user)
):
    """
    Get summary statistics

    Returns:
    - Total transactions count
    - Total debit amount
    - Total credit amount
    - Net amount (credit - debit)
    - Category breakdown
    - Date range
    """
    try:
        db = get_db()
        stats = db.get_summary_stats(user_id=current_user.user_id)
        db.close()

        return SummaryStats(**stats)

    except Exception as e:
        logger.error(f"Error fetching summary: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch summary: {str(e)}"
        )


@router.get("/category-breakdown", response_model=list[CategoryBreakdown])
async def get_category_breakdown(
    start_date: Optional[str] = Query(None, description="Start date filter"),
    end_date: Optional[str] = Query(None, description="End date filter"),
    current_user: User = Depends(get_current_user)
):
    """
    Get spending breakdown by category

    Returns percentage and total amount for each category
    """
    try:
        db = get_db()

        transactions = db.get_transactions(
            user_id=current_user.user_id,
            start_date=start_date,
            end_date=end_date
        )

        # Calculate category breakdown with debit/credit netting
        # Group by category and merchant to handle cases where a merchant has both debit and credit
        category_merchant_totals = defaultdict(lambda: {'debit': 0.0, 'credit': 0.0})
        category_counts = defaultdict(int)
        
        for txn in transactions:
            # Include all transactions (EMI-converted transactions are now included)
            # Note: EMI-converted transactions are typically large purchases that were
            # converted to EMI, so including them gives a complete picture of spending
            extra_metadata = txn.extra_metadata or {}
            # if extra_metadata.get('emi_converted'):
            #     continue  # COMMENTED OUT: Now including EMI-converted transactions
            
            category = txn.category or "Unknown"
            merchant = txn.merchant_canonical or "Unknown"
            key = (category, merchant)
            
            # Handle ENUM comparison (works for both ENUM and string for backward compatibility)
            txn_type_value = txn.type.value if hasattr(txn.type, 'value') else txn.type
            if txn_type_value == TransactionType.DEBIT.value:
                category_merchant_totals[key]['debit'] += txn.amount
                category_counts[category] += 1
            elif txn_type_value == TransactionType.CREDIT.value:
                category_merchant_totals[key]['credit'] += txn.amount

        # Calculate net totals per category (debit - credit)
        category_totals = defaultdict(lambda: {'count': 0, 'total': 0.0})
        total_amount = 0.0
        
        for (category, merchant), amounts in category_merchant_totals.items():
            net_amount = amounts['debit'] - amounts['credit']
            if net_amount > 0:  # Only show if net spending is positive
                category_totals[category]['total'] += net_amount
                category_totals[category]['count'] = category_counts[category]
                total_amount += net_amount

        # Convert to response format
        breakdown = []
        for category, data in category_totals.items():
            percentage = (data['total'] / total_amount * 100) if total_amount > 0 else 0
            breakdown.append(CategoryBreakdown(
                category=category,
                count=data['count'],
                total_amount=round(data['total'], 2),
                percentage=round(percentage, 2)
            ))

        # Sort by total amount descending
        breakdown.sort(key=lambda x: x.total_amount, reverse=True)

        db.close()
        return breakdown

    except Exception as e:
        logger.error(f"Error fetching category breakdown: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch category breakdown: {str(e)}"
        )


@router.get("/top-merchants", response_model=list[TopMerchant])
async def get_top_merchants(
    limit: int = Query(10, ge=1, le=50, description="Number of top merchants to return"),
    start_date: Optional[str] = Query(None, description="Start date filter"),
    end_date: Optional[str] = Query(None, description="End date filter"),
    current_user: User = Depends(get_current_user)
):
    """
    Get top merchants by spending

    Returns merchants sorted by total spend amount
    """
    try:
        db = get_db()

        transactions = db.get_transactions(
            user_id=current_user.user_id,
            start_date=start_date,
            end_date=end_date
        )

        # Calculate merchant totals with debit/credit netting
        merchant_totals = defaultdict(lambda: {'debit': 0.0, 'credit': 0.0, 'count': 0})

        for txn in transactions:
            # Handle ENUM comparison (works for both ENUM and string for backward compatibility)
            txn_type_value = txn.type.value if hasattr(txn.type, 'value') else txn.type
            if txn.merchant_canonical:
                merchant = txn.merchant_canonical
                if txn_type_value == TransactionType.DEBIT.value:
                    merchant_totals[merchant]['debit'] += txn.amount
                    merchant_totals[merchant]['count'] += 1
                elif txn_type_value == TransactionType.CREDIT.value:
                    merchant_totals[merchant]['credit'] += txn.amount

        # Convert to response format with net spending (debit - credit)
        top_merchants = []
        for merchant, data in merchant_totals.items():
            net_amount = data['debit'] - data['credit']
            if net_amount > 0:  # Only include merchants with positive net spending
                top_merchants.append(
                    TopMerchant(
                        merchant=merchant,
                        total_spend=round(net_amount, 2),
                        transaction_count=data['count']
                    )
                )

        # Sort by total spend and limit
        top_merchants.sort(key=lambda x: x.total_spend, reverse=True)
        top_merchants = top_merchants[:limit]

        db.close()
        return top_merchants

    except Exception as e:
        logger.error(f"Error fetching top merchants: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch top merchants: {str(e)}"
        )


@router.get("/trends", response_model=list[dict])
async def get_monthly_trends(
    months: int = Query(6, ge=1, le=24, description="Number of months to include in trends"),
    start_date: Optional[str] = Query(None, description="Start date filter"),
    end_date: Optional[str] = Query(None, description="End date filter"),
    current_user: User = Depends(get_current_user)
):
    """
    Get monthly trends for income, expenses, and savings

    Returns month-by-month breakdown with:
    - Total income and expenses
    - Net savings
    - Savings rate
    - Month-over-month growth percentages
    """
    try:
        db = get_db()

        transactions = db.get_transactions(
            user_id=current_user.user_id,
            start_date=start_date,
            end_date=end_date
        )

        # Group by month
        monthly_data = defaultdict(lambda: {'income': 0.0, 'expenses': 0.0, 'transactions': 0})

        for txn in transactions:
            # Extract month from date (YYYY-MM format)
            month = txn.date[:7] if txn.date and len(txn.date) >= 7 else None
            if not month:
                continue

            monthly_data[month]['transactions'] += 1

            # Handle ENUM comparison (works for both ENUM and string for backward compatibility)
            txn_type_value = txn.type.value if hasattr(txn.type, 'value') else txn.type
            if txn_type_value == TransactionType.CREDIT.value:
                monthly_data[month]['income'] += txn.amount
            else:  # debit
                monthly_data[month]['expenses'] += txn.amount

        # Convert to sorted list of trends
        trends = []
        sorted_months = sorted(monthly_data.keys(), reverse=True)[:months]
        sorted_months.reverse()  # Oldest to newest

        prev_month_data = None

        for month in sorted_months:
            data = monthly_data[month]
            net_savings = data['income'] - data['expenses']
            savings_rate = (net_savings / data['income'] * 100) if data['income'] > 0 else 0

            # Calculate growth percentages
            income_growth = None
            expense_growth = None
            savings_growth = None

            if prev_month_data:
                if prev_month_data['income'] > 0:
                    income_growth = ((data['income'] - prev_month_data['income']) / prev_month_data['income']) * 100
                if prev_month_data['expenses'] > 0:
                    expense_growth = ((data['expenses'] - prev_month_data['expenses']) / prev_month_data['expenses']) * 100
                prev_savings = prev_month_data['income'] - prev_month_data['expenses']
                if prev_savings != 0:
                    savings_growth = ((net_savings - prev_savings) / abs(prev_savings)) * 100

            trend = {
                'month': month,
                'income': round(data['income'], 2),
                'expenses': round(data['expenses'], 2),
                'net_savings': round(net_savings, 2),
                'savings_rate': round(savings_rate, 2),
                'transaction_count': data['transactions'],
                'income_growth': round(income_growth, 2) if income_growth is not None else None,
                'expense_growth': round(expense_growth, 2) if expense_growth is not None else None,
                'savings_growth': round(savings_growth, 2) if savings_growth is not None else None
            }

            trends.append(trend)
            prev_month_data = data

        db.close()
        return trends

    except Exception as e:
        logger.error(f"Error fetching monthly trends: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch monthly trends: {str(e)}"
        )


@router.get("/comprehensive", response_model=AnalyticsResponse)
async def get_comprehensive_analytics(
    start_date: Optional[str] = Query(None, description="Start date filter"),
    end_date: Optional[str] = Query(None, description="End date filter")
):
    """
    Get comprehensive analytics

    Returns all analytics in a single response:
    - Summary statistics
    - Category breakdown
    - Top merchants
    """
    try:
        db = get_db()

        # Get summary
        stats = db.get_summary_stats()
        summary = SummaryStats(**stats)

        # Get transactions for detailed analytics
        transactions = db.get_transactions(
            start_date=start_date,
            end_date=end_date
        )

        # Category breakdown with debit/credit netting
        category_merchant_totals = defaultdict(lambda: {'debit': 0.0, 'credit': 0.0})
        category_counts = defaultdict(int)
        
        for txn in transactions:
            # Include all transactions (EMI-converted transactions are now included)
            # extra_metadata = txn.extra_metadata or {}
            # if extra_metadata.get('emi_converted'):
            #     continue  # COMMENTED OUT: Now including EMI-converted transactions
            
            category = txn.category or "Unknown"
            merchant = txn.merchant_canonical or "Unknown"
            key = (category, merchant)
            
            # Handle ENUM comparison (works for both ENUM and string for backward compatibility)
            txn_type_value = txn.type.value if hasattr(txn.type, 'value') else txn.type
            if txn_type_value == TransactionType.DEBIT.value:
                category_merchant_totals[key]['debit'] += txn.amount
                category_counts[category] += 1
            elif txn_type_value == TransactionType.CREDIT.value:
                category_merchant_totals[key]['credit'] += txn.amount
        
        # Calculate net totals per category (debit - credit)
        category_totals = defaultdict(lambda: {'count': 0, 'total': 0.0})
        merchant_totals = defaultdict(lambda: {'debit': 0.0, 'credit': 0.0, 'count': 0})
        total_debit = 0.0
        total_credit = 0.0
        
        for (category, merchant), amounts in category_merchant_totals.items():
            net_amount = amounts['debit'] - amounts['credit']
            
            # Track for merchant totals
            if merchant != "Unknown":
                merchant_totals[merchant]['debit'] += amounts['debit']
                merchant_totals[merchant]['credit'] += amounts['credit']
                if amounts['debit'] > 0:
                    merchant_totals[merchant]['count'] += 1
            
            total_debit += amounts['debit']
            total_credit += amounts['credit']
            
            # Category totals (only positive net)
            if net_amount > 0:
                category_totals[category]['total'] += net_amount
                category_totals[category]['count'] = category_counts[category]

        # Build category breakdown
        category_breakdown = []
        for category, data in category_totals.items():
            total_net = sum(ct['total'] for ct in category_totals.values())
            percentage = (data['total'] / total_net * 100) if total_net > 0 else 0
            category_breakdown.append(CategoryBreakdown(
                category=category,
                count=data['count'],
                total_amount=round(data['total'], 2),
                percentage=round(percentage, 2)
            ))
        category_breakdown.sort(key=lambda x: x.total_amount, reverse=True)

        # Build top merchants with net spending (debit - credit)
        top_merchants = []
        for merchant, data in merchant_totals.items():
            net_amount = data['debit'] - data['credit']
            if net_amount > 0:  # Only include merchants with positive net spending
                top_merchants.append(
                    TopMerchant(
                        merchant=merchant,
                        total_spend=round(net_amount, 2),
                        transaction_count=data['count']
                    )
                )
        top_merchants.sort(key=lambda x: x.total_spend, reverse=True)
        top_merchants = top_merchants[:10]

        db.close()

        return AnalyticsResponse(
            summary=summary,
            category_breakdown=category_breakdown,
            top_merchants=top_merchants
        )

    except Exception as e:
        logger.error(f"Error fetching comprehensive analytics: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch analytics: {str(e)}"
        )
