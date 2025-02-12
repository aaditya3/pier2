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
from functools import wraps
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

def _select_db():
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

def handle_response(id_key):
    '''
        Basic decorator to handle post errors.
    '''
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            resp = func(*args, **kwargs)
            if resp.status_code == 200:
                return json.loads(resp.text)[id_key]
            else:
                raise ValueError(f"API Error: {resp.text}")
        return wrapper
    return decorator

@handle_response("store_id")
def add_store(client):
    return client.post(f'/stores', json = {})

@handle_response("warehouse_id")
def add_warehouse(client):
    return client.post(f'/warehouses', json = {})

@handle_response("item_id")
def add_item(client):
    return client.post(f'/items', json = {})

@handle_response("customer_id")
def add_customer(client, data):
    return client.post(f'/customers', json = data)

@handle_response("customer_address_id")
def add_customer_address(client, data):
    return client.post(f'/customers/addresses', json = data)

@handle_response("order_id")
def add_order(client, order, items):
    data = {'items' : items, 'order': order}
    return client.post(f'/orders', json = data)

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
        zips = [str(x) for x in list(set(np.random.randint(10000, 100000, num_unique_zips * 10)))[0:num_unique_zips]] # ok if fewer

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
        item_ids,
        store_ids,
        warehouse_ids,
        min_items = 1,
        max_items = 10,
        min_orders = 1,
        max_orders = 20,
        min_qty = 1,
        max_qty = 10):

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
                    case FulfillmentModality.store_inventory.value:
                        d['source_store_id'] = int(np.random.choice(store_ids))
                    case FulfillmentModality.store_to_home.value:
                        d['source_store_id'] = int(np.random.choice(store_ids))
                        d['dest_customer_address_id'] = int(np.random.choice(shipping_ad_ids))
                    case FulfillmentModality.ware_to_home.value:
                        d['source_warehouse_id'] = int(np.random.choice(warehouse_ids))
                        d['dest_customer_address_id'] = int(np.random.choice(shipping_ad_ids))
                    case FulfillmentModality.ware_to_store.value:
                        d['source_warehouse_id'] = int(np.random.choice(warehouse_ids))
                        d['dest_store_id'] = int(np.random.choice(store_ids))
                    case _:
                        raise ValueError(f"Internal error. Could not match any fulfillment modality for {d['fulfillment_modality']}")
                order_items.append(d)

            orders.append(order_data)
    return pd.DataFrame(orders), pd.DataFrame(order_items)

def add_all(client, customers = None, customer_addresses = None, orders = None, order_items = None):
    if (orders is not None and order_items is None) or (orders is None and order_items is not None):
        raise ValueError("Both orders and order_items must be provided or none.")

    if customers is not None:
        for index, row in customers.iterrows():
            add_customer(client, row.to_dict())

    if customer_addresses is not None:
        for index, row in customer_addresses.iterrows():
            add_customer_address(client, row.to_dict())

    if orders is not None:
        for index, row in orders.iterrows():
            order_id = row.order_id
            order_data = row.to_dict()
            items = []
            for index, r in order_items.query(f'order_id == {order_id}').iterrows():

                item_data = r.to_dict()
                # Fix for pandas converting int's to nan's due to nulls allowed in the following
                for k in ['source_warehouse_id', 'source_store_id', 'dest_store_id', 'dest_customer_address_id']:
                    if item_data[k] is not None:
                        if math.isnan(item_data[k]):
                            item_data.pop(k)
                        else:
                            item_data[k] = int(item_data[k])
                items.append(item_data)

            add_order(client, order_data, items)

@pytest.fixture(name="session")
def session_fixture():
    which_db = _select_db()

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

    # Negative test
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
    resp = client.post(f'/customers', json = customer_data)
    assert resp.status_code == 422, resp.content
    result = json.loads(resp.text)
    print(f"** Recieved from server after post: {resp.status_code}")

    # Check bad first name
    customer_data = {
        'email': "pinkfloyd.com",
        'first_name': " ",
        'last_name': "Floyd"
    }
    resp = client.post(f'/customers', json = customer_data)
    assert resp.status_code == 422, resp.content
    result = json.loads(resp.text)
    print(f"** Recieved from server after post: {resp.status_code}")

    # Check bad last name
    customer_data = {
        'email': "pinkfloyd.com",
        'first_name': "Pink",
        'last_name': "   "
    }
    resp = client.post(f'/customers', json = customer_data)
    assert resp.status_code == 422, resp.content
    result = json.loads(resp.text)
    print(f"** Recieved from server after post: {resp.status_code}")

    # Check bad phone
    customer_data = {
        'email': "pinkfloyd.com",
        'first_name': "Pink",
        'last_name': "Floyd",
        'phone': '434324'
    }
    resp = client.post(f'/customers', json = customer_data)
    assert resp.status_code == 422, resp.content
    result = json.loads(resp.text)
    print(f"** Recieved from server after post: {resp.status_code}")

    customer_data = {
        "email": "pink@floyd.com",
        "first_name": "Pink",
        "last_name": "Floyd",
        "phone": "111-222-4444"
    }
    resp = client.post(f'/customers', json = customer_data)
    assert resp.status_code == 200, resp.content
    result = json.loads(resp.text)
    print(f"** Recieved from server after post: {resp.status_code}")

    resp = client.get(f'/customers/{result["customer_id"]}')
    assert resp.status_code == 200
    result = json.loads(resp.text)
    print(f"** Recieved from server after create: {resp.status_code}")

def test_add_customer_address(client: TestClient):
    data = {
        "email": "pink@floyd.com",
        "first_name": "Pink",
        "last_name": "Floyd",
        "phone": "111-222-4444"
    }
    customer_id = add_customer(client, data)

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
    print(f"** Recieved from server after post: {resp.status_code}")


    customer_data['is_billing'] = True
    resp = client.post(f'/customers/addresses', json = customer_data)
    assert resp.status_code == 200, resp.content
    result = json.loads(resp.text)
    print(f"** Recieved from server after post: {resp.status_code}")

    resp = client.get(f'/customers/addresses/{result['customer_address_id']}')
    assert resp.status_code == 200
    result = json.loads(resp.text)
    print(f"** Recieved from server after create: {resp.status_code}")

    # Bad state
    customer_data['state'] = "foo"
    resp = client.post(f'/customers/addresses', json = customer_data)
    assert resp.status_code == 422, resp.content
    result = json.loads(resp.text)
    print(f"** Recieved from server after post: {resp.status_code}")

def test_add_order(client: TestClient):
    store_id = add_store(client)
    warehouse_id = add_warehouse(client)
    item_id = add_item(client)

    customer_data = {
        "email": "pink@floyd.com",
        "first_name": "Pink",
        "last_name": "Floyd",
        "phone": "111-222-4444"
    }
    customer_id = add_customer(client, customer_data)

    address_data = {
        'customer_id': customer_id,
        'address_line_1': '34 Haight',
        'city': 'San Francisco',
        'state': 'CA',
        'zip_code': "94131",
        'is_billing': True,
        'is_shipping': True
    }
    customer_address_id = add_customer_address(client, address_data)

    items = [
        {'item_id': item_id,
            'fulfillment_modality': FulfillmentModality.store_to_home.value,
            'quantity': 3,
            'price_per_item': 3.2,
            'source_store_id': store_id,
            'dest_customer_address_id': customer_address_id
        }
    ]

    order_data = {
        'customer_id': customer_id,
        'time_of_order': '2025-02-09 14:14:37',
        'source': OrderSource.online.value,
        'billing_address_id': customer_address_id
    }

    resp = client.post(f'/orders', json = {'items' : items, 'order': order_data})
    assert resp.status_code == 200, resp.content
    result = json.loads(resp.text)
    print(f"** Recieved from server after post: {resp.status_code}")

    # Test make billing a non-billing address
    address_data['is_billing'] = False
    address_data['is_shipping'] = True
    customer_address_id = add_customer_address(client, address_data)
    order_data['billing_address_id'] = customer_address_id
    resp = client.post(f'/orders', json = {'items' : items, 'order': order_data})
    assert resp.status_code == 422, resp.content
    result = json.loads(resp.text)
    print(f"** Recieved from server after post: {resp.status_code}")

    # Test make shipping a non-shipping address
    address_data['is_billing'] = True
    address_data['is_shipping'] = False
    customer_address_id = add_customer_address(client, address_data)
    order_data['billing_address_id'] = customer_address_id
    for i in range(len(items)):
        if items[i]['dest_customer_address_id']:
            items[i]['dest_customer_address_id'] = customer_address_id
    resp = client.post(f'/orders', json = {'items' : items, 'order': order_data})
    assert resp.status_code == 422, resp.content
    result = json.loads(resp.text)
    print(f"** Recieved from server after post: {resp.status_code}")

    # Test fulfilment modalities
    # FIXME: Check all cases, beyond the scope of this exercise.
    items = [
        {'item_id': item_id,
            'fulfillment_modality': FulfillmentModality.store_to_home.value,
            'quantity': 3,
            'price_per_item': 3.2,
            'source_store_id': store_id,
            # 'dest_customer_address_id': customer_address_id
        }
    ]
    resp = client.post(f'/orders', json = {'items' : items, 'order': order_data})
    assert resp.status_code == 422, resp.content
    result = json.loads(resp.text)
    print(f"** Recieved from server after post: {resp.status_code}")


def test_order_history_query(client: TestClient):
    customers = get_customers_df(2)
    customer_addresses = get_customer_addresses_df(list(customers.customer_id))
    item_ids = [add_item(client) for i in range(1, 101)]
    store_ids = [add_store(client) for i in range(1, 6)]
    warehouse_ids = [add_warehouse(client) for i in range(1, 6)]
    orders, order_items = get_orders_df(customers, customer_addresses, item_ids, store_ids, warehouse_ids)

    add_all(client, customers, customer_addresses, orders, order_items)

    for index, row in customers.iterrows():
        data = {'email': row['email']}
        customer_id = row['customer_id']
        resp = client.get(f'/query/order_history', params = data)
        result = json.loads(resp.text)
        assert resp.status_code == 200, resp.content

        # check against pandas result
        pandas_orders = set(orders.merge(customers.query(f'customer_id == {customer_id}'))['order_id'])
        response_orders = set(pd.DataFrame(result)['order_id'])
        assert pandas_orders == response_orders, f"Pandas result: {pandas_orders}, response result: {response_orders}"

def test_group_by_billing_zip(client: TestClient, session: Session):
    customers = get_customers_df(3)
    customer_addresses = get_customer_addresses_df(list(customers.customer_id))
    item_ids = [add_item(client) for i in range(1, 101)]
    store_ids = [add_store(client) for i in range(1, 6)]
    warehouse_ids = [add_warehouse(client) for i in range(1, 6)]
    orders, order_items = get_orders_df(customers, customer_addresses, item_ids, store_ids, warehouse_ids)

    assert(len(orders) > 0)
    assert(len(customers) > 0)
    assert(len(order_items) > 0)
    add_all(client, customers, customer_addresses, orders, order_items)

    resp = client.get(f'/query/count_billing_orders')
    result = json.loads(resp.text)
    assert resp.status_code == 200, resp.content

    # check against pandas result
    all_orders = pd.read_sql( "SELECT * FROM orders", session.bind)
    assert(len(all_orders) > 0)
    all_customer_addresses = pd.read_sql( "SELECT * FROM customer_addresses", session.bind)
    assert(len(all_customer_addresses) > 0)
    pandas_result = all_orders.merge(all_customer_addresses,
                                     left_on = 'billing_address_id',
                                     right_on = 'customer_address_id').groupby(
                                         'zip_code').size()
    assert pandas_result.to_dict() == result

def test_group_by_shipping_zip(client: TestClient, session: Session):
    customers = get_customers_df(3)
    customer_addresses = get_customer_addresses_df(list(customers.customer_id))
    item_ids = [add_item(client) for i in range(1, 101)]
    store_ids = [add_store(client) for i in range(1, 6)]
    warehouse_ids = [add_warehouse(client) for i in range(1, 6)]
    orders, order_items = get_orders_df(customers, customer_addresses, item_ids, store_ids, warehouse_ids)

    add_all(client, customers, customer_addresses, orders, order_items)

    # many rows already added, wont be adding more here.
    resp = client.get(f'/query/count_by_shipping_zip')
    result = json.loads(resp.text)
    assert resp.status_code == 200, resp.content

    # check against pandas result
    customer_addresses = pd.read_sql( "SELECT * FROM customer_addresses", session.bind)

    order_items_shipped_home = pd.read_sql(
        "SELECT * FROM order_items",
        session.bind)
    pandas_result = order_items_shipped_home.merge(customer_addresses,
                                   left_on = 'dest_customer_address_id',
                                   right_on = 'customer_address_id').groupby('zip_code')['order_id'].nunique()
    assert pandas_result.to_dict() == result

def test_instore_shoppers(client: TestClient, session: Session):
    customers = get_customers_df(10)
    customer_addresses = get_customer_addresses_df(list(customers.customer_id))
    item_ids = [add_item(client) for i in range(1, 101)]
    store_ids = [add_store(client) for i in range(1, 6)]
    warehouse_ids = [add_warehouse(client) for i in range(1, 6)]
    orders, order_items = get_orders_df(customers, customer_addresses, item_ids, store_ids, warehouse_ids)

    add_all(client, customers, customer_addresses, orders, order_items)

    # many rows already added, wont be adding more here.
    resp = client.get(f'/query/instore_shoppers')
    result = json.loads(resp.text)
    assert resp.status_code == 200, resp.content

    # check against pandas result
    orders = pd.read_sql( "SELECT * FROM orders", session.bind)
    pandas_result = orders[orders['source'] == 'store'].groupby('customer_id').size().reset_index(
        name = "count").sort_values("count", ascending=False).head(5)

    assert {str(row['customer_id']): int(row['count']) for _, row in pandas_result.iterrows()} == result
