import logging
from sqlalchemy import func, distinct, and_
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from ..database import get_db
from ..models import Customers, CustomerAddresess, OrderItems, Orders, FulfillmentModality, OrderSource
from ..schemas import Order

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/query", tags=["query"])

@router.get("/order_history", response_model=List[Order])
def get_order_history(email: str = None, phone: str = None, db: Session = Depends(get_db)):

    if email and phone:
        raise ValueError("Both phone number and email id cannot be provided. ")

    if not email and not phone:
        raise ValueError("At least one of phone number and email id must be provided. ")

    customer = None
    if email:
        customer = db.query(Customers).filter(Customers.email == email).first()
    else:
        customer = db.query(Customers).filter(Customers.phone == phone).first()

    if not customer:
        raise HTTPException(status_code=404, detail=f"Customer not found with {f'Email {email}' if email else f'Phone: {phone}'}")
    
    orders = db.query(Orders).filter(Orders.customer_id == customer.customer_id).order_by(Orders.time_of_order).all()
    return orders

@router.get("/count_billing_orders")
def get_count_billing_orders(db: Session = Depends(get_db)):

    results = db.query(CustomerAddresess.zip_code, func.count()).join(
        Orders, Orders.billing_address_id == CustomerAddresess.customer_address_id).group_by(
            CustomerAddresess.zip_code).order_by(func.count().desc()).all()
    return {r[0]: r[1] for r in results}

@router.get("/count_by_shipping_zip")
def get_count_by_shipping_zip(db: Session = Depends(get_db)):

    valid_fulfillment_modalities = [FulfillmentModality.store_to_home, FulfillmentModality.ware_to_home]

    results = db.query(CustomerAddresess.zip_code, func.count(distinct(OrderItems.order_id))).join(
        OrderItems, OrderItems.dest_customer_address_id == CustomerAddresess.customer_address_id).filter(
            OrderItems.fulfillment_modality.in_(valid_fulfillment_modalities)).group_by(
                CustomerAddresess.zip_code).order_by(func.count(distinct(OrderItems.order_id)).desc()).all()

    return {r[0]: r[1] for r in results}

@router.get("/instore_shoppers")
def get_instore_shoppers(top_k: int = 5, db: Session = Depends(get_db)):
    results = db.query(Orders.customer_id, func.count()).filter(Orders.source == OrderSource.store).group_by(
        Orders.customer_id).order_by(func.count().desc()).limit(top_k).all()
    return {r[0]: r[1] for r in results}