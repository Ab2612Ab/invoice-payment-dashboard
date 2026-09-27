from fastapi.testclient import TestClient
from api.index import customers, invoices, payments, app

client = TestClient(app)

def setup_function():
    customers.clear()
    invoices.clear()
    payments.clear()

def test_invoice_payment_flow():
    customer = client.post("/customers", json={"name":"Acme Studio","email":"billing@acme.example"})
    assert customer.status_code == 201
    cid = customer.json()["id"]
    invoice = client.post("/invoices", json={"customer_id":cid,"invoice_number":"INV-1001","description":"Website development","amount":"1500.00","due_date":"2099-12-31"})
    assert invoice.status_code == 201
    iid = invoice.json()["id"]
    payment = client.post("/payments", json={"invoice_id":iid,"amount":"500.00","reference":"PAY-001"})
    assert payment.status_code == 201
    balance = client.get(f"/invoices/{iid}/balance")
    assert balance.json()["remaining"] == 1000.0

def test_full_payment_marks_paid():
    customer = client.post("/customers", json={"name":"Client One","email":"client@example.com"})
    cid = customer.json()["id"]
    invoice = client.post("/invoices", json={"customer_id":cid,"invoice_number":"INV-2001","description":"Landing page","amount":"800.00","due_date":"2099-12-31"})
    iid = invoice.json()["id"]
    assert client.post("/payments", json={"invoice_id":iid,"amount":"800.00"}).status_code == 201
    assert client.get(f"/invoices/{iid}").json()["status"] == "paid"

def test_payment_cannot_exceed_balance():
    customer = client.post("/customers", json={"name":"Client Two","email":"two@example.com"})
    cid = customer.json()["id"]
    invoice = client.post("/invoices", json={"customer_id":cid,"invoice_number":"INV-3001","description":"API work","amount":"300.00","due_date":"2099-12-31"})
    response = client.post("/payments", json={"invoice_id":invoice.json()["id"],"amount":"301.00"})
    assert response.status_code == 422

def test_dashboard():
    customer = client.post("/customers", json={"name":"Dashboard Client","email":"dash@example.com"})
    cid = customer.json()["id"]
    client.post("/invoices", json={"customer_id":cid,"invoice_number":"INV-4001","description":"Project","amount":"1000.00","due_date":"2099-12-31"})
    dashboard = client.get("/dashboard")
    assert dashboard.status_code == 200
    assert dashboard.json()["total_invoices"] == 1
    assert dashboard.json()["total_invoiced"] == 1000.0
