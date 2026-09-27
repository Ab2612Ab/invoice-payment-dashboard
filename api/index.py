from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Optional
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict, EmailStr, Field

app = FastAPI(title="Invoice Payment Dashboard API", version="1.0.0")

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=False, allow_methods=["*"], allow_headers=["*"])

class InvoiceStatus(str, Enum):
    draft = "draft"
    sent = "sent"
    paid = "paid"
    overdue = "overdue"
    cancelled = "cancelled"

class CustomerCreate(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    email: EmailStr
    company: Optional[str] = Field(default=None, max_length=160)

class InvoiceCreate(BaseModel):
    customer_id: str
    invoice_number: str = Field(min_length=1, max_length=50)
    description: str = Field(min_length=1, max_length=500)
    amount: Decimal = Field(gt=0, decimal_places=2)
    due_date: date
    status: InvoiceStatus = InvoiceStatus.sent

class PaymentCreate(BaseModel):
    invoice_id: str
    amount: Decimal = Field(gt=0, decimal_places=2)
    payment_date: date = Field(default_factory=date.today)
    reference: Optional[str] = Field(default=None, max_length=100)

class Customer(CustomerCreate):
    model_config = ConfigDict(from_attributes=True)
    id: str
    created_at: datetime

class Invoice(InvoiceCreate):
    model_config = ConfigDict(from_attributes=True)
    id: str
    created_at: datetime
    updated_at: datetime

class Payment(PaymentCreate):
    model_config = ConfigDict(from_attributes=True)
    id: str
    created_at: datetime

customers: dict[str, Customer] = {}
invoices: dict[str, Invoice] = {}
payments: dict[str, Payment] = {}

def money(value: Decimal) -> float:
    return float(value.quantize(Decimal("0.01")))

def paid_for_invoice(invoice_id: str) -> Decimal:
    return sum((p.amount for p in payments.values() if p.invoice_id == invoice_id), Decimal("0"))

def refresh_invoice_status(invoice: Invoice) -> Invoice:
    if invoice.status not in (InvoiceStatus.cancelled, InvoiceStatus.draft):
        paid = paid_for_invoice(invoice.id)
        if paid >= invoice.amount:
            invoice.status = InvoiceStatus.paid
        elif invoice.due_date < date.today():
            invoice.status = InvoiceStatus.overdue
        elif invoice.status == InvoiceStatus.overdue:
            invoice.status = InvoiceStatus.sent
    return invoice

@app.get("/")
def root():
    return {"name": "Invoice Payment Dashboard API", "version": "1.0.0", "docs": "/docs", "health": "/health"}

@app.get("/health")
def health():
    return {"status": "ok", "customers": len(customers), "invoices": len(invoices), "payments": len(payments)}

@app.post("/customers", response_model=Customer, status_code=201)
def create_customer(payload: CustomerCreate):
    now = datetime.utcnow()
    customer = Customer(id=str(uuid4()), created_at=now, **payload.model_dump())
    customers[customer.id] = customer
    return customer

@app.get("/customers", response_model=list[Customer])
def list_customers():
    return list(customers.values())

@app.post("/invoices", response_model=Invoice, status_code=201)
def create_invoice(payload: InvoiceCreate):
    if payload.customer_id not in customers:
        raise HTTPException(status_code=404, detail="Customer not found")
    if any(i.invoice_number == payload.invoice_number for i in invoices.values()):
        raise HTTPException(status_code=409, detail="Invoice number already exists")
    now = datetime.utcnow()
    invoice = Invoice(id=str(uuid4()), created_at=now, updated_at=now, **payload.model_dump())
    invoices[invoice.id] = invoice
    return invoice

@app.get("/invoices", response_model=list[Invoice])
def list_invoices(status: Optional[InvoiceStatus] = None, customer_id: Optional[str] = Query(default=None)):
    results = []
    for invoice in invoices.values():
        refresh_invoice_status(invoice)
        if status and invoice.status != status:
            continue
        if customer_id and invoice.customer_id != customer_id:
            continue
        results.append(invoice)
    return sorted(results, key=lambda i: i.due_date)

@app.get("/invoices/{invoice_id}", response_model=Invoice)
def get_invoice(invoice_id: str):
    invoice = invoices.get(invoice_id)
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return refresh_invoice_status(invoice)

@app.post("/payments", response_model=Payment, status_code=201)
def record_payment(payload: PaymentCreate):
    invoice = invoices.get(payload.invoice_id)
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    refresh_invoice_status(invoice)
    if invoice.status == InvoiceStatus.cancelled:
        raise HTTPException(status_code=400, detail="Cannot pay a cancelled invoice")
    remaining = invoice.amount - paid_for_invoice(invoice.id)
    if payload.amount > remaining:
        raise HTTPException(status_code=422, detail=f"Payment exceeds remaining balance of {money(remaining):.2f}")
    payment = Payment(id=str(uuid4()), created_at=datetime.utcnow(), **payload.model_dump())
    payments[payment.id] = payment
    refresh_invoice_status(invoice)
    invoice.updated_at = datetime.utcnow()
    return payment

@app.get("/invoices/{invoice_id}/balance")
def invoice_balance(invoice_id: str):
    invoice = invoices.get(invoice_id)
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    paid = paid_for_invoice(invoice_id)
    remaining = max(invoice.amount - paid, Decimal("0"))
    refresh_invoice_status(invoice)
    return {"invoice_id": invoice_id, "invoice_amount": money(invoice.amount), "paid": money(paid), "remaining": money(remaining), "status": invoice.status}

@app.get("/payments", response_model=list[Payment])
def list_payments():
    return sorted(payments.values(), key=lambda p: p.payment_date, reverse=True)

@app.get("/dashboard")
def dashboard():
    total_invoiced = Decimal("0")
    total_paid = Decimal("0")
    outstanding = Decimal("0")
    overdue = Decimal("0")
    status_counts = {status.value: 0 for status in InvoiceStatus}
    for invoice in invoices.values():
        refresh_invoice_status(invoice)
        paid = paid_for_invoice(invoice.id)
        balance = max(invoice.amount - paid, Decimal("0"))
        total_invoiced += invoice.amount
        total_paid += paid
        outstanding += balance
        if invoice.status == InvoiceStatus.overdue:
            overdue += balance
        status_counts[invoice.status.value] += 1
    collection_rate = money((total_paid / total_invoiced) * Decimal("100")) if total_invoiced else 0
    return {"total_invoices": len(invoices), "total_invoiced": money(total_invoiced), "total_paid": money(total_paid), "outstanding": money(outstanding), "overdue": money(overdue), "collection_rate_percent": collection_rate, "by_status": status_counts}
