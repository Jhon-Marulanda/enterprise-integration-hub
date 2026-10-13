# Enterprise Integration Hub

## 1. Objective

Build an integration platform that connects a sales system
with a legacy SOAP service through REST APIs and asynchronous
message processing.

## 2. Architecture components

- Sales System: Laravel application that submits orders.
- Integration Service: Python application built with FastAPI.
- REST API: receives and validates integration requests.
- GraphQL API: queries orders and their integration status.
- RabbitMQ: transports messages asynchronously.
- Legacy Adapter: transforms data and calls a SOAP service.
- PostgreSQL: stores orders, processing status, and traceability.

## 3. Order processing flow

1. Laravel submits an order through REST.
2. FastAPI validates the request.
3. The integration service stores the order in PostgreSQL.
4. A message is published to RabbitMQ.
5. A consumer processes the message.
6. The legacy adapter transforms the data and calls SOAP.
7. PostgreSQL records the processing result.
8. GraphQL allows clients to query the order status.

## 4. Reliability requirements

- Validate incoming data.
- Avoid duplicate processing through idempotency.
- Retry transient failures.
- Send repeatedly failing messages to a dead-letter queue.
- Track each integration using a correlation ID.
- Keep credentials and secrets outside source code.

## 5. Development environment

- Ubuntu on WSL2
- Docker and Docker Compose
- Python and FastAPI
- PHP and Laravel
- PostgreSQL
- RabbitMQ
- Git

## 6. Initial scope

Start with a minimal FastAPI service and verify its health endpoint.
Add persistence, messaging, SOAP integration, GraphQL, testing,
and CI/CD incrementally.
