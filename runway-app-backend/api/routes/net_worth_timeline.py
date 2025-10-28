"""
Net Worth Timeline API Routes

Provides endpoints for tracking net worth over time with monthly snapshots.
Includes dynamic calculation based on EMI payments and investment growth.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import uuid

from storage.models import User, Asset, Liability, NetWorthSnapshot
from storage.database import DatabaseManager
from auth.dependencies import get_current_user, get_db
from api.routes.net_worth_calculator import (
    calculate_dynamic_net_worth_timeline,
    project_future_net_worth,
    get_net_worth_crossover_point
)

router = APIRouter()


def calculate_current_net_worth(session, user_id: str) -> dict:
    """
    Calculate current net worth from assets and liabilities.
    Returns dict with total_assets, total_liabilities, net_worth, and breakdowns.
    """
    # Get all active assets
    assets = session.query(Asset).filter(
        Asset.user_id == user_id,
        Asset.disposed == False
    ).all()

    # Get all liabilities
    liabilities = session.query(Liability).filter(
        Liability.user_id == user_id
    ).all()

    # Calculate totals
    total_assets = sum(
        asset.current_value if asset.current_value else asset.purchase_price
        for asset in assets
    )

    total_liabilities = sum(
        liability.outstanding_balance if liability.outstanding_balance else liability.principal_amount
        for liability in liabilities
    )

    net_worth = total_assets - total_liabilities

    # Calculate liquid assets
    liquid_assets = sum(
        asset.current_value if asset.current_value else asset.purchase_price
        for asset in assets if asset.liquid
    )

    # Asset breakdown by type
    asset_breakdown = {}
    for asset in assets:
        asset_type = asset.asset_type or 'other'
        value = asset.current_value if asset.current_value else asset.purchase_price
        asset_breakdown[asset_type] = asset_breakdown.get(asset_type, 0) + value

    # Liability breakdown by type
    liability_breakdown = {}
    for liability in liabilities:
        liability_type = liability.liability_type or 'other'
        value = liability.outstanding_balance if liability.outstanding_balance else liability.principal_amount
        liability_breakdown[liability_type] = liability_breakdown.get(liability_type, 0) + value

    return {
        'total_assets': total_assets,
        'total_liabilities': total_liabilities,
        'net_worth': net_worth,
        'liquid_assets': liquid_assets,
        'asset_breakdown': asset_breakdown,
        'liability_breakdown': liability_breakdown
    }


@router.get("/timeline")
async def get_net_worth_timeline(
    months: int = Query(default=12, ge=1, le=999, description="Number of months to fetch (999 = all)"),
    current_user: User = Depends(get_current_user),
    db: DatabaseManager = Depends(get_db)
):
    """
    Get net worth timeline for the specified number of months.

    If no snapshots exist, calculates from current assets/liabilities.
    If partial snapshots exist, fills gaps with current data.
    """
    session = db.get_session()
    try:
        # Get existing snapshots
        snapshots = session.query(NetWorthSnapshot).filter(
            NetWorthSnapshot.user_id == current_user.user_id
        ).order_by(NetWorthSnapshot.month).all()

        # If we have snapshots, use them
        if snapshots:
            # Limit to requested number of months
            if months < len(snapshots):
                snapshots = snapshots[-months:]

            timeline = [
                {
                    'month': snapshot.month,
                    'assets': snapshot.total_assets,
                    'liabilities': snapshot.total_liabilities,
                    'net_worth': snapshot.net_worth
                }
                for snapshot in snapshots
            ]
        else:
            # No snapshots exist - create a synthetic timeline based on current data
            # This is a fallback for new users
            current_data = calculate_current_net_worth(session, current_user.user_id)

            # Generate monthly data points (assuming flat growth for now)
            # In a real scenario, you'd want historical transaction data
            timeline = []
            today = datetime.now()

            for i in range(months - 1, -1, -1):
                month_date = today - relativedelta(months=i)
                month_str = month_date.strftime('%Y-%m')

                # For simplicity, show current values
                # In production, you'd interpolate or use transaction history
                timeline.append({
                    'month': month_str,
                    'assets': current_data['total_assets'],
                    'liabilities': current_data['total_liabilities'],
                    'net_worth': current_data['net_worth']
                })

        return {
            'timeline': timeline,
            'has_historical_data': len(snapshots) > 0,
            'months_requested': months,
            'months_returned': len(timeline)
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch timeline: {str(e)}")
    finally:
        session.close()


@router.get("/current")
async def get_current_net_worth(
    current_user: User = Depends(get_current_user),
    db: DatabaseManager = Depends(get_db)
):
    """
    Get current net worth snapshot (real-time calculation).
    """
    session = db.get_session()
    try:
        data = calculate_current_net_worth(session, current_user.user_id)

        return {
            'user_id': current_user.user_id,
            'calculated_at': datetime.now().isoformat(),
            **data
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to calculate net worth: {str(e)}")
    finally:
        session.close()


@router.post("/snapshot")
async def create_net_worth_snapshot(
    current_user: User = Depends(get_current_user),
    db: DatabaseManager = Depends(get_db)
):
    """
    Create a manual net worth snapshot for the current month.

    This captures the current state of assets and liabilities.
    Typically called automatically on a schedule (e.g., first of each month).
    """
    session = db.get_session()
    try:
        # Calculate current net worth
        data = calculate_current_net_worth(session, current_user.user_id)

        # Get current month
        today = datetime.now()
        month_str = today.strftime('%Y-%m')
        date_str = today.strftime('%Y-%m-%d')

        # Check if snapshot already exists for this month
        existing = session.query(NetWorthSnapshot).filter(
            NetWorthSnapshot.user_id == current_user.user_id,
            NetWorthSnapshot.month == month_str
        ).first()

        if existing:
            # Update existing snapshot
            existing.snapshot_date = date_str
            existing.total_assets = data['total_assets']
            existing.total_liabilities = data['total_liabilities']
            existing.net_worth = data['net_worth']
            existing.liquid_assets = data['liquid_assets']
            existing.asset_breakdown = data['asset_breakdown']
            existing.liability_breakdown = data['liability_breakdown']
            existing.created_at = datetime.now()

            session.commit()

            return {
                'message': 'Snapshot updated',
                'snapshot_id': existing.snapshot_id,
                'month': month_str,
                **data
            }
        else:
            # Create new snapshot
            snapshot = NetWorthSnapshot(
                snapshot_id=str(uuid.uuid4()),
                user_id=current_user.user_id,
                snapshot_date=date_str,
                month=month_str,
                total_assets=data['total_assets'],
                total_liabilities=data['total_liabilities'],
                net_worth=data['net_worth'],
                liquid_assets=data['liquid_assets'],
                asset_breakdown=data['asset_breakdown'],
                liability_breakdown=data['liability_breakdown']
            )

            session.add(snapshot)
            session.commit()

            return {
                'message': 'Snapshot created',
                'snapshot_id': snapshot.snapshot_id,
                'month': month_str,
                **data
            }

    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to create snapshot: {str(e)}")
    finally:
        session.close()


@router.delete("/snapshots/{month}")
async def delete_snapshot(
    month: str,
    current_user: User = Depends(get_current_user),
    db: DatabaseManager = Depends(get_db)
):
    """
    Delete a specific snapshot by month (YYYY-MM format).
    """
    session = db.get_session()
    try:
        snapshot = session.query(NetWorthSnapshot).filter(
            NetWorthSnapshot.user_id == current_user.user_id,
            NetWorthSnapshot.month == month
        ).first()

        if not snapshot:
            raise HTTPException(status_code=404, detail=f"Snapshot not found for month {month}")

        session.delete(snapshot)
        session.commit()

        return {'message': f'Snapshot for {month} deleted successfully'}

    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to delete snapshot: {str(e)}")
    finally:
        session.close()


@router.get("/snapshots")
async def list_all_snapshots(
    current_user: User = Depends(get_current_user),
    db: DatabaseManager = Depends(get_db)
):
    """
    List all snapshots for the current user (for debugging/admin).
    """
    session = db.get_session()
    try:
        snapshots = session.query(NetWorthSnapshot).filter(
            NetWorthSnapshot.user_id == current_user.user_id
        ).order_by(NetWorthSnapshot.month.desc()).all()

        return {
            'snapshots': [snapshot.to_dict() for snapshot in snapshots],
            'total_count': len(snapshots)
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list snapshots: {str(e)}")
    finally:
        session.close()


@router.get("/timeline/dynamic")
async def get_dynamic_net_worth_timeline(
    months: int = Query(default=12, ge=1, le=999, description="Number of months (past or future)"),
    projection: bool = Query(default=False, description="If true, projects future net worth"),
    current_user: User = Depends(get_current_user),
    db: DatabaseManager = Depends(get_db)
):
    """
    Get DYNAMIC net worth timeline that accounts for:
    - EMI payments reducing liabilities over time
    - SIP/investment growth
    - Asset appreciation
    - New liabilities being added

    This provides a REALISTIC view of net worth evolution.

    Args:
        months: Number of months to calculate
        projection: If True, projects into future; if False, shows historical
    """
    session = db.get_session()
    try:
        if projection:
            # Project future net worth
            result = project_future_net_worth(
                session=session,
                user_id=current_user.user_id,
                months_ahead=months
            )

            return {
                'timeline': result['timeline'],
                'crossover_point': result['crossover_point'],
                'projection_months': result['projection_months'],
                'final_net_worth': result['final_net_worth'],
                'net_worth_growth': result['net_worth_growth'],
                'is_projection': True
            }
        else:
            # Historical/current timeline
            end_date = datetime.now()
            start_date = end_date - relativedelta(months=months)

            timeline = calculate_dynamic_net_worth_timeline(
                session=session,
                user_id=current_user.user_id,
                start_month=start_date.strftime('%Y-%m'),
                end_month=end_date.strftime('%Y-%m'),
                projection=False
            )

            crossover = get_net_worth_crossover_point(timeline)

            return {
                'timeline': timeline,
                'crossover_point': crossover,
                'months_requested': months,
                'months_returned': len(timeline),
                'is_projection': False
            }

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to calculate dynamic timeline: {str(e)}")
    finally:
        session.close()


@router.get("/projection")
async def get_net_worth_projection(
    years: int = Query(default=5, ge=1, le=30, description="Years to project ahead"),
    current_user: User = Depends(get_current_user),
    db: DatabaseManager = Depends(get_db)
):
    """
    Project net worth into the future based on current EMIs and investments.

    Shows when:
    - Net worth becomes positive
    - Loans will be paid off
    - Investment targets will be reached
    """
    session = db.get_session()
    try:
        months_ahead = years * 12

        result = project_future_net_worth(
            session=session,
            user_id=current_user.user_id,
            months_ahead=months_ahead
        )

        # Find when each loan gets paid off
        liabilities = session.query(Liability).filter(
            Liability.user_id == current_user.user_id
        ).all()

        loan_payoff_schedule = []
        for liability in liabilities:
            if liability.remaining_tenure_months:
                payoff_date = datetime.now() + relativedelta(months=liability.remaining_tenure_months)
                loan_payoff_schedule.append({
                    'name': liability.name,
                    'payoff_month': payoff_date.strftime('%Y-%m'),
                    'months_remaining': liability.remaining_tenure_months,
                    'current_balance': liability.outstanding_balance
                })

        return {
            'timeline': result['timeline'],
            'crossover_point': result['crossover_point'],
            'years_projected': years,
            'final_net_worth': result['final_net_worth'],
            'total_growth': result['net_worth_growth'],
            'loan_payoff_schedule': loan_payoff_schedule,
            'insights': {
                'will_be_positive': result['crossover_point'] is not None,
                'months_to_positive': None  # Calculate from crossover_point if needed
            }
        }

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to calculate projection: {str(e)}")
    finally:
        session.close()
