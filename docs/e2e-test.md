# End-to-End (E2E) Test

## Objective

Validate the complete order processing flow across the Enterprise Integration Hub components, from REST API submission to GraphQL status retrieval.

## Environment

- FastAPI REST API
- PostgreSQL 17
- RabbitMQ 4
- Transactional Outbox Publisher
- Order Worker
- GraphQL endpoint

## Test Scenario

Submit an order through the REST API, persist it in PostgreSQL, publish its outbox event to RabbitMQ, process the message through the worker and legacy adapter, and retrieve the final order status through GraphQL.

## Test Data

- External order ID: `E2E-1792029101`
- Internal order ID: `57`
- Currency: `COP`
- Product code: `PROD-E2E-001`
- Quantity: `2`
- Unit price: `15000`

## Execution Results

| Step | Component | Expected result | Actual result |
|---|---|---|---|
| 1 | REST API | Accept the order with HTTP 202 | Passed |
| 2 | PostgreSQL | Persist the order and items | Passed |
| 3 | Transactional Outbox | Create an event for the order | Passed |
| 4 | Outbox Publisher | Publish the event to RabbitMQ | Passed |
| 5 | Order Worker | Process the order successfully | Passed |
| 6 | GraphQL | Return the updated order status | Passed |

## Database Verification

The order was persisted with internal ID `57` and external ID `E2E-1792029101`.

The associated outbox message had ID `28`, event type `order.created`, status `published`, and one publication attempt.

The final order status in PostgreSQL was `succeeded`.

## GraphQL Verification

Query used:

```graphql
query {
  order(externalOrderId: "E2E-1792029101") {
    externalOrderId
    status
    currency
    createdAt
    updatedAt
  }
}
```

The response returned the expected external order ID, currency `COP`, and status `succeeded`.

## Conclusion

The E2E test passed. The order was accepted through the REST API, persisted in PostgreSQL, published through the transactional outbox to RabbitMQ, processed asynchronously by the worker, and retrieved with its final status through GraphQL.

This test validates the main integration flow. It does not replace dedicated tests for retries, dead-letter handling, duplicate message delivery, or service recovery.