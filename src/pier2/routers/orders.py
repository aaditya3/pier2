import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from ..database import get_db
from ..models import Orders, OrderItems
from ..schemas import NewOrder, NewOrderItem, Order, OrderItem


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/orders", tags=["orders"])

@router.post("/", response_model=Order)
def add_order(order: NewOrder, items: List[NewOrderItem], db: Session = Depends(get_db)):
    db_order = Orders(**order.dict())
    items = [OrderItems(**item.dict()) for item in items]

    for item in items:
        item.order = db_order

    db_order.items = items

    db.add(db_order)
    db.commit()
    db.refresh(db_order)

    for item in items:
        db.refresh(item)

    return db_order

@router.get("/{order_id}", response_model=Order)
def get_customer(order_id: int, db: Session = Depends(get_db)):
    order = db.query(Orders).filter(Orders.order_id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order
