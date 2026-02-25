import logging
from decimal import Decimal, InvalidOperation

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app import services
from app.auth import get_current_user
from app.db import get_db
from app.models import User
from app.schemas import WalletOperation, WalletResponse

router = APIRouter(prefix="/wallet", tags=["wallet"])
logger = logging.getLogger(__name__)


def _wallet_response(customer_id: str, balance: Decimal | float | int | str | None) -> WalletResponse:
    """Normalize wallet balance for API response."""
    try:
        normalized = float(Decimal(str(balance if balance is not None else 0)))
    except (InvalidOperation, ValueError):
        normalized = 0.0
    return WalletResponse(customer_id=customer_id, balance=normalized)


@router.post("/{customer_id}/credit", response_model=WalletResponse)
def credit_wallet(
    customer_id: str,
    operation: WalletOperation,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Credit amount to customer wallet."""
    if customer_id != current_user.user_id:
        logger.warning(
            "Forbidden wallet credit requester=%s target=%s",
            current_user.user_id,
            customer_id,
        )
        raise HTTPException(status_code=403, detail="Forbidden")
    try:
        wallet = services.credit_wallet(db, customer_id, operation.amount)
        return _wallet_response(str(wallet.customer_id), wallet.balance)
    except ValueError as e:
        logger.warning("Wallet credit validation failed customer_id=%s error=%s", customer_id, e)
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{customer_id}/debit", response_model=WalletResponse)
def debit_wallet(
    customer_id: str,
    operation: WalletOperation,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Debit amount from customer wallet."""
    if customer_id != current_user.user_id:
        logger.warning(
            "Forbidden wallet debit requester=%s target=%s",
            current_user.user_id,
            customer_id,
        )
        raise HTTPException(status_code=403, detail="Forbidden")
    try:
        wallet = services.debit_wallet(db, customer_id, operation.amount)
        return _wallet_response(str(wallet.customer_id), wallet.balance)
    except ValueError as e:
        logger.warning("Wallet debit validation failed customer_id=%s error=%s", customer_id, e)
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{customer_id}", response_model=WalletResponse)
def get_wallet(
    customer_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get wallet balance for a customer."""
    if customer_id != current_user.user_id:
        logger.warning(
            "Forbidden wallet fetch requester=%s target=%s",
            current_user.user_id,
            customer_id,
        )
        raise HTTPException(status_code=403, detail="Forbidden")
    try:
        wallet = services.get_wallet(db, customer_id)
        return _wallet_response(str(wallet.customer_id), wallet.balance)
    except ValueError as e:
        logger.warning("Wallet fetch validation failed customer_id=%s error=%s", customer_id, e)
        raise HTTPException(status_code=400, detail=str(e))
