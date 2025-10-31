"""
Asset API Routes

CRUD operations for assets with auto-detection from EMI patterns
"""

from fastapi import APIRouter, HTTPException, Depends, status
from typing import List, Optional
from pydantic import BaseModel
import logging
import sys
import uuid
from pathlib import Path
from collections import defaultdict
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from storage.models import Asset, User, Transaction
from storage.database import DatabaseManager
from auth.dependencies import get_current_user, get_db
from config import Config
from utils.date_parser import parse_date

logger = logging.getLogger(__name__)

router = APIRouter()

# Pydantic models
class DetectedAsset(BaseModel):
    """Auto-detected asset from EMI patterns"""
    merchant: str
    emi_amount: float
    transaction_count: int
    estimated_loan_amount: Optional[float] = None
    estimated_interest_rate: Optional[float] = None
    suggested_asset_type: str  # "property", "vehicle", "other"
    confidence: str  # "high", "medium", "low"


class AssetDetectionResponse(BaseModel):
    """Response from asset detection"""
    detected_assets: List[DetectedAsset]
    message: str


@router.get("/detect-from-emis", response_model=AssetDetectionResponse)
async def detect_assets_from_emis(
    current_user: User = Depends(get_current_user),
    db: DatabaseManager = Depends(get_db)
):
    """
    Auto-detect potential assets from recurring EMI/loan payments

    Analyzes transaction history to find recurring loan payments and suggests
    corresponding assets (property, vehicle, etc.)
    """
    try:
        session = db.get_session()

        # Get all transactions for the user
        transactions = session.query(Transaction).filter(
            Transaction.user_id == current_user.user_id,
            Transaction.type == "debit"
        ).all()

        # Group by merchant and amount to find recurring patterns
        merchant_patterns = defaultdict(lambda: {'amounts': defaultdict(list), 'txns': []})

        for txn in transactions:
            merchant = txn.merchant_canonical or "Unknown"
            amount = round(txn.amount, -2)  # Round to nearest 100 for grouping

            # Filter for potential EMI keywords
            description_lower = (txn.description_raw or "").lower()
            category_lower = (txn.category or "").lower()

            is_potential_emi = any(keyword in description_lower or keyword in category_lower
                                  for keyword in ['emi', 'loan', 'mortgage', 'finance', 'installment', 'hdfc', 'icici', 'sbi', 'axis'])

            if is_potential_emi:
                merchant_patterns[merchant]['amounts'][amount].append(txn)
                merchant_patterns[merchant]['txns'].append(txn)

        # Detect recurring EMIs (3+ transactions of same amount)
        detected = []

        for merchant, data in merchant_patterns.items():
            for amount, txn_list in data['amounts'].items():
                if len(txn_list) >= 3:  # Recurring pattern
                    # Determine asset type from merchant/description
                    asset_type = "other"
                    confidence = "medium"

                    merchant_lower = merchant.lower()
                    sample_desc = txn_list[0].description_raw.lower() if txn_list[0].description_raw else ""

                    # Property/Home loan indicators
                    if any(keyword in merchant_lower or keyword in sample_desc
                          for keyword in ['home', 'housing', 'mortgage', 'property', 'hdfc home', 'lic housing']):
                        asset_type = "property"
                        confidence = "high"

                    # Vehicle loan indicators
                    elif any(keyword in merchant_lower or keyword in sample_desc
                            for keyword in ['car', 'vehicle', 'auto', 'bike', 'motor', 'honda', 'toyota', 'maruti']):
                        asset_type = "vehicle"
                        confidence = "high"

                    # Personal/other loans
                    elif any(keyword in merchant_lower or keyword in sample_desc
                            for keyword in ['personal', 'loan', 'finance', 'credit']):
                        asset_type = "other"
                        confidence = "low"

                    # Estimate loan amount (rough calculation)
                    # Assuming typical 8-10% interest, 5-20 year tenure
                    # EMI = P * r * (1+r)^n / ((1+r)^n - 1)
                    # Rough estimate: Loan amount = EMI * 60 (assuming 5 year tenure)
                    estimated_loan = amount * 60

                    detected.append(DetectedAsset(
                        merchant=merchant,
                        emi_amount=amount,
                        transaction_count=len(txn_list),
                        estimated_loan_amount=estimated_loan,
                        estimated_interest_rate=9.0,  # Typical rate
                        suggested_asset_type=asset_type,
                        confidence=confidence
                    ))

        # Sort by confidence and EMI amount
        confidence_order = {"high": 0, "medium": 1, "low": 2}
        detected.sort(key=lambda x: (confidence_order[x.confidence], -x.emi_amount))

        session.close()

        message = f"Found {len(detected)} potential assets from EMI patterns" if detected else "No recurring EMI patterns detected"

        return AssetDetectionResponse(
            detected_assets=detected,
            message=message
        )

    except Exception as e:
        logger.error(f"Error detecting assets from EMIs: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to detect assets: {str(e)}"
        )


@router.get("/", response_model=List[dict])
async def get_assets(
    current_user: User = Depends(get_current_user),
    db: DatabaseManager = Depends(get_db)
):
    """Get all assets for the current user"""
    session = db.get_session()
    
    try:
        assets = session.query(Asset).filter(
            Asset.user_id == current_user.user_id
        ).all()

        # Deduplicate by recurring_pattern_id (if present): keep most recently updated
        by_pattern = {}
        unique_assets = []
        for a in assets:
            pid = getattr(a, 'recurring_pattern_id', None)
            if not pid:
                unique_assets.append(a)
                continue
            existing = by_pattern.get(pid)
            if not existing:
                by_pattern[pid] = a
            else:
                prev_updated = existing.updated_at or existing.created_at
                curr_updated = a.updated_at or a.created_at
                if curr_updated and prev_updated and curr_updated > prev_updated:
                    by_pattern[pid] = a
        unique_assets.extend([v for v in by_pattern.values()])
        
        return [asset.to_dict() for asset in unique_assets]
    finally:
        session.close()


@router.get("/{asset_id}", response_model=dict)
async def get_asset(
    asset_id: str,
    current_user: User = Depends(get_current_user),
    db: DatabaseManager = Depends(get_db)
):
    """Get a single asset by ID"""
    session = db.get_session()
    
    try:
        asset = session.query(Asset).filter(
            Asset.asset_id == asset_id,
            Asset.user_id == current_user.user_id
        ).first()
        
        if not asset:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Asset not found"
            )
        
        return asset.to_dict()
    finally:
        session.close()


@router.post("/", response_model=dict, status_code=status.HTTP_201_CREATED)
async def create_asset(
    asset_data: dict,
    current_user: User = Depends(get_current_user),
    db: DatabaseManager = Depends(get_db)
):
    """Create a new asset"""
    session = db.get_session()
    
    try:
        # Parse purchase_date if provided
        purchase_date = asset_data.get('purchase_date')
        if purchase_date:
            # Parse date string to datetime object
            parsed_date_str = parse_date(purchase_date)
            if parsed_date_str:
                purchase_date = datetime.strptime(parsed_date_str, '%Y-%m-%d').date()
            else:
                purchase_date = None
        
        # Upsert by recurring_pattern_id to avoid duplicates for same EMI mapping
        existing = None
        rp_id = asset_data.get('recurring_pattern_id')
        if rp_id:
            existing = session.query(Asset).filter(
                Asset.user_id == current_user.user_id,
                Asset.recurring_pattern_id == rp_id
            ).first()

        # Create or update
        if existing:
            existing.name = asset_data.get('name', existing.name)
            existing.asset_type = asset_data.get('asset_type', existing.asset_type)
            existing.quantity = asset_data.get('quantity', existing.quantity)
            existing.purchase_price = asset_data.get('purchase_price', existing.purchase_price)
            existing.current_value = asset_data.get('current_value', existing.current_value)
            existing.purchase_date = purchase_date or existing.purchase_date
            existing.notes = asset_data.get('notes', existing.notes)
            session.commit()
            session.refresh(existing)
            return existing.to_dict()

        asset = Asset(
            asset_id=str(uuid.uuid4()),
            user_id=current_user.user_id,
            name=asset_data.get('name'),
            asset_type=asset_data.get('asset_type'),
            quantity=asset_data.get('quantity'),
            purchase_price=asset_data.get('purchase_price'),
            current_value=asset_data.get('current_value'),
            purchase_date=purchase_date,
            recurring_pattern_id=asset_data.get('recurring_pattern_id'),
            liquid=asset_data.get('liquid', False),
            disposed=asset_data.get('disposed', False),
            notes=asset_data.get('notes')
        )
        
        session.add(asset)
        session.commit()
        session.refresh(asset)
        
        return asset.to_dict()
    except Exception as e:
        session.rollback()
        logger.error(f"Error creating asset: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create asset: {str(e)}"
        )
    finally:
        session.close()


@router.patch("/{asset_id}", response_model=dict)
async def update_asset(
    asset_id: str,
    asset_data: dict,
    current_user: User = Depends(get_current_user),
    db: DatabaseManager = Depends(get_db)
):
    """Update an existing asset"""
    session = db.get_session()
    
    try:
        asset = session.query(Asset).filter(
            Asset.asset_id == asset_id,
            Asset.user_id == current_user.user_id
        ).first()
        
        if not asset:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Asset not found"
            )
        
        # Update fields
        if 'name' in asset_data:
            asset.name = asset_data['name']
        if 'asset_type' in asset_data:
            asset.asset_type = asset_data['asset_type']
        if 'quantity' in asset_data:
            asset.quantity = asset_data['quantity']
        if 'purchase_price' in asset_data:
            asset.purchase_price = asset_data['purchase_price']
        if 'current_value' in asset_data:
            asset.current_value = asset_data['current_value']
        if 'purchase_date' in asset_data:
            asset.purchase_date = asset_data['purchase_date']
        if 'liquid' in asset_data:
            asset.liquid = asset_data['liquid']
        if 'disposed' in asset_data:
            asset.disposed = asset_data['disposed']
        if 'recurring_pattern_id' in asset_data:
            asset.recurring_pattern_id = asset_data['recurring_pattern_id']
        if 'notes' in asset_data:
            asset.notes = asset_data['notes']
        
        session.commit()
        session.refresh(asset)
        
        return asset.to_dict()
    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        logger.error(f"Error updating asset: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update asset: {str(e)}"
        )
    finally:
        session.close()


@router.delete("/{asset_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_asset(
    asset_id: str,
    current_user: User = Depends(get_current_user),
    db: DatabaseManager = Depends(get_db)
):
    """Delete an asset"""
    session = db.get_session()
    
    try:
        asset = session.query(Asset).filter(
            Asset.asset_id == asset_id,
            Asset.user_id == current_user.user_id
        ).first()
        
        if not asset:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Asset not found"
            )
        
        session.delete(asset)
        session.commit()
    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        logger.error(f"Error deleting asset: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete asset: {str(e)}"
        )
    finally:
        session.close()

