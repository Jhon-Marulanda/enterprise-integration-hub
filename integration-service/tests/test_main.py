from fastapi.testclient import TestClient

from main import app
from decimal import Decimal

import pytest
from pydantic import ValidationError
from schemas import OrderSchema
from uuid import uuid4

client = TestClient(app)


def test_health_returns_200():
    response = client.get("/health")

    assert response.status_code == 200


def test_health_returns_expected_data():
    response = client.get("/health")

    assert response.json() == {
        "status": "ok",
        "service": "integration-service",
    }

def test_order_schema_accepts_valid_order():
    order = OrderSchema(
        external_order_id="ORD-1001",
        customer={
            "document_number": "1020304050",
            "name": "Ana Martinez",
            "email": "ana@example.com",
        },
        items=[
            {
                "product_code": "PROD-001",
                "quantity": 2,
                "unit_price": "45000.00",
            }
        ],
        currency="COP",
    )

    assert order.external_order_id == "ORD-1001"
    assert order.items[0].quantity == 2
    assert order.items[0].unit_price == Decimal("45000.00")


def test_order_schema_rejects_zero_quantity():
    with pytest.raises(ValidationError):
        OrderSchema(
            external_order_id="ORD-1002",
            customer={
                "document_number": "1020304050",
                "name": "Ana Martinez",
                "email": "ana@example.com",
            },
            items=[
                {
                    "product_code": "PROD-001",
                    "quantity": 0,
                    "unit_price": "45000.00",
                }
            ],
            currency="COP",
        )

def test_receive_order_returns_202():
    payload = {
        "external_order_id": f"ORD-{uuid4().hex[:12]}",
        "customer": {
            "document_number": "1020304050",
            "name": "Ana Martinez",
            "email": "ana@example.com",
        },
        "items": [
            {
                "product_code": "PROD-001",
                "quantity": 2,
                "unit_price": "45000.00",
            }
        ],
        "currency": "COP",
    }

    response = client.post("/api/v1/orders", json=payload)

    assert response.status_code == 202
    assert response.json()["external_order_id"] == payload["external_order_id"]
    assert response.json()["status"] == "pending"


def test_receive_order_rejects_invalid_quantity():
    payload = {
        "external_order_id": "ORD-1002",
        "customer": {
            "document_number": "1020304050",
            "name": "Ana Martinez",
            "email": "ana@example.com",
        },
        "items": [
            {
                "product_code": "PROD-001",
                "quantity": 0,
                "unit_price": "45000.00",
            }
        ],
        "currency": "COP",
    }

    response = client.post("/api/v1/orders", json=payload)

    assert response.status_code == 422

def test_duplicate_order_returns_409():
    payload = {
        "external_order_id": f"ORD-DUP-{uuid4().hex[:12]}",
        "customer": {
            "document_number": "1020304050",
            "name": "Ana Martinez",
            "email": "ana@example.com",
        },
        "items": [
            {
                "product_code": "PROD-001",
                "quantity": 2,
                "unit_price": "45000.00",
            }
        ],
        "currency": "COP",
    }

    first_response = client.post("/api/v1/orders", json=payload)
    second_response = client.post("/api/v1/orders", json=payload)

    assert first_response.status_code == 202
    assert second_response.status_code == 409
    assert second_response.json()["detail"] == (
        "An order with this external ID already exists."
    )
