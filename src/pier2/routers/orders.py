import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from ..database import get_db
from ..models import Orders, OrderItems, CustomerAddresess, FulfillmentModality
from ..schemas import NewOrder, NewOrderItem, Order, OrderItem


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/orders", tags=["orders"])


# FIXME: Consider optimization this function. It's doing a lot of (possibly inneficient) queries.
@router.post("/", response_model=Order)
def add_order(order: NewOrder, items: List[NewOrderItem], db: Session = Depends(get_db)):
    db_order = Orders(**order.dict())
    items = [OrderItems(**item.dict()) for item in items]

    for item in items:
        item.order = db_order

    db_order.items = items
    db.add(db_order)
    results = db.query(CustomerAddresess).filter(
        CustomerAddresess.customer_address_id == order.dict()['billing_address_id']).first()

    if not results:
        raise HTTPException(status_code=422, detail="The billing address id is invalid.")
    if not results.is_billing:
        raise HTTPException(status_code=422, detail="The address provided for billing is not marked as a billing address.")

    shipping_home_address_ids = [item.dest_customer_address_id for item in items
                               if item.fulfillment_modality in
                               [FulfillmentModality.store_to_home, FulfillmentModality.ware_to_home]]

    shipping_home_addresses = db.query(CustomerAddresess).filter(
        CustomerAddresess.customer_address_id.in_(shipping_home_address_ids)).all()

    shipping_home_addresses = {ad.customer_address_id: ad.is_shipping for ad in shipping_home_addresses}
    if not all(shipping_home_addresses.values()):
        raise HTTPException(status_code=422,
                            detail = "Some shipping addresses are not marked as is_shipping. ")

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
