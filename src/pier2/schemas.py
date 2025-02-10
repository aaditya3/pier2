from pydantic import BaseModel, ValidationError, validator, model_validator
from typing import Optional, List
from typing_extensions import Self
import re
from .models import FulfillmentModality, OrderSource
import datetime


states = [
    "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA",
    "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD",
    "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ",
    "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC",
    "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY"
]

def validate_phone_number(phone: Optional[str]) -> Optional[str]:
    if phone is None:
        return None

    phone_regex = r"^\d{3}-\d{3}-\d{4}$"

    if not re.match(phone_regex, phone):
        raise ValueError("Invalid phone number format.")

    return phone

def validate_email(email: str) -> str:


    email_regex = r"[^@\s]+@[^@\s]+\.[^@\s]+"

    if not re.match(email_regex, email):
        raise ValueError("Invalid email format.")

    return email

def validate_state(state: str) -> str:
    upper_state = state.upper()
    if upper_state not in states:
        raise ValueError(f"Invalid state {state}.")

    return upper_state

# FIXME: Obviously need to check zipcode beyond just format.
def validate_zip(zip: str) -> str:

    zip_regex = r"^\d{5}$"

    if not re.match(zip_regex, zip):
        raise ValueError("Invalid zip code.")

    return zip

class Customer(BaseModel):
    customer_id: int
    email: str
    first_name: str
    last_name: str
    phone: Optional[str] = None

class NewCustomer(BaseModel):
    email: str
    _email_validator = validator("email")(validate_email)
    first_name: str
    last_name: str
    phone: Optional[str] = None
    _phone_validator = validator("phone")(validate_phone_number)

class CustomerAddress(BaseModel):
    customer_address_id: int
    address_line_1: str
    address_line_2: Optional[str]
    city: str
    state: str
    zip_code: str
    is_billing: Optional[bool]
    is_shipping: Optional[bool]

class NewCustomerAddress(BaseModel):

    address_line_1: str    #FIXME consider some kind of validation here.
    address_line_2: Optional[str] = None
    city: str
    state: str

    zip_code: str
    _zip_validator: validator("zip_code")(validate_zip)

    is_billing: Optional[bool] = False
    is_shipping: Optional[bool] = False

    @model_validator(mode='after')
    def validate_billing_shipping(self) -> Self:
        if not self.is_billing and not self.is_shipping:
            raise ValueError("An address must be either set to shipping or billing or both. Got false for both.")
        return self


class NewStore(BaseModel):
    pass

class NewWarehouse(BaseModel):
    pass

class NewItem(BaseModel):
    pass

class Store(BaseModel):
    store_id: int

class Warehouse(BaseModel):
    warehouse_id: int

class Item(BaseModel):
    item_id: int


class NewOrderItem(BaseModel):

    item_id: int
    fulfillment_modality: FulfillmentModality
    quantity: int
    price_per_item: float

    source_warehouse_id: Optional[int] = None
    source_store_id: Optional[int] = None
    dest_store_id: Optional[int] = None
    dest_customer_address_id: Optional[int] = None

    @model_validator(mode='after')
    def validate_datetime(self) -> Self:
        """
            Only 1 of source and one of dest. should be set.

            fulfillment_modality is actually redundant as that information is implicitly
            available in the source/dest id's. But in this case being explicit
            at the cost of being redundant.
        """
        fulfillment_modality = self.fulfillment_modality
        source_warehouse_id = self.source_warehouse_id
        source_store_id = self.source_store_id
        dest_store_id = self.dest_store_id
        dest_customer_address_id = self.dest_customer_address_id


        if fulfillment_modality in [FulfillmentModality.ware_to_home, FulfillmentModality.ware_to_store]:
                if source_warehouse_id is None:
                    raise ValueError(f"source_warehouse_id must be input when FulfillmentModality is {fulfillment_modality}")

                if fulfillment_modality == FulfillmentModality.ware_to_home:
                    if dest_customer_address_id is None:
                        raise ValueError(f"dest_customer_address_id must be input when FulfillmentModality is {fulfillment_modality}")

                    if source_store_id or dest_store_id:
                        raise ValueError(f"Cannot supply source_store_id {source_store_id} or dest_store_id {dest_store_id} when {fulfillment_modality}.")

                if fulfillment_modality == FulfillmentModality.ware_to_store:
                    if dest_store_id is None:
                        raise ValueError(f"dest_store_id must be input when FulfillmentModality is {fulfillment_modality}")
                    if source_store_id or dest_customer_address_id:
                        raise ValueError(f"Cannot supply source_store_id {source_store_id} or dest_customer_address_id {dest_customer_address_id} when {fulfillment_modality}.")


        if fulfillment_modality == FulfillmentModality.store_to_home:

            if source_store_id is None:
                raise ValueError(f"source_store_id must be input when FulfillmentModality is {fulfillment_modality}")

            if dest_customer_address_id is None:
                raise ValueError(f"dest_customer_address_id must be input when FulfillmentModality is {fulfillment_modality}")

            if source_warehouse_id or dest_store_id:
                raise ValueError(f"Cannot supply source_warehouse_id {source_warehouse_id} or dest_store_id {dest_store_id} when {fulfillment_modality}.")


        if fulfillment_modality == FulfillmentModality.store_inventory:
            if source_store_id is None:
                raise ValueError(f"source_store_id must be input when FulfillmentModality is {fulfillment_modality}")

            if source_warehouse_id or dest_store_id or dest_customer_address_id:
                raise ValueError(f"Cannot supply source_warehouse_id {source_warehouse_id} or dest_store_id {dest_store_id} or dest_customer_address_id {dest_customer_address_id} when {fulfillment_modality}.")

        return self


class NewOrder(BaseModel):
    customer_id: int
    time_of_order: datetime.datetime
    source: OrderSource

    @model_validator(mode='after')
    def validate_datetime(self) -> Self:

        if not (self.time_of_order.hour != 0 or self.time_of_order.minute != 0 or self.time_of_order.second != 0):
            raise ValueError("Time of order must contain time information.")

        return self

class OrderItem(BaseModel):
    order_item_id: int
    order_id: int
    item_id: int
    fulfillment_modality: FulfillmentModality
    quantity: int
    price_per_item: float

    source_warehouse_id: Optional[int] = None
    source_store_id: Optional[int] = None
    dest_store_id: Optional[int] = None
    dest_customer_address_id: Optional[int] = None


class Order(BaseModel):
    order_id: int
    customer_id: int
    time_of_order: datetime.datetime
    source: OrderSource
    items: List[OrderItem]



