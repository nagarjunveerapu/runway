"""
Liability API Routes

CRUD operations for liabilities (loans, EMIs, debts)
"""

from fastapi import APIRouter, HTTPException, Depends, status
from typing import List, Optional
import logging
import sys
import uuid
from pathlib import Path
from datetime import datetime
from dateutil.relativedelta import relativedelta

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from storage.models import Liability, User
from storage.database import DatabaseManager
from auth.dependencies import get_current_user, get_db
from config import Config
from utils.date_parser import parse_date
from api.routes.net_worth_calculator import calculate_emi_amortization

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/", response_model=List[dict])
async def get_liabilities(
    current_user: User = Depends(get_current_user),
    db: DatabaseManager = Depends(get_db)
):
    """Get all liabilities for the current user"""
    session = db.get_session()
    
    try:
        liabilities = session.query(Liability).filter(
            Liability.user_id == current_user.user_id
        ).all()
        
        return [liability.to_dict() for liability in liabilities]
    finally:
        session.close()


@router.get("/{liability_id}", response_model=dict)
async def get_liability(
    liability_id: str,
    current_user: User = Depends(get_current_user),
    db: DatabaseManager = Depends(get_db)
):
    """Get a single liability by ID"""
    session = db.get_session()
    
    try:
        liability = session.query(Liability).filter(
            Liability.liability_id == liability_id,
            Liability.user_id == current_user.user_id
        ).first()
        
        if not liability:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Liability not found"
            )
        
        return liability.to_dict()
    finally:
        session.close()


@router.post("/", response_model=dict, status_code=status.HTTP_201_CREATED)
async def create_liability(
    liability_data: dict,
    current_user: User = Depends(get_current_user),
    db: DatabaseManager = Depends(get_db)
):
    """Create a new liability"""
    session = db.get_session()
    
    try:
        # Parse start_date if provided
        start_date = liability_data.get('start_date')
        start_date_obj = None
        if start_date:
            parsed_date_str = parse_date(start_date)
            if parsed_date_str:
                start_date_obj = datetime.strptime(parsed_date_str, '%Y-%m-%d')
            else:
                start_date_obj = None

        # Calculate end_date if we have start_date and original_tenure_months
        end_date_obj = None
        original_tenure = liability_data.get('original_tenure_months')
        if start_date_obj and original_tenure:
            end_date_obj = start_date_obj + relativedelta(months=int(original_tenure))

        liability = Liability(
            liability_id=str(uuid.uuid4()),
            user_id=current_user.user_id,
            name=liability_data.get('name'),
            liability_type=liability_data.get('liability_type', 'loan'),
            principal_amount=liability_data.get('principal_amount'),
            outstanding_balance=liability_data.get('outstanding_balance'),
            interest_rate=liability_data.get('interest_rate'),
            emi_amount=liability_data.get('emi_amount'),
            rate_type=liability_data.get('rate_type'),
            rate_reset_frequency_months=liability_data.get('rate_reset_frequency_months'),
            processing_fee=liability_data.get('processing_fee'),
            prepayment_penalty_pct=liability_data.get('prepayment_penalty_pct'),
            original_tenure_months=liability_data.get('original_tenure_months'),
            remaining_tenure_months=liability_data.get('remaining_tenure_months'),
            recurring_pattern_id=liability_data.get('recurring_pattern_id'),
            start_date=start_date_obj,
            end_date=end_date_obj,
            last_rate_reset_date=liability_data.get('last_rate_reset_date'),
            moratorium_months=liability_data.get('moratorium_months'),
            lender_name=liability_data.get('lender_name'),
            status=liability_data.get('status', 'active'),
            closure_date=liability_data.get('closure_date'),
            closure_reason=liability_data.get('closure_reason')
        )
        
        session.add(liability)
        session.commit()
        session.refresh(liability)
        
        return liability.to_dict()
    except Exception as e:
        session.rollback()
        logger.error(f"Error creating liability: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create liability: {str(e)}"
        )
    finally:
        session.close()


@router.patch("/{liability_id}", response_model=dict)
async def update_liability(
    liability_id: str,
    liability_data: dict,
    current_user: User = Depends(get_current_user),
    db: DatabaseManager = Depends(get_db)
):
    """Update an existing liability"""
    session = db.get_session()
    
    try:
        liability = session.query(Liability).filter(
            Liability.liability_id == liability_id,
            Liability.user_id == current_user.user_id
        ).first()
        
        if not liability:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Liability not found"
            )
        
        # Update fields
        for key, value in liability_data.items():
            if key == 'start_date' and value:
                parsed_date_str = parse_date(value)
                if parsed_date_str:
                    value = datetime.strptime(parsed_date_str, '%Y-%m-%d').date()
            if hasattr(liability, key):
                setattr(liability, key, value)
        
        session.commit()
        session.refresh(liability)
        
        return liability.to_dict()
    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        logger.error(f"Error updating liability: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update liability: {str(e)}"
        )
    finally:
        session.close()


@router.get("/{liability_id}/amortization", response_model=dict)
async def get_amortization_schedule(
    liability_id: str,
    current_user: User = Depends(get_current_user),
    db: DatabaseManager = Depends(get_db)
):
    """Return amortization schedule for a liability using current terms."""
    session = db.get_session()
    try:
        liability = session.query(Liability).filter(
            Liability.liability_id == liability_id,
            Liability.user_id == current_user.user_id
        ).first()

        if not liability:
            raise HTTPException(status_code=404, detail="Liability not found")

        if not liability.principal_amount or not liability.interest_rate or not liability.original_tenure_months:
            return { 'schedule': [], 'message': 'Insufficient data for amortization' }

        schedule = calculate_emi_amortization(
            principal=liability.principal_amount,
            interest_rate=liability.interest_rate,
            tenure_months=liability.original_tenure_months
        )

        return { 'schedule': schedule }
    finally:
        session.close()


@router.post("/{liability_id}/close", response_model=dict)
async def close_liability(
    liability_id: str,
    payload: dict = None,
    current_user: User = Depends(get_current_user),
    db: DatabaseManager = Depends(get_db)
):
    """Close a liability and set closure metadata."""
    session = db.get_session()
    try:
        liability = session.query(Liability).filter(
            Liability.liability_id == liability_id,
            Liability.user_id == current_user.user_id
        ).first()

        if not liability:
            raise HTTPException(status_code=404, detail="Liability not found")

        liability.status = 'closed'
        liability.closure_date = datetime.now()
        if payload and 'closure_reason' in payload:
            liability.closure_reason = payload['closure_reason']

        session.commit()
        session.refresh(liability)
        return liability.to_dict()
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to close liability: {str(e)}")
    finally:
        session.close()


@router.delete("/{liability_id}")
async def delete_liability(
    liability_id: str,
    current_user: User = Depends(get_current_user),
    db: DatabaseManager = Depends(get_db)
):
    """Delete a liability"""
    session = db.get_session()
    
    try:
        liability = session.query(Liability).filter(
            Liability.liability_id == liability_id,
            Liability.user_id == current_user.user_id
        ).first()
        
        if not liability:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Liability not found"
            )
        
        session.delete(liability)
        session.commit()
        
        return {"message": "Liability deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        logger.error(f"Error deleting liability: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete liability: {str(e)}"
        )
    finally:
        session.close()

