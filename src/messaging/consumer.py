"""Generic RabbitMQ consumer with bounded retry and dead-letter publishing."""

import json
import os

from .rabbitmq_client import DEAD_LETTER_QUEUE, EMAIL_QUEUE, RabbitMQClient

class EmailJobConsumer:
    def __init__(self, handler, client_factory=RabbitMQClient):
        self.handler = handler
        self.client_factory = client_factory
        self.max_retries = int(os.getenv("MAX_RETRIES", "3"))
        self.prefetch = int(os.getenv("RABBITMQ_PREFETCH_COUNT", "1"))

    def _callback(self, channel, method, properties, body):
        headers = dict((properties.headers or {}))
        try:
            self.handler(json.loads(body))
            channel.basic_ack(delivery_tag=method.delivery_tag)
        except Exception:
            retries = int(headers.get("x-retry-count", 0))
            try:
                import pika
                if retries < self.max_retries:
                    headers["x-retry-count"] = retries + 1
                    channel.basic_publish("", EMAIL_QUEUE, body, pika.BasicProperties(delivery_mode=2, content_type="application/json", headers=headers))
                else:
                    channel.basic_publish("", DEAD_LETTER_QUEUE, body, pika.BasicProperties(delivery_mode=2, content_type="application/json", headers=headers))
                channel.basic_ack(delivery_tag=method.delivery_tag)
            except Exception:
                channel.basic_nack(delivery_tag=method.delivery_tag, requeue=True)

    def start(self):
        client = self.client_factory()
        channel = client.connect()
        channel.basic_qos(prefetch_count=self.prefetch)
        channel.basic_consume(queue=EMAIL_QUEUE, on_message_callback=self._callback, auto_ack=False)
        try:
            channel.start_consuming()
        finally:
            client.close()
