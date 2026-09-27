# Invoice Payment Dashboard API

A practical **Python + FastAPI** backend for customers, invoices, payments, balances, overdue tracking, and financial dashboard metrics.

## Features

- Customer management
- Invoice creation and unique invoice numbers
- Invoice status tracking
- Partial and full payments
- Automatic paid/overdue status updates
- Invoice balance calculation
- Payment history
- Outstanding and overdue amounts
- Collection-rate calculation
- Financial dashboard
- Email and input validation
- Swagger documentation
- Automated tests
- Vercel-ready configuration

## Python skills demonstrated

Python backend development, FastAPI REST APIs, Pydantic validation, Python enums, Decimal money calculations, date/datetime handling, business-rule validation, REST design, financial aggregation, and automated API testing.

## API endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| GET | / | API information |
| GET | /health | Health check |
| POST | /customers | Create customer |
| GET | /customers | List customers |
| POST | /invoices | Create invoice |
| GET | /invoices | List/filter invoices |
| GET | /invoices/{id} | Get invoice |
| POST | /payments | Record payment |
| GET | /payments | Payment history |
| GET | /invoices/{id}/balance | Invoice balance |
| GET | /dashboard | Financial dashboard |

## Run locally

pip install -r requirements.txt
uvicorn api.index:app --reload
pytest

Swagger: http://127.0.0.1:8000/docs

## Production note

This portfolio version uses in-memory storage. For real billing software, use PostgreSQL/Supabase plus authentication, authorization, audit logs, and a payment provider.
