# AI-Powered Email Processing System

This application authenticates customers with JWT, verifies optional order ownership in PostgreSQL, queues email-processing work in RabbitMQ, and processes it in a separate AI worker. The worker reuses the existing ML classifier, RAG pipeline, FAISS index, and LLM service; Dockerization does not change that business logic.

## Technology stack

- FastAPI and JWT authentication
- PostgreSQL, SQLAlchemy, and Alembic
- RabbitMQ and a separate Python worker
- ML classifier, RAG, FAISS, and an external LLM provider or Ollama
- Docker and Docker Compose

## Container architecture

```text
Customer
  -> FastAPI container -> JWT authentication -> PostgreSQL container
  -> order verification -> RabbitMQ container -> worker container
  -> ML + RAG + FAISS -> LLM API -> PostgreSQL container -> final result
```

The Compose network resolves services by name: application containers connect to `postgres` and `rabbitmq`, never `localhost`.

## Prerequisites

- Docker Desktop with Docker Compose v2
- A configured LLM: an OpenAI-compatible API key, or Ollama reachable from Docker

Create the local environment file. It is ignored by Git and Docker build contexts.

```powershell
Copy-Item .env.example .env
```

Set every `replace_with_...` value in `.env`. Never commit it. Required Docker values are `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `RABBITMQ_USER`, `RABBITMQ_PASSWORD`, `JWT_SECRET_KEY`, `JWT_ALGORITHM`, `JWT_ACCESS_TOKEN_EXPIRE_MINUTES`, `LLM_MODEL`, and the applicable LLM settings.

For an API-based LLM, set `LLM_PROVIDER=openai` and `LLM_API_KEY`. For Ollama running on the Docker Desktop host, set `LLM_PROVIDER=ollama` and `LLM_BASE_URL=http://host.docker.internal:11434`; `localhost` would point at the API/worker container instead.

## Build and start

Build the shared application image:

```powershell
docker compose build
```

Start the infrastructure, apply the existing Alembic migrations, then start the API and worker:

```powershell
docker compose up -d postgres rabbitmq
docker compose run --rm api alembic upgrade head
docker compose up -d api worker
```

`docker compose up` also starts all four services. It is suitable after migrations have already been applied:

```powershell
docker compose up
docker compose up -d
```

Stop containers without removing the persistent PostgreSQL volume:

```powershell
docker compose down
```

PostgreSQL is persisted in the named `postgres_data` volume. Do not use `docker compose down -v` unless you intentionally want to delete all database data.

## Data and model assets

The Docker image copies the trained classifier from `models/` and the existing FAISS/knowledge-base assets from `data/`, including `data/vector_store/faiss.index`. They are intentionally not excluded by `.dockerignore`.

After applying migrations, load the supplied data once into an empty database:

```powershell
docker compose run --rm api python scripts/load_data_to_postgres.py
```

The loader refuses to run if application data already exists, preventing duplicate records. If you need to rebuild FAISS assets, use the project’s existing RAG scripts before building the image; Docker does not alter or rebuild the RAG implementation.

## Ports and management

- `8000`: FastAPI API at [http://localhost:8000](http://localhost:8000), with OpenAPI at `/docs`.
- `5432`: PostgreSQL, exposed for local administration.
- `5672`: RabbitMQ AMQP, exposed for local clients.
- `15672`: RabbitMQ management UI at [http://localhost:15672](http://localhost:15672), using `RABBITMQ_USER` and `RABBITMQ_PASSWORD` from `.env`.

PostgreSQL and RabbitMQ have Compose health checks. The API and worker wait for both to become healthy, and the worker restarts if its broker connection fails later. The API health endpoint is lightweight:

```powershell
Invoke-RestMethod http://localhost:8000/health
```

It returns `{"status":"healthy"}` without loading AI models or generating a response.

## API and worker

After starting Compose, the API and worker are already running as separate services. To inspect their logs:

```powershell
docker compose logs -f api
docker compose logs -f worker
```

Both email endpoints require `Authorization: Bearer <JWT>`:

```http
POST /api/v1/emails/process
Content-Type: application/json

{
  "subject": "Where is my order?",
  "email_body": "Please provide an update.",
  "order_id": "ORD00598"
}
```

The API returns a queued job immediately. Retrieve the customer-owned job at `GET /api/v1/emails/jobs/{job_id}`. The durable `email_processing_queue` holds work and `email_processing_dead_letter` holds messages that exceeded `MAX_RETRIES`.

## Testing and validation

Run unit tests locally:

```powershell
python -m unittest discover -s tests -v
```

With the containers, migrations, seed data, and LLM ready, run the complete flow:

```powershell
python scripts/test_async_processing.py
```

It logs in, submits an email, polls the job endpoint with a timeout, and prints the final status, predicted category, and response. You can also verify service state with `docker compose ps`, inspect queues in the management UI, and inspect logs with `docker compose logs -f`.