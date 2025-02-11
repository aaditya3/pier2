import enum

from sqlalchemy import Column, Identity, Enum as SQLEnum, DateTime, Integer, String, Float, Boolean, ForeignKey, UniqueConstraint
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

class FulfillmentModality(enum.Enum):
    ware_to_home = 1
    ware_to_store = 2
    store_to_home = 3
    store_inventory = 4

class OrderSource(enum.Enum):
    store = 1
    online = 2

class Customers(Base):
    __tablename__ = "customers"

    customer_id = Column(Integer, Identity(), primary_key = True, index = True)  # consider uuid or similar
    email = Column(String, unique = True, index = True, nullable = False)
    phone = Column(String, unique = True)   # FIXME: Consider supporting multiple phone numbers in the future (similar to addresses)
    first_name = Column(String, nullable = False)
    last_name = Column(String, nullable = False)

    addresses = relationship("CustomerAddresess", back_populates="customer")


class CustomerAddresess(Base):
    __tablename__ = "customer_addresses"

    customer_address_id = Column(Integer, Identity(), primary_key = True, index = True)
    address_line_1 = Column(String, nullable = False)
    address_line_2 = Column(String)
    city = Column(String, nullable = False)
    state = Column(String(2), nullable = False)
    zip_code = Column(String(5), nullable = False)
    is_billing = Column(Boolean, index = False, default = False, nullable = False)
    is_shipping = Column(Boolean, index = False, default = False, nullable = False)

    customer_id = Column(Integer, ForeignKey('customers.customer_id'), nullable = False)
    customer = relationship("Customers", back_populates="addresses")



class Orders(Base):
    __tablename__ = "orders"

    order_id = Column(Integer, Identity(), primary_key = True, index = True)
    customer_id = Column(Integer, ForeignKey('customers.customer_id'), nullable = False)
    time_of_order = Column(DateTime, nullable = False)
    source = Column(SQLEnum(OrderSource), nullable = False)
    billing_address_id = Column(Integer, ForeignKey('customer_addresses.customer_address_id'), nullable = False)

    billing_address = relationship("CustomerAddresess", foreign_keys=[billing_address_id])
    items = relationship("OrderItems", back_populates="order")


class OrderItems(Base):

    __tablename__ = "order_items"

    order_item_id = Column(Integer, Identity(), primary_key = True, index = True)
    order_id = Column(Integer, ForeignKey('orders.order_id'), nullable = False)

    item_id = Column(Integer, ForeignKey('items.item_id'), nullable = False)
    fulfillment_modality = Column(SQLEnum(FulfillmentModality), index = True, nullable = False)
    quantity = Column(Integer, nullable = False)
    price_per_item = Column(Float, nullable = False)

    source_warehouse_id = Column(Integer, ForeignKey('warehouses.warehouse_id'))
    source_store_id = Column(Integer, ForeignKey('stores.store_id'))
    dest_store_id = Column(Integer, ForeignKey('stores.store_id'))

    # FIXME: Below make sure to validate that the addresses is a is_shipping True or make it so.
    dest_customer_address_id = Column(Integer, ForeignKey('customer_addresses.customer_address_id'))

    order = relationship("Orders", back_populates="items")

    __table_args__ = (
        UniqueConstraint('order_id',
                         'item_id',
                         'source_warehouse_id',
                         'source_store_id',
                         'dest_store_id',
                         'dest_customer_address_id',
                         name='_unique_item_src_dest'),
    )


class Stores(Base):
    __tablename__ = "stores"

    store_id = Column(Integer, Identity(), primary_key = True, index = True)


class Warehouses(Base):
    __tablename__ = "warehouses"

    warehouse_id = Column(Integer, Identity(), primary_key = True, index = True)


class Items(Base):
    __tablename__ = "items"

    item_id = Column(Integer, Identity(), primary_key = True, index = True)

'''

Should be considered. Will be ignoring for this exercise.


class StoreInventory(Base):
    pass

class WarehouseInventory(Base):
    pass

'''