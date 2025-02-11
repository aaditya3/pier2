import requests
import json
import yaml
import os
import pytest
from datetime import datetime
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlmodel.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine


from pier2.database import get_db
from pier2.models import Base, FulfillmentModality, OrderSource
from pier2.main import app

IN_MEMORY_DB = "sqlite:///:memory:"
FILE_DB = "sqlite:///./test.db"

def select_db():
    return IN_MEMORY_DB

def _print_json(data):
    print(json.dumps(data, indent=4))

def add_store(client):
    resp = client.post(f'/stores', json = {})
    result = json.loads(resp.text)
    print("Added store:", result['store_id'])
    return result['store_id']
    
def add_warehouse(client):
    resp = client.post(f'/warehouses', json = {})
    result = json.loads(resp.text)
    print("Added warehouse:", result['warehouse_id'])
    return result['warehouse_id']

def add_item(client):
    resp = client.post(f'/items', json = {})
    result = json.loads(resp.text)
    print("Added item:", result['item_id'])
    return result['item_id']

def add_customer(client, email = "pink@floyd.com"):
    customer_data = {
        'email': email,
        'first_name': "Pink",
        'last_name': "Floyd"
    }
    resp = client.post(f'/customers', json = customer_data)
    result = json.loads(resp.text)
    print("Added customer:", result['customer_id'])
    return result['customer_id']

def add_customer_address(client, customer_id):
    customer_data = {
        'customer_id': customer_id,
        'address_line_1': '34 Haight',
        'city': 'San Francisco',
        'state': 'CA',
        'zip_code': "94131",
        'is_billing': True,
        'is_shipping': True
    }
    
    resp = client.post(f'/customers/addresses', json = customer_data)
    result = json.loads(resp.text)
    print("Added customer address:", result['customer_address_id'])
    return result['customer_address_id']

def add_order(client, customer_id, customer_address_id, item_id):
    items = [
        {'item_id': item_id,
            'fulfillment_modality': FulfillmentModality.store_to_home.value,
            'quantity': 3,
            'price_per_item': 3.2,
            'source_store_id': 1,
            'dest_customer_address_id': customer_address_id
        }
    ]

    order_data = {
        'customer_id': customer_id,
        'time_of_order': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        'source': OrderSource.online.value,
        'billing_address_id': customer_address_id
    }
    
    data = {
        'items' : items,
        'order': order_data
    }
    

    resp = client.post(f'/orders', json = data)
    result = json.loads(resp.text)
    print(result)
    print("Added order:", result['order_id'])
    return result['order_id']


@pytest.fixture(name="session")
def session_fixture():
    which_db = select_db()

    engine = create_engine(
        which_db, connect_args={"check_same_thread": False}, poolclass = StaticPool
    )

    # Apparently SQL Lite will need it turned on explicitly.
    if which_db in [FILE_DB, IN_MEMORY_DB]:
        @event.listens_for(engine, "connect")
        def do_connect(dbapi_connection, connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys = ON")
            cursor.close()
    
    Base.metadata.create_all(engine)
    print(f"*** Created tables {Base.metadata.tables.keys()}")
    with Session(engine) as session:
        yield session

@pytest.fixture(name="client")
def client_fixture(session: Session):
    def get_session_override():
        return session

    app.dependency_overrides[get_db] = get_session_override
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


def test_add_customer(client: TestClient):

    # Check empty db
    resp = client.get(f'/customers/123456789')
    assert resp.status_code == 404

    # Check incomplete data
    resp = client.post(f'/customers', json = {'email': "pink@floyd.com"})
    assert resp.status_code == 422
    result = json.loads(resp.text)
    print(f"** Recieved from server after post: {result}")

    # Check bad email
    customer_data = {
        'email': "pinkfloyd.com",
        'first_name': "Pink",
        'last_name': "Floyd"
    }

    # FIXME: Add check fo empty first and last name

    resp = client.post(f'/customers', json = customer_data)
    assert resp.status_code == 422, resp.content
    result = json.loads(resp.text)
    print(f"** Recieved from server after post: {result}")

    customer_data = {
        "email": "pink@floyd.com",
        "first_name": "Pink",
        "last_name": "Floyd"
    }
    resp = client.post(f'/customers', json = customer_data)
    assert resp.status_code == 200, resp.content
    result = json.loads(resp.text)
    print(f"** Recieved from server after post: {result}")

    resp = client.get(f'/customers/{result['customer_id']}')
    assert resp.status_code == 200
    result = json.loads(resp.text)
    print(f"** Recieved from server after create: {result}")

def test_add_customer_address(client: TestClient):

    customer_id = add_customer(client)

    ## Customer address test
    customer_data = {
        'customer_id': customer_id,
        'address_line_1': '34 Haight',
        'city': 'San Francisco',
        'state': 'CA',
        'zip_code': "94131",
        'is_billing': False

    }

    resp = client.post(f'/customers/addresses', json = customer_data)
    assert resp.status_code == 422, resp.content
    result = json.loads(resp.text)
    print(f"** Recieved from server after post: {result}")


    customer_data['is_billing'] = True
    resp = client.post(f'/customers/addresses', json = customer_data)
    assert resp.status_code == 200, resp.content
    result = json.loads(resp.text)
    print(f"** Recieved from server after post: {result}")

    resp = client.get(f'/customers/addresses/{result['customer_address_id']}')
    assert resp.status_code == 200
    result = json.loads(resp.text)
    print(f"** Recieved from server after create: {result}")


def test_add_order(client: TestClient):

    add_store(client)
    add_warehouse(client)
    item_id = add_item(client)
    customer_id = add_customer(client)
    customer_address_id = add_customer_address(client, customer_id)

    items = [
        {'item_id': item_id,
            'fulfillment_modality': FulfillmentModality.store_to_home.value,
            'quantity': 3,
            'price_per_item': 3.2,
            'source_store_id': 1,
            'dest_customer_address_id': customer_address_id
        }
    ]

    order_data = {
        'customer_id': customer_id,
        'time_of_order': '2025-02-09 14:14:37',
        'source': OrderSource.online.value,
        'billing_address_id': customer_address_id
    }
    
    data = {
        'items' : items,
        'order': order_data
    }

    resp = client.post(f'/orders', json = data)
    assert resp.status_code == 200, resp.content
    result = json.loads(resp.text)
    print(f"** Recieved from server after post: {result}")

def test_order_history_query(client: TestClient):
    email = "a@b.com"

    add_store(client)
    add_warehouse(client)
    item_id = add_item(client)
    customer_id = add_customer(client, email)
    customer_address_id = add_customer_address(client, customer_id)
    for i in range(5):
        order_id = add_order(client, customer_id, customer_address_id, item_id)


    data = {'email': email}

    resp = client.get(f'/query/order_history', params = data)
    result = json.loads(resp.text)
    assert resp.status_code == 200, resp.content
    
    print("** Recieved from server after post:")
    _print_json(result)


def test_group_by_billing_zip(client: TestClient):
    email = "a@b.com"

    add_store(client)
    add_warehouse(client)
    item_id = add_item(client)
    customer_id = add_customer(client, email)
    customer_address_id = add_customer_address(client, customer_id)
    for i in range(5):
        order_id = add_order(client, customer_id, customer_address_id, item_id)


    resp = client.get('/query/count_billing_orders')
    result = json.loads(resp.text)
    assert resp.status_code == 200, resp.content
    
    print("** Recieved from server after post:")
    _print_json(result)


def test_group_by_shipping_zip(client: TestClient):
    email = "a@b.com"

    add_store(client)
    add_warehouse(client)
    item_id = add_item(client)
    customer_id = add_customer(client, email)
    customer_address_id = add_customer_address(client, customer_id)
    for i in range(5):
        order_id = add_order(client, customer_id, customer_address_id, item_id)


    resp = client.get('/query/count_by_shipping_zip')
    result = json.loads(resp.text)
    assert resp.status_code == 200, resp.content
    
    print("** Recieved from server after post:")
    _print_json(result)


def test_instore_shoppers(client: TestClient):
    email = "a@b.com"

    add_store(client)
    add_warehouse(client)
    item_id = add_item(client)
    customer_id = add_customer(client, email)
    customer_address_id = add_customer_address(client, customer_id)
    for i in range(5):
        order_id = add_order(client, customer_id, customer_address_id, item_id)


    resp = client.get('/query/instore_shoppers')
    result = json.loads(resp.text)
    assert resp.status_code == 200, resp.content
    
    print("** Recieved from server after post:")
    _print_json(result)