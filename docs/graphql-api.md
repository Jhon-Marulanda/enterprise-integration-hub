# GraphQL API

## Overview

The Enterprise Integration Hub exposes a GraphQL endpoint through the FastAPI application.

- **Endpoint:** `/graphql`
- **Method:** `POST`
- **Content-Type:** `application/json`
- **Interactive interface:** Open `/graphql` in a browser to access GraphiQL.

GraphQL allows clients to request specific order fields without retrieving the entire order object.

## Available Query

### Retrieve an order

The `order` query retrieves an order using its external identifier.

**Query example:**

```graphql
query {
  order(externalOrderId: "ORD-OUTBOX-CLAIM-001") {
    externalOrderId
    status
    currency
    createdAt
    updatedAt
  }
}
```

**Available fields:**

| Field | Description |
|---|---|
| `externalOrderId` | External identifier assigned to the order |
| `status` | Current order status |
| `currency` | Currency used by the order |
| `createdAt` | Date and time when the order was created |
| `updatedAt` | Date and time when the order was last updated |

GraphQL exposes these fields using camelCase naming, even though the underlying Python model uses snake_case.

## HTTP Request Example

```bash
curl -X POST http://localhost:8000/graphql \
  -H 'Content-Type: application/json' \
  -d '{"query":"query { order(externalOrderId: \"ORD-OUTBOX-CLAIM-001\") { externalOrderId status currency } }"}'
```

## Successful Response

When the order exists, the response contains the requested fields.

```json
{
  "data": {
    "order": {
      "externalOrderId": "ORD-OUTBOX-CLAIM-001",
      "status": "succeeded",
      "currency": "COP"
    }
  }
}
```

The values above are an example based on a test order. Actual results depend on the data stored in PostgreSQL.

## Order Not Found

If no order matches the supplied external identifier, the query returns `null`.

```json
{
  "data": {
    "order": null
  }
}
```

This is a valid GraphQL response, not an application error.

## Current Limitations

- The API currently supports querying a single order by its external identifier.
- The API does not expose mutations for creating or updating orders; order creation remains available through the REST endpoint.
- Authentication and authorization for GraphQL have not yet been implemented.
- The query returns order metadata only and does not expose customer details or order items.
