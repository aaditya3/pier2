import requests
import json
import yaml
import os
import pytest
from datetime import datetime
import numpy as np
import math
import pandas as pd
import random
import copy
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

def _random_datetime(lookback_years = 2):
    current_year = datetime.now().year
    start_date = datetime(current_year - lookback_years, 1, 1)
    end_date = datetime(current_year, 12, 31, 23, 59, 59)

    random_timestamp = random.randint(int(start_date.timestamp()), int(end_date.timestamp()))
    random_datetime = datetime.fromtimestamp(random_timestamp)

    return random_datetime

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

def get_customers_df(count):

    email_ids = None

    while True:
        email_ids = list(set(np.random.randint(0, count * 100, count * 10)))
        if len(email_ids) >= count:
            email_ids = email_ids[0:count]
            break

    return pd.DataFrame([{
        'customer_id': i + 1,
        'email': f'{email_ids[i]}@piertwo.com',
        'first_name': "Pink",
        'last_name': "Floyd"
    } for i in range(len(email_ids))])

def get_customer_addresses_df(customer_ids, min_addresses = 1, max_addresses = 8):

    customer_data = {
                'address_line_1': '34 Haight',
                'city': 'San Francisco',
                'state': 'CA'
            }

    data = []
    for cid in customer_ids:
        num_addresses = np.random.randint(1, max_addresses + 1)
        num_unique_zips = round(math.log(num_addresses + 1, 2))
        zips = list(set(np.random.randint(10000, 100000, num_unique_zips * 10)))[0:num_unique_zips] # ok if fewer

        cd = copy.deepcopy(customer_data)
        cd['customer_address_id'] = len(data) + 1
        cd['customer_id'] = cid
        cd['zip_code'] = np.random.choice(zips)
        cd['is_billing'] = True
        cd['is_shipping'] = True
        data.append(cd)


        for i in range(num_addresses - 1):

            cd = copy.deepcopy(customer_data)
            cd['customer_address_id'] = len(data) + 1
            cd['customer_id'] = cid
            cd['zip_code'] = np.random.choice(zips)
            cd['is_billing'] = (np.random.randint(0,2) == 1)
            cd['is_shipping'] = (np.random.randint(0,2) == 1) if cd['is_billing'] else True
            data.append(cd)

    return pd.DataFrame(data)

def get_orders_df(
        customers_df,
        customer_addresses_df,
        min_items = 1,
        max_items = 10,
        min_orders = 1,
        max_orders = 20,
        min_qty = 1,
        max_qty = 10):

    item_ids = list(range(1, max_items * 10))
    store_ids = list(range(1, 6))
    warehouse_ids = list(range(1, 6))

    merged = customers_df.merge(customer_addresses_df, on = 'customer_id')
    orders = []
    order_items = []

    for cid in customer_addresses_df['customer_id']:

        billing_ad_ids = list(merged.query(f'`is_billing` == True and `customer_id` == {cid}')['customer_address_id'])
        shipping_ad_ids = list(merged.query(f'`is_shipping` == True and `customer_id` == {cid}')['customer_address_id'])
        assert len(billing_ad_ids)
        assert len(shipping_ad_ids)

        num_orders = np.random.randint(min_orders, max_orders + 1)
        for i in range(num_orders):
            order_data = {
                    'order_id': len(orders) + 1,
                    'customer_id': cid,
                    'time_of_order': _random_datetime().strftime("%Y-%m-%d %H:%M:%S"),
                    'source': random.choice(list(OrderSource)).value,
                    'billing_address_id': random.choice(billing_ad_ids)
                }

            num_items = np.random.randint(min_items, max_items + 1)
            random.shuffle(item_ids)
            this_orders_items = item_ids[0:num_items]
            for item in this_orders_items:
                d = {
                        'order_item_id': len(order_items) + 1,
                        'order_id': len(orders) + 1,
                        'item_id': item,
                        'fulfillment_modality': random.choice(list(FulfillmentModality)).value,
                        'quantity': np.random.randint(1, 5),
                        'price_per_item': float((np.random.rand() + 0.1) * 100)
                    }

                match d['fulfillment_modality']:
                    case FulfillmentModality.store_inventory:
                        d['source_store_id']: int(np.random.choice(store_ids))
                    case FulfillmentModality.store_to_home:
                        d['source_store_id']: int(np.random.choice(store_ids))
                        d['dest_customer_address_id']: int(np.random.choice(shipping_ad_ids))
                    case FulfillmentModality.ware_to_home:
                        d['source_warehouse_id']: int(np.random.choice(warehouse_ids))
                        d['dest_customer_address_id']: int(np.random.choice(shipping_ad_ids))
                    case FulfillmentModality.ware_to_store:
                        d['source_warehouse_id']: int(np.random.choice(warehouse_ids))
                        d['dest_store_id']: int(np.random.choice(store_ids))
                order_items.append(d)

            orders.append(order_data)

    return pd.DataFrame(orders), pd.DataFrame(order_items)

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

def test_neg_create_order_non_shipping_address():
    # FIXME
    pass

def test_neg_create_order_non_billing_address():
    # FIXME
    pass

def test_neg_create_order_non_billing_address():
    # FIXME
    pass


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