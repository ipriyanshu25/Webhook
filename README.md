# Webhook Delivery Service

A robust backend system that functions as a reliable webhook delivery service. This service ingests incoming webhooks, queues them, and attempts delivery to subscribed target URLs, handling failures with retries and providing visibility into the delivery status.

## Features

- **Subscription Management**: Create, read, update, and delete webhook subscriptions
- **Webhook Ingestion**: Accept and queue incoming webhook payloads for asynchronous processing
- **Asynchronous Delivery**: Process webhook deliveries in the background
- **Retry Mechanism**: Automatically retry failed deliveries with exponential backoff
- **Delivery Logging**: Comprehensive logging of all delivery attempts
- **Log Retention**: Automatic cleanup of old delivery logs based on retention period
- **Status/Analytics**: API endpoints to retrieve delivery status and history
- **Caching**: Redis-based caching to optimize performance
- **Payload Signature Verification**: Verify webhook signatures for security
- **Event Type Filtering**: Filter webhooks based on event types

## Architecture

### Technology Stack

- **Language**: Python 3.9+
- **Web Framework**: Flask
- **Database**: PostgreSQL
- **Asynchronous Tasks**: Celery with Redis as broker
- **Caching**: Redis
- **Containerization**: Docker and Docker Compose

### Component Overview

- **API Layer**: Flask application providing RESTful API endpoints
- **Database Layer**: PostgreSQL storing subscriptions, webhooks, and delivery logs
- **Worker Layer**: Celery workers processing webhook deliveries and retries
- **Cache Layer**: Redis for caching and acting as message broker

### Database Schema

#### Subscriptions Table
- `id`: UUID, primary key
- `name`: String, name of the subscription
- `target_url`: String, URL where webhooks will be delivered
- `secret_key`: String (optional), used for signature verification
- `event_types`: String (optional), comma-separated list of event types
- `created_at`: DateTime, when the subscription was created
- `updated_at`: DateTime, when the subscription was last updated
- `active`: Boolean, whether the subscription is active

#### Webhooks Table
- `id`: UUID, primary key
- `subscription_id`: UUID, foreign key to subscriptions
- `payload`: JSON, the webhook payload
- `event_type`: String (optional), type of event
- `status`: String, current status of webhook (queued, processing, completed, failed)
- `created_at`: DateTime, when the webhook was created
- `updated_at`: DateTime, when the webhook was last updated

#### Delivery Logs Table
- `id`: UUID, primary key
- `webhook_id`: UUID, foreign key to webhooks
- `attempt_number`: Integer, which attempt this was
- `status`: String, outcome of the attempt (success, failed_attempt, failure)
- `timestamp`: DateTime, when the attempt occurred
- `http_status`: Integer (optional), HTTP status code received
- `error_details`: Text (optional), error message if applicable
- `response_time`: Float (optional), time taken for the request in seconds

### Indexing Strategy

- Index on `webhooks.subscription_id` for quick lookup of webhooks by subscription
- Index on `delivery_logs.webhook_id` for quick lookup of logs by webhook
- Index on `delivery_logs.timestamp` for efficient cleanup of old logs
- Composite index on `delivery_logs.webhook_id` and `delivery_logs.attempt_number` for ordering logs

### Retry Strategy

The service implements an exponential backoff retry strategy:
- Initial delivery attempt happens immediately upon webhook ingestion
- Subsequent retries occur with increasing delays: 10s, 30s, 1m, 5m, 15m
- Maximum of 5 retry attempts before marking delivery as permanently failed

### Caching Strategy

Redis is used for caching to optimize performance:
- Subscription details cached by ID to reduce database lookups
- Active webhooks cached during processing to reduce contention
- Cache invalidation on subscription updates

## Setup Instructions

### Prerequisites

- Docker and Docker Compose installed
- Git (for cloning the repository)

### Running Locally

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/webhook-delivery-service.git
   cd webhook-delivery-service
   ```

2. Start the application using Docker Compose:
   ```bash
   docker-compose up -d
   ```

3. Access the web UI at: http://localhost:5000

4. To stop the application:
   ```bash
   docker-compose down
   ```

### Deployed Application

The application is deployed and available at the following URL:
[https://webhook-service.example.com](https://webhook-service.example.com)

## API Documentation

### Subscription Management

#### Create a Subscription
```
POST /api/subscriptions
```
Request body:
```json
{
  "name": "My Webhook Subscription",
  "target_url": "https://my-service.com/webhook-receiver",
  "secret_key": "optional_secret_for_verification",
  "event_types": "order.created,user.updated"
}
```

#### Get All Subscriptions
```
GET /api/subscriptions
```

#### Get a Specific Subscription
```
GET /api/subscriptions/{subscription_id}
```

#### Update a Subscription
```
PUT /api/subscriptions/{subscription_id}
```
Request body:
```json
{
  "name": "Updated Name",
  "target_url": "https://new-url.com/webhook"
}
```

#### Delete a Subscription
```
DELETE /api/subscriptions/{subscription_id}
```

### Webhook Management

#### Ingest a Webhook
```
POST /api/webhooks/ingest/{subscription_id}
```
Headers (optional):
```
X-Hub-Signature-256: sha256=computed_signature_here
X-Event-Type: order.created
```
Request body (any valid JSON):
```json
{
  "event": "order.created",
  "data": {
    "order_id": "12345",
    "customer": "John Doe",
    "amount": 99.99
  }
}
```

#### Get Webhook Status
```
GET /api/webhooks/{webhook_id}
```

#### List Webhooks for a Subscription
```
GET /api/webhooks/subscription/{subscription_id}
```

### Delivery Logs

#### Get Delivery Logs for a Webhook
```
GET /api/logs/webhook/{webhook_id}
```

#### Get Recent Delivery Logs for a Subscription
```
GET /api/logs/subscription/{subscription_id}
```

## Architecture Decisions

### Framework Choice: Flask

Flask was chosen for its lightweight nature and flexibility. It provides just enough structure while allowing the freedom to organize the application as needed. Combined with SQLAlchemy, it offers a powerful foundation for building a robust API.

### Database Choice: PostgreSQL

PostgreSQL was selected for its:
- JSON support (for storing webhook payloads)
- Reliability and ACID compliance
- Strong indexing capabilities
- Support for complex queries
- Good performance with high write loads

### Asynchronous Tasks: Celery with Redis

Celery with Redis broker was chosen for handling asynchronous tasks because:
- It provides reliable message delivery
- Supports task retries with customizable backoff
- Offers monitoring and inspection tools
- Scales horizontally by adding more workers
- Redis as a broker is fast, reliable, and has low overhead

### Containerization: Docker and Docker Compose

Docker was chosen for:
- Consistent environment across development and production
- Easy setup for new developers
- Simplified deployment process
- Isolation of components
- Resource management

## Cost Estimation

For running on a free tier with moderate traffic (5000 webhooks/day, average 1.2 delivery attempts per webhook):

| Component | Service | Free Tier Limits | Monthly Cost |
|-----------|---------|------------------|--------------|
| API Server | Render Web Service | 750 hours free | $0 |
| Worker | Render Web Service | Shared with API | $0 |
| Database | Render PostgreSQL | 1GB storage, limited connections | $0 |
| Redis | Redis Labs | 30MB free tier | $0 |
| **Total** | | | **$0** |

For a production environment, estimated monthly cost would be approximately $50-100 depending on traffic volume.

## Assumptions

- Webhook payloads are reasonably sized (< 1MB)
- Target endpoints respond within a reasonable timeframe (< 10 seconds)
- Free tier resources are sufficient for the specified traffic
- All components can run in a single region to minimize latency

## Credits

- Flask: Web framework (https://flask.palletsprojects.com/)
- SQLAlchemy: ORM (https://www.sqlalchemy.org/)
- Celery: Task queue (https://docs.celeryproject.org/)
- Redis: Caching and message broker (https://redis.io/)
- PostgreSQL: Database (https://www.postgresql.org/)
- Docker: Containerization (https://www.docker.com/)
- Swagger/OpenAPI: API documentation (https://swagger.io/)webhook_id` for quick lookup of logs by webhook
- Index on `delivery_logs.