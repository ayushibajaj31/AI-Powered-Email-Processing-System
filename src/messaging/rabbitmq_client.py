"""RabbitMQ connection and durable queue declaration."""

import os
from dotenv import load_dotenv

load_dotenv()
EMAIL_QUEUE = "email_processing_queue"
DEAD_LETTER_QUEUE = "email_processing_dead_letter"

class RabbitMQClient:
    def __init__(self, url=None):
        self.url = url or os.getenv("RABBITMQ_URL")
        if not self.url:
            raise RuntimeError("RABBITMQ_URL is not configured.")
        self.connection = None
        self.channel = None

    def connect(self):
        import pika
        self.connection = pika.BlockingConnection(pika.URLParameters(self.url))
        self.channel = self.connection.channel()
        self.channel.queue_declare(queue=DEAD_LETTER_QUEUE, durable=True)
        self.channel.queue_declare(queue=EMAIL_QUEUE, durable=True)
        return self.channel

    def close(self):
        if self.connection and self.connection.is_open:
            self.connection.close()
