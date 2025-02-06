from pydantic import BaseModel

class AddCustomer(BaseModel):
    email: str

class Customer(BaseModel):
    customer_id: int
    email: str
