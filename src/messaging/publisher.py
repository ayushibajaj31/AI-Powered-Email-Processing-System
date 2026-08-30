"""Publish durable, JSON-only email-processing jobs."""

import json

from .rabbitmq_client import EMAIL_QUEUE, RabbitMQClient

class EmailJobPublisher:
    def __init__(self, client_factory=RabbitMQClient):
        self.client_factory = client_factory

    def publish(self, message, headers=None):
        import pika
        client = self.client_factory()
        try:
            channel = client.connect()
            channel.basic_publish(
                exchange="", routing_key=EMAIL_QUEUE, body=json.dumps(message),
                properties=pika.BasicProperties(delivery_mode=2, content_type="application/json", headers=headers or {}),
            )
        finally:
            client.close()
