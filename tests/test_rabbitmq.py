"""Messaging behavior tests using fake broker objects."""
import json
import unittest
from unittest.mock import patch
from src.messaging.consumer import EmailJobConsumer
from src.messaging.publisher import EmailJobPublisher
from src.messaging.rabbitmq_client import RabbitMQClient
class Channel:
    def __init__(self): self.published=[]; self.acks=[]; self.nacks=[]
    def basic_publish(self,exchange,routing_key,body,properties): self.published.append((routing_key,json.loads(body)))
    def basic_ack(self,delivery_tag): self.acks.append(delivery_tag)
    def basic_nack(self,delivery_tag,requeue): self.nacks.append((delivery_tag,requeue))
class Client:
    def __init__(self): self.channel=Channel(); self.closed=False
    def connect(self): return self.channel
    def close(self): self.closed=True
class RabbitMQTestCase(unittest.TestCase):
    def test_connection_declares_durable_queues(self):
        channel=type("DeclaredChannel",(),{"declared":[],"queue_declare":lambda self,**kwargs:self.declared.append(kwargs)})()
        connection=type("Connection",(),{"channel":lambda self:channel,"is_open":False})()
        with patch("pika.BlockingConnection",return_value=connection):
            RabbitMQClient("amqp://guest:guest@localhost:5672/").connect()
        self.assertEqual([item["queue"] for item in channel.declared],["email_processing_dead_letter","email_processing_queue"])
    def test_publish_json_job(self):
        client=Client()
        with patch("pika.BasicProperties",lambda **kwargs:kwargs): EmailJobPublisher(client_factory=lambda:client).publish({"job_id":"JOB1"})
        self.assertEqual(client.channel.published[0][1]["job_id"],"JOB1")
    def test_success_is_acknowledged(self):
        channel=Channel(); EmailJobConsumer(lambda message:None)._callback(channel,type("M",(),{"delivery_tag":1})(),type("P",(),{"headers":{}})(),b'{"job_id":"JOB1"}')
        self.assertEqual(channel.acks,[1])
    def test_failure_retries_then_dead_letters(self):
        channel=Channel(); consumer=EmailJobConsumer(lambda message:(_ for _ in ()).throw(ValueError("bad")))
        with patch("pika.BasicProperties",lambda **kwargs:kwargs):
            consumer._callback(channel,type("M",(),{"delivery_tag":1})(),type("P",(),{"headers":{"x-retry-count":0}})(),b'{"job_id":"JOB1"}')
            consumer.max_retries=0; consumer._callback(channel,type("M",(),{"delivery_tag":2})(),type("P",(),{"headers":{"x-retry-count":0}})(),b'{"job_id":"JOB1"}')
        self.assertEqual([item[0] for item in channel.published],["email_processing_queue","email_processing_dead_letter"])
if __name__=="__main__": unittest.main()
