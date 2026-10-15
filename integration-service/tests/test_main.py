from datetime import datetime, timezone
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from main import app
from schemas import OrderSchema

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


class FakeSession:
    def __init__(self, order):
        self.order = order

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False

    def scalar(self, statement):
        return self.order


def test_graphql_returns_order(monkeypatch):
    order = SimpleNamespace(
        external_order_id="ORD-GRAPHQL-001",
        status="succeeded",
        currency="COP",
        created_at=datetime(2026, 10, 14, tzinfo=timezone.utc),
        updated_at=datetime(2026, 10, 14, tzinfo=timezone.utc),
    )

    monkeypatch.setattr(
        "graphql_schema.SessionLocal",
        lambda: FakeSession(order),
    )

    response = client.post(
        "/graphql",
        json={
            "query": """
                query {
                    order(externalOrderId: "ORD-GRAPHQL-001") {
                        externalOrderId
                        status
                        currency
                    }
                }
            """
        },
    )

    assert response.status_code == 200
    assert response.json()["data"]["order"] == {
        "externalOrderId": "ORD-GRAPHQL-001",
        "status": "succeeded",
        "currency": "COP",
    }


def test_graphql_returns_null_when_order_not_found(monkeypatch):
    monkeypatch.setattr(
        "graphql_schema.SessionLocal",
        lambda: FakeSession(None),
    )

    response = client.post(
        "/graphql",
        json={
            "query": """
                query {
                    order(externalOrderId: "DOES-NOT-EXIST") {
                        externalOrderId
                        status
                    }
                }
            """
        },
    )

    assert response.status_code == 200
    assert response.json()["data"]["order"] is None
