import requests
import json

# FIXME: Need to pick this up from config file.
SERVER_URL = "http://127.0.0.1:8000"

# FIXME: need DB setup and teardown here.
def test_add_customer():

    # FIXME: Assumes empty db. Once all tests are written may need fix.
    resp = requests.get(f'{SERVER_URL}/customers/1')
    assert not resp.ok 
    assert resp.status_code == 404

    resp = requests.post(f'{SERVER_URL}/customers', json = {'email': "pink@floyd.com"})
    assert resp.ok 
    assert resp.status_code == 200
    result = json.loads(resp.text)
    print(f"Recieved from server after post: {result}")

    resp = requests.get(f'{SERVER_URL}/customers/{result['customer_id']}')
    assert resp.ok
    assert resp.status_code == 200
    result = json.loads(resp.text)
    print(f"Recieved from server after creagette: {result}")



