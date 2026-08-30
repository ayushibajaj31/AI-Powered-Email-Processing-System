"""Small operational checks that never initialize the ML, RAG, or LLM stack."""

from sqlalchemy import text

from src.database.database import configure_database
from src.messaging.rabbitmq_client import EMAIL_QUEUE, RabbitMQClient


def database_health():
    try:
        engine = configure_database()
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return {"status": "healthy"}
    except Exception:
        return {"status": "unavailable"}


def rabbitmq_health():
    try:
        client = RabbitMQClient()
        channel = client.connect()
        queue = channel.queue_declare(queue=EMAIL_QUEUE, passive=True)
        consumers = queue.method.consumer_count
        client.close()
        return {"status": "healthy", "worker": "connected" if consumers else "unavailable"}
    except Exception:
        return {"status": "unavailable", "worker": "unknown"}
