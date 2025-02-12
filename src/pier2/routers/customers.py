import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db, transactional
from ..models import Customers, CustomerAddresess
from ..schemas import NewCustomer, Customer, NewCustomerAddress, CustomerAddress

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/customers", tags=["customers"])

@router.post("/", response_model=Customer)
@transactional
def add_customer(customer: NewCustomer, db: Session = Depends(get_db)):
    db_customer = Customers(**customer.dict())
    db.add(db_customer)
    db.flush()
    db.refresh(db_customer)
    return db_customer

@router.get("/{customer_id}", response_model=Customer)
@transactional
def get_customer(customer_id: int, db: Session = Depends(get_db)):
    customer = db.query(Customers).filter(Customers.customer_id == customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    return customer

@router.post("/addresses", response_model=CustomerAddress)
@transactional
def add_customer_address(customer_address: NewCustomerAddress, db: Session = Depends(get_db)):
    db_customer_add = CustomerAddresess(**customer_address.dict())
    db.add(db_customer_add)
    db.flush()
    db.refresh(db_customer_add)
    return db_customer_add

@router.get("/addresses/{customer_address_id}", response_model=CustomerAddress)
@transactional
def get_customer_address(customer_address_id: int, db: Session = Depends(get_db)):
    customer_add = db.query(CustomerAddresess).filter(CustomerAddresess.customer_address_id == customer_address_id).first()
    if not customer_add:
        raise HTTPException(status_code=404, detail="Customer address not found")
    return customer_add

