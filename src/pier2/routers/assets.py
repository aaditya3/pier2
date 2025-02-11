import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from ..database import get_db, transactional
from ..models import Stores, Warehouses, Items
from ..schemas import NewStore, Store, NewWarehouse, Warehouse, NewItem, Item

logger = logging.getLogger(__name__)

stores_router = APIRouter(prefix="/stores", tags=["stores"])
items_router = APIRouter(prefix="/items", tags=["items"])
warehouses_router = APIRouter(prefix="/warehouses", tags=["warehouses"])

# Stores
@stores_router.post("/", response_model=Store)
@transactional
def add_store(store: NewStore, db: Session = Depends(get_db)):
    store = Stores(**store.dict())
    db.add(store)
    db.flush()
    db.refresh(store)
    return store

@stores_router.get("/{store_id}", response_model=Store)
@transactional
def get_store(store_id: int, db: Session = Depends(get_db)):
    store = db.query(Stores).filter(Stores.store_id == store_id).first()
    if not store:
        raise HTTPException(status_code=404, detail="Store not found")
    return store

# Warehouses
@warehouses_router.post("/", response_model=Warehouse)
@transactional
def add_warehouse(warehouse: NewWarehouse, db: Session = Depends(get_db)):
    warehouse = Warehouses(**warehouse.dict())
    db.add(warehouse)
    db.flush()
    db.refresh(warehouse)
    return warehouse

@warehouses_router.get("/{warehouse_id}", response_model=Warehouse)
@transactional
def get_warehouse(warehouse_id: int, db: Session = Depends(get_db)):
    warehouse = db.query(Warehouses).filter(Warehouses.warehouse_id == warehouse_id).first()
    if not warehouse:
        raise HTTPException(status_code=404, detail="warehouse not found")
    return warehouse

# Items
@items_router.post("/", response_model=Item)
@transactional
def add_item(item: NewItem, db: Session = Depends(get_db)):
    item = Items(**item.dict())
    db.add(item)
    db.flush()
    db.refresh(item)
    return item

@items_router.get("/{item_id}", response_model=Item)
@transactional
def get_item(item_id: int, db: Session = Depends(get_db)):
    item = db.query(Items).filter(Items.v == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    return Item