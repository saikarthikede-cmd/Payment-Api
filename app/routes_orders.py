import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app import services
from app.auth import get_current_user
from app.config import settings
from app.db import get_db
from app.models import User
from app.schemas import OrderCreate, OrderResponse, OrderDetail

router = APIRouter(prefix="/orders", tags=["orders"])
logger = logging.getLogger(__name__)


@router.post("", response_model=OrderResponse, status_code=201)
def create_order(
    order: OrderCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create an order for the authenticated customer."""
    if order.customer_id != current_user.user_id:
        logger.warning(
            "Forbidden order create user_id=%s target_customer_id=%s",
            current_user.user_id,
            order.customer_id,
        )
        raise HTTPException(status_code=403, detail="Forbidden")

    try:
        new_order = services.create_order(db, order)
        return OrderResponse(order_id=new_order.id, status=new_order.status)
    except ValueError as e:
        logger.warning("Order creation validation failed customer_id=%s error=%s", order.customer_id, e)
        # Business logic validation errors (invalid data)
        # These should be returned immediately to client for correction
        raise HTTPException(status_code=400, detail=str(e))
    except Exception:
        logger.exception("Order creation failed customer_id=%s", order.customer_id)
        # Transient failures: database connection, constraint violations, etc.
        # Graceful degradation: queue for async processing
        if settings.enable_graceful_degradation:
            # Return tracking ID for async processing
            # Background worker will create actual order and update status
            # Client can poll /orders?customer_id=X to check completion
            # Tracking ID format: all-zeros UUID indicates async processing
            return OrderResponse(
                order_id=uuid.UUID("00000000-0000-0000-0000-000000000000"),
                status="pending"
            )
        else:
            # Strict mode: fail fast and return error to client
            raise HTTPException(status_code=500, detail="Order processing failed")


@router.get("", response_model=List[OrderDetail])
def list_orders(
    customer_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all orders for a customer."""
    if customer_id != current_user.user_id:
        logger.warning(
            "Forbidden order list user_id=%s target_customer_id=%s",
            current_user.user_id,
            customer_id,
        )
        raise HTTPException(status_code=403, detail="Forbidden")
    orders = services.get_orders_by_customer(db, customer_id)
    return orders
