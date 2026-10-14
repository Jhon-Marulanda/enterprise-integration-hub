
from fastapi import Depends, FastAPI, HTTPException, status
from sqlalchemy.orm import Session

from database import get_db
from order_service import DuplicateOrderError, create_order
from schemas import OrderSchema

app = FastAPI(
    title="Enterprise Integration Hub",
    description="API for enterprise system integrations.",
    version="0.1.0",
)


@app.get("/health", tags=["Health"])
def health_check():
    return {
        "status": "ok",
        "service": "integration-service",
    }


@app.post(
    "/api/v1/orders",
    status_code=status.HTTP_202_ACCEPTED,
    tags=["Orders"],
)
def receive_order(
    order: OrderSchema,
    db: Session = Depends(get_db),
):
    try:
        saved_order = create_order(db, order)
    except DuplicateOrderError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    return {
        "message": "Order received successfully",
        "id": saved_order.id,
        "external_order_id": saved_order.external_order_id,
        "status": saved_order.status,
    }
