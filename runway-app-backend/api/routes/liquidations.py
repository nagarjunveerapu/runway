"""
Liquidation API Routes

CRUD operations for liquidation events
"""

from fastapi import APIRouter, HTTPException, Depends, status
from typing import List
import logging
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from storage.models import Liquidation, User
from storage.database import DatabaseManager
from auth.dependencies import get_current_user, get_db
from config import Config

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/", response_model=List[dict])
async def get_liquidations(
    current_user: User = Depends(get_current_user),
    db: DatabaseManager = Depends(get_db)
):
    """Get all liquidations for the current user"""
    session = db.get_session()
    
    try:
        liquidations = session.query(Liquidation).filter(
            Liquidation.user_id == current_user.user_id
        ).all()
        
        return [liq.to_dict() for liq in liquidations]
    finally:
        session.close()


@router.get("/{liquidation_id}", response_model=dict)
async def get_liquidation(
    liquidation_id: str,
    current_user: User = Depends(get_current_user),
    db: DatabaseManager = Depends(get_db)
):
    """Get a single liquidation by ID"""
    session = db.get_session()
    
    try:
        liquidation = session.query(Liquidation).filter(
            Liquidation.liquidation_id == liquidation_id,
            Liquidation.user_id == current_user.user_id
        ).first()
        
        if not liquidation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Liquidation not found"
            )
        
        return liquidation.to_dict()
    finally:
        session.close()


@router.post("/", response_model=dict, status_code=status.HTTP_201_CREATED)
async def create_liquidation(
    liquidation_data: dict,
    current_user: User = Depends(get_current_user),
    db: DatabaseManager = Depends(get_db)
):
    """Create a new liquidation event"""
    session = db.get_session()
    
    try:
        # Calculate net received
        gross_proceeds = liquidation_data.get('gross_proceeds', 0)
        fees = liquidation_data.get('fees', 0)
        net_received = gross_proceeds - fees
        
        # Create liquidation
        liquidation = Liquidation(
            liquidation_id=str(uuid.uuid4()),
            user_id=current_user.user_id,
            asset_id=liquidation_data.get('asset_id'),
            date=liquidation_data.get('date'),
            gross_proceeds=gross_proceeds,
            fees=fees,
            net_received=net_received,
            quantity_sold=liquidation_data.get('quantity_sold'),
            notes=liquidation_data.get('notes')
        )
        
        session.add(liquidation)
        session.commit()
        session.refresh(liquidation)
        
        return liquidation.to_dict()
    except Exception as e:
        session.rollback()
        logger.error(f"Error creating liquidation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create liquidation: {str(e)}"
        )
    finally:
        session.close()


@router.delete("/{liquidation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_liquidation(
    liquidation_id: str,
    current_user: User = Depends(get_current_user),
    db: DatabaseManager = Depends(get_db)
):
    """Delete a liquidation event"""
    session = db.get_session()
    
    try:
        liquidation = session.query(Liquidation).filter(
            Liquidation.liquidation_id == liquidation_id,
            Liquidation.user_id == current_user.user_id
        ).first()
        
        if not liquidation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Liquidation not found"
            )
        
        session.delete(liquidation)
        session.commit()
    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        logger.error(f"Error deleting liquidation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete liquidation: {str(e)}"
        )
    finally:
        session.close()

