"""
Net Worth Calculator - Dynamic Timeline with EMI Tracking

This module provides realistic net worth calculations that account for:
1. EMI payments reducing liabilities over time
2. Liquid investments growing (SIPs, RDs, etc.)
3. Asset appreciation
4. New liabilities being added
5. Projection into future months
"""

from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from typing import List, Dict, Optional
from sqlalchemy.orm import Session

from storage.models import Asset, Liability, Transaction, DetectedEMIPattern


def calculate_emi_amortization(principal: float, interest_rate: float, tenure_months: int) -> List[Dict]:
    """
    Calculate month-by-month EMI amortization schedule.

    Returns list of dicts with: month, emi, principal_paid, interest_paid, balance
    """
    if tenure_months <= 0 or interest_rate <= 0:
        return []

    monthly_rate = interest_rate / 12 / 100

    # EMI formula: P * r * (1+r)^n / ((1+r)^n - 1)
    emi = principal * monthly_rate * ((1 + monthly_rate) ** tenure_months) / (((1 + monthly_rate) ** tenure_months) - 1)

    schedule = []
    balance = principal

    for month in range(1, tenure_months + 1):
        interest_paid = balance * monthly_rate
        principal_paid = emi - interest_paid
        balance -= principal_paid

        schedule.append({
            'month': month,
            'emi': round(emi, 2),
            'principal_paid': round(principal_paid, 2),
            'interest_paid': round(interest_paid, 2),
            'balance': round(max(0, balance), 2)  # Ensure balance doesn't go negative
        })

    return schedule


def get_liability_balance_at_month(liability: Liability, months_from_now: int) -> float:
    """
    Calculate liability balance after X months from NOW using original loan terms.

    Args:
        liability: Liability object with complete loan details
        months_from_now: Number of months into the future from the timeline start

    Returns:
        Outstanding balance after months_from_now months of additional EMI payments
    """
    # If no loan details, return static balance
    if not liability.principal_amount or not liability.emi_amount:
        return liability.outstanding_balance if liability.outstanding_balance else 0
    
    # Handle case where we have EMI but missing interest rate
    # Use simple linear reduction based on EMI amount
    if not liability.interest_rate:
        # Estimate tenure from EMI amount (how many months to pay off)
        if liability.emi_amount > 0:
            estimated_months = liability.outstanding_balance / liability.emi_amount
            reduction_per_month = liability.outstanding_balance / estimated_months
            new_balance = liability.outstanding_balance - (reduction_per_month * months_from_now)
            return max(0, new_balance)
        return liability.outstanding_balance

    # If we don't have original tenure, fall back to simple calculation
    if not liability.original_tenure_months:
        if liability.remaining_tenure_months and liability.remaining_tenure_months > 0:
            reduction_per_month = liability.outstanding_balance / liability.remaining_tenure_months
            new_balance = liability.outstanding_balance - (reduction_per_month * months_from_now)
            return max(0, new_balance)
        return liability.outstanding_balance

    # If already asking for months beyond the remaining tenure, loan is paid off
    if liability.remaining_tenure_months and months_from_now >= liability.remaining_tenure_months:
        return 0

    # Handle moratorium: skip principal reductions for moratorium period from NOW
    moratorium_months = liability.moratorium_months or 0

    # Calculate FULL amortization schedule from ORIGINAL loan terms
    # This gives us the accurate principal/interest split
    full_schedule = calculate_emi_amortization(
        principal=liability.principal_amount,
        interest_rate=liability.interest_rate,
        tenure_months=liability.original_tenure_months
    )

    # Calculate how many months have elapsed from loan start to NOW
    months_elapsed_to_today = liability.original_tenure_months - (liability.remaining_tenure_months or 0)

    # Calculate total months from loan start to the requested future date
    effective_months_from_now = max(0, months_from_now - moratorium_months)
    total_months_from_start = months_elapsed_to_today + effective_months_from_now

    # Return balance at that point in the schedule
    if total_months_from_start >= len(full_schedule):
        return 0  # Loan fully paid off
    elif total_months_from_start == 0:
        return liability.principal_amount
    else:
        return full_schedule[total_months_from_start - 1]['balance']


def get_sip_value_at_month(sip_amount: float, months_elapsed: int, annual_return: float = 12.0) -> float:
    """
    Calculate SIP investment value after X months.

    Args:
        sip_amount: Monthly SIP amount
        months_elapsed: Number of months invested
        annual_return: Expected annual return percentage (default 12%)

    Returns:
        Total value of SIP investment
    """
    if months_elapsed <= 0:
        return 0

    monthly_rate = annual_return / 12 / 100

    # Future value of SIP: P * [((1 + r)^n - 1) / r] * (1 + r)
    if monthly_rate > 0:
        fv = sip_amount * (((1 + monthly_rate) ** months_elapsed - 1) / monthly_rate) * (1 + monthly_rate)
    else:
        fv = sip_amount * months_elapsed

    return round(fv, 2)


def calculate_dynamic_net_worth_timeline(
    session: Session,
    user_id: str,
    start_month: str,  # YYYY-MM format
    end_month: str,    # YYYY-MM format
    projection: bool = False  # If True, projects into future
) -> List[Dict]:
    """
    Calculate realistic net worth timeline considering:
    - EMI payments reducing liabilities
    - SIP/recurring investments growing
    - Asset appreciation
    - New liabilities added dynamically

    Args:
        session: Database session
        user_id: User ID
        start_month: Starting month (YYYY-MM)
        end_month: Ending month (YYYY-MM)
        projection: If True, projects future based on current trends

    Returns:
        List of monthly net worth data points
    """

    # Parse start and end dates
    start_date = datetime.strptime(start_month, '%Y-%m')
    end_date = datetime.strptime(end_month, '%Y-%m')

    # Get all assets (snapshot at start_date)
    assets = session.query(Asset).filter(
        Asset.user_id == user_id,
        Asset.disposed == False
    ).all()

    # Get all liabilities with start dates
    liabilities = session.query(Liability).filter(
        Liability.user_id == user_id
    ).all()

    # Get detected SIP/investment patterns
    sip_patterns = session.query(DetectedEMIPattern).filter(
        DetectedEMIPattern.user_id == user_id,
        DetectedEMIPattern.category.in_(['Investment', 'Government Scheme'])
    ).all()

    # Build timeline month by month
    timeline = []
    current_date = start_date

    while current_date <= end_date:
        month_str = current_date.strftime('%Y-%m')

        # Calculate assets (with optional appreciation)
        total_assets = 0
        liquid_assets = 0

        for asset in assets:
            # Base asset value
            asset_value = asset.current_value if asset.current_value else asset.purchase_price

            # Add appreciation for property/stocks (optional - can be refined)
            if asset.asset_type in ['property', 'stocks']:
                months_since_purchase = 0
                if asset.purchase_date:
                    if isinstance(asset.purchase_date, str):
                        purchase_dt = datetime.strptime(asset.purchase_date, '%Y-%m-%d')
                    else:
                        purchase_dt = asset.purchase_date
                    months_since_purchase = (current_date.year - purchase_dt.year) * 12 + (current_date.month - purchase_dt.month)

                # Assume 6% annual appreciation for property, 12% for stocks
                annual_rate = 0.06 if asset.asset_type == 'property' else 0.12
                monthly_rate = annual_rate / 12
                asset_value = asset_value * ((1 + monthly_rate) ** months_since_purchase)

            total_assets += asset_value
            if asset.liquid:
                liquid_assets += asset_value

        # Calculate SIP accumulation
        for sip in sip_patterns:
            if sip.is_confirmed:
                # Calculate months since SIP started (from first detected transaction)
                # For simplicity, assume started 12 months before current calculation
                months_invested = min((current_date.year - start_date.year) * 12 + (current_date.month - start_date.month), 60)  # Max 5 years
                sip_value = get_sip_value_at_month(sip.emi_amount, months_invested, annual_return=12.0)
                total_assets += sip_value
                liquid_assets += sip_value  # SIPs are liquid
        
        # Add monthly savings accumulation for projection (Real Finance Model)
        # How real finance systems work:
        # 1. Income - Expenses = Savings (from transaction data)
        # 2. Savings are invested in assets (FD, MF, Stocks, etc.)
        # 3. Investments grow with returns (4-12% annually depending on type)
        if projection:
            # Calculate months elapsed from start
            months_elapsed = (current_date.year - start_date.year) * 12 + (current_date.month - start_date.month)
            
            if months_elapsed > 0:
                # Get transaction data to calculate actual savings rate
                from storage.database import DatabaseManager
                from storage.models import Transaction
                
                # Calculate average monthly income and expenses from recent transactions
                recent_transactions = session.query(Transaction).filter(
                    Transaction.user_id == user_id
                ).order_by(Transaction.date.desc()).limit(100).all()
                
                if recent_transactions:
                    # Group transactions by month to calculate proper monthly averages
                    monthly_data = {}
                    for txn in recent_transactions:
                        if txn.date:
                            month_key = txn.date[:7]  # YYYY-MM format
                            if month_key not in monthly_data:
                                monthly_data[month_key] = {'income': 0, 'expenses': 0}
                            
                            if txn.type == 'credit':
                                monthly_data[month_key]['income'] += txn.amount
                            elif txn.type == 'debit':
                                monthly_data[month_key]['expenses'] += txn.amount
                    
                    # Calculate average monthly income and expenses
                    if monthly_data:
                        avg_monthly_income = sum(m['income'] for m in monthly_data.values()) / len(monthly_data)
                        avg_monthly_expenses = sum(m['expenses'] for m in monthly_data.values()) / len(monthly_data)
                        
                        # Calculate net monthly savings (this is what goes into assets)
                        monthly_savings = max(0, avg_monthly_income - avg_monthly_expenses)
                        
                        # Apply investment returns to accumulated savings
                        # Conservative: assume savings are invested with 8% annual return
                        annual_return_rate = 0.08
                        monthly_return_rate = annual_return_rate / 12
                        
                        # Calculate accumulated savings with compounding
                        accumulated_savings = 0
                        for month in range(1, months_elapsed + 1):
                            # This month's savings contribution
                            monthly_contribution = monthly_savings
                            # Previous accumulated savings grow with returns
                            accumulated_savings = accumulated_savings * (1 + monthly_return_rate) + monthly_contribution
                        
                        total_assets += accumulated_savings
                        liquid_assets += accumulated_savings

        # Calculate liabilities (with EMI reduction)
        total_liabilities = 0

        # Calculate months from the start of the timeline (not from liability start_date)
        months_from_timeline_start = (current_date.year - start_date.year) * 12 + (current_date.month - start_date.month)

        for liability in liabilities:
            # Check if liability exists at this point in time
            if liability.start_date:
                if isinstance(liability.start_date, str):
                    liability_start = datetime.strptime(liability.start_date, '%Y-%m-%d')
                else:
                    liability_start = liability.start_date

                # Only include if the liability has started by current_date
                if current_date < liability_start:
                    continue  # Skip this liability for this month

            # Calculate balance after X months from NOW (timeline start = "now")
            current_balance = get_liability_balance_at_month(liability, months_from_timeline_start)
            total_liabilities += current_balance

        # Calculate net worth
        net_worth = total_assets - total_liabilities

        timeline.append({
            'month': month_str,
            'assets': round(total_assets, 2),
            'liabilities': round(total_liabilities, 2),
            'net_worth': round(net_worth, 2),
            'liquid_assets': round(liquid_assets, 2)
        })

        # Move to next month
        current_date = current_date + relativedelta(months=1)

    return timeline


def get_net_worth_crossover_point(timeline: List[Dict]) -> Optional[str]:
    """
    Find the month when net worth goes from negative to positive.

    Args:
        timeline: List of timeline data points

    Returns:
        Month string (YYYY-MM) when net worth becomes positive, or None
    """
    for i, data in enumerate(timeline):
        if i > 0 and timeline[i-1]['net_worth'] < 0 and data['net_worth'] >= 0:
            return data['month']

    # Check if already positive at start
    if timeline and timeline[0]['net_worth'] >= 0:
        return timeline[0]['month']

    return None


def project_future_net_worth(
    session: Session,
    user_id: str,
    months_ahead: int = 60  # Project 5 years ahead by default
) -> Dict:
    """
    Project net worth into the future based on current liabilities and investments.

    Returns:
        Dict with timeline, crossover_point, fire_date estimates
    """
    current_month = datetime.now().strftime('%Y-%m')
    future_month = (datetime.now() + relativedelta(months=months_ahead)).strftime('%Y-%m')

    timeline = calculate_dynamic_net_worth_timeline(
        session=session,
        user_id=user_id,
        start_month=current_month,
        end_month=future_month,
        projection=True
    )

    crossover_point = get_net_worth_crossover_point(timeline)

    return {
        'timeline': timeline,
        'crossover_point': crossover_point,
        'projection_months': months_ahead,
        'final_net_worth': timeline[-1]['net_worth'] if timeline else 0,
        'net_worth_growth': timeline[-1]['net_worth'] - timeline[0]['net_worth'] if len(timeline) > 1 else 0
    }
