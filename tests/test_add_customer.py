import requests
import json
import yaml
import os
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlmodel.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from pier2.database import get_db
from pier2.models import Base
from pier2.routers import customers
from pier2.main import app


@pytest.fixture(name="session")
def session_fixture():
    engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass = StaticPool
    )
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

    resp = client.get(f'/customers/1')
    assert resp.status_code == 404

    resp = client.post(f'/customers', json = {'email': "pink@floyd.com"})
    assert resp.status_code == 422
    result = json.loads(resp.text)
    print(f"** Recieved from server after post: {result}")

    customer_data = {
        'email': "pinkfloyd.com",
        'first_name': "Pink",
        'last_name': "Floyd"
    }
    resp = client.post(f'/customers', json = customer_data)
    assert resp.status_code == 422, resp.content
    result = json.loads(resp.text)
    print(f"** Recieved from server after post: {result}")

    customer_data = {
        'email': "pink@floyd.com",
        'first_name': "Pink",
        'last_name': "Floyd"
    }
    resp = client.post(f'/customers', json = customer_data)
    assert resp.status_code == 200, resp.content
    result = json.loads(resp.text)
    print(f"** Recieved from server after post: {result}")

    resp = client.get(f'/customers/{result['customer_id']}')
    assert resp.status_code == 200
    result = json.loads(resp.text)
    print(f"** Recieved from server after create: {result}")



