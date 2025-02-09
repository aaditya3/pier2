import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Customers
from ..schemas import NewCustomer, Customer

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/customers", tags=["customers"])

@router.post("/", response_model=Customer)
def add_customer(customer: NewCustomer, db: Session = Depends(get_db)):
    db_customer = Customers(**customer.dict())
    db.add(db_customer)
    db.commit()
    db.refresh(db_customer)
    return db_customer

@router.get("/{customer_id}", response_model=Customer)
def get_customer(customer_id: int, db: Session = Depends(get_db)):
    customer = db.query(Customers).filter(Customers.customer_id == customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    return customer