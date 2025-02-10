import enum

from sqlalchemy import Column, Identity, Enum as SQLEnum, DateTime, Integer, String, Float, Boolean, ForeignKey
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

# FIXME: nullable is true by efault. index is False by default.
# which are unique?
class Customers(Base):
    __tablename__ = "customers"

    customer_id = Column(Integer, Identity(), primary_key=True, index=True)  # consider uuid or similar
    email = Column(String, unique = True, index = True, nullable = False)
    first_name = Column(String, index = False)
    last_name = Column(String, index=False)
    phone = Column(String, unique = True, index=False)   # FIXME: Consider supporting multiple phone numbers in the future (similar to addresses)
    addresses = relationship("CustomerAddresess", back_populates="customer")


class CustomerAddresess(Base):
    __tablename__ = "customer_addresses"

    customer_address_id = Column(Integer, Identity(), primary_key=True, index=True)
    address_line_1 = Column(String, index=False)
    address_line_2 = Column(String, index=False)
    city = Column(String, index=False)
    state = Column(String(2), index=False)
    zip_code = Column(String(5), index = False)
    is_billing = Column(Boolean, index = False)
    is_shipping = Column(Boolean, index = False)

    customer_id = Column(Integer, ForeignKey('customers.customer_id'))
    customer = relationship("Customers", back_populates="addresses")


# FIXME: Review this index = False everywhere?
class Orders(Base):
    __tablename__ = "orders"

    order_id = Column(Integer, Identity(), primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey('customers.customer_id'))
    time_of_order = Column(DateTime, index = False)
    source = Column(SQLEnum(OrderSource), index = False)
    items = relationship("OrderItems", back_populates="order")
    billing_address_id = Column(Integer, ForeignKey('customer_addresses.customer_address_id'))


# FIXME: Consider adding a unique constraint where it would make sense.
class OrderItems(Base):

    __tablename__ = "order_items"

    order_item_id = Column(Integer, Identity(), primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey('orders.order_id'))
    order = relationship("Orders", back_populates="items")

    item_id = Column(Integer, ForeignKey('items.item_id'))
    fulfillment_modality = Column(SQLEnum(FulfillmentModality), index = True)
    quantity = Column(Integer, index = False)
    price_per_item = Column(Float, index = False)

    source_warehouse_id = Column(Integer, ForeignKey('warehouses.warehouse_id'))
    source_store_id = Column(Integer, ForeignKey('stores.store_id'))
    dest_store_id = Column(Integer, ForeignKey('stores.store_id'))

    # FIXME: Below make sure to validate that the addresses is a is_shipping True or make it so.
    dest_customer_address_id = Column(Integer, ForeignKey('customer_addresses.customer_address_id'))


class Stores(Base):
    __tablename__ = "stores"

    store_id = Column(Integer, Identity(), primary_key=True, index=True)

class Warehouses(Base):
    __tablename__ = "warehouses"

    warehouse_id = Column(Integer, Identity(), primary_key=True, index=True)


class Items(Base):
    __tablename__ = "items"

    item_id = Column(Integer, Identity(), primary_key=True, index=True)

'''

Should be considered. Will be ignoring for this exercise.


class StoreInventory(Base):
    pass

class WarehouseInventory(Base):
    pass

'''