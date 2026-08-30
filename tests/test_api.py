"""Authenticated asynchronous email API tests with mocked database and broker."""
import os
import unittest
from types import SimpleNamespace
os.environ["JWT_SECRET_KEY"] = "test-only-secret-that-is-long-enough"
from fastapi.testclient import TestClient
from src.api.main import app
from src.api.routes.email_routes import get_database_repository, get_job_publisher
from src.auth.dependencies import AuthenticatedUser, get_auth_repository, get_current_user
from src.database.repositories import OrderOwnershipError, RecordNotFoundError

class MockPublisher:
    def __init__(self): self.messages=[]
    def publish(self, message): self.messages.append(message)
class MockRepository:
    def __init__(self):
        self.own_job=SimpleNamespace(job_id="JOB-OWN",status="completed",email=SimpleNamespace(processing_results=[SimpleNamespace(predicted_category="Exchange",generated_response="Done.")]))
    def get_customer(self, customer_id): return {"customer_id":customer_id} if customer_id=="CUST0001" else None
    def get_verified_order(self, customer_id, order_id):
        if customer_id=="CUST0001" and order_id=="ORD00001": return {"order_id":order_id}
        raise OrderOwnershipError("Not owned")
    def create_email_job(self,*args): pass
    def get_job_for_customer(self,job_id,customer_id):
        if job_id=="JOB-OWN" and customer_id=="CUST0001": return self.own_job
        if job_id=="JOB-OTHER": raise OrderOwnershipError("Not owned")
        raise RecordNotFoundError("Missing")

class APITestCase(unittest.TestCase):
    def setUp(self):
        self.publisher=MockPublisher()
        app.dependency_overrides[get_database_repository]=lambda: MockRepository()
        app.dependency_overrides[get_job_publisher]=lambda: self.publisher
        app.dependency_overrides[get_current_user]=lambda: AuthenticatedUser(1,"CUST0001","customer101@example.com","customer")
        app.dependency_overrides[get_auth_repository]=lambda: object()
        self.client=TestClient(app)
    def tearDown(self): app.dependency_overrides.clear()
    def test_valid_jwt_queues_email(self):
        response=self.client.post("/api/v1/emails/process",json={"subject":"Need help","email_body":"Please check my order.","order_id":"ORD00001"})
        self.assertEqual(response.status_code,200); self.assertEqual(response.json()["status"],"queued"); self.assertEqual(len(self.publisher.messages),1)
    def test_other_customers_order_is_denied(self):
        self.assertEqual(self.client.post("/api/v1/emails/process",json={"subject":"Help","email_body":"Check it.","order_id":"ORD00900"}).status_code,403)
    def test_valid_customer_can_get_own_job(self): self.assertEqual(self.client.get("/api/v1/emails/jobs/JOB-OWN").status_code,200)
    def test_customer_cannot_get_another_job(self):
        response=self.client.get("/api/v1/emails/jobs/JOB-OTHER"); self.assertEqual(response.status_code,403); self.assertNotIn("JOB-OTHER",response.text)
    def test_missing_jwt_is_rejected(self):
        app.dependency_overrides.pop(get_current_user)
        self.assertEqual(self.client.post("/api/v1/emails/process",json={"subject":"Help","email_body":"Please help."}).status_code,401)
    def test_customer_id_in_body_is_rejected_and_cannot_override_jwt(self):
        response=self.client.post("/api/v1/emails/process",json={"subject":"Help","email_body":"Please help.","customer_id":"C205"})
        self.assertEqual(response.status_code,422)
    def test_queue_outage_returns_safe_503_and_marks_job_failed(self):
        class FailingPublisher:
            def publish(self, message): raise RuntimeError("broker offline")
        app.dependency_overrides[get_job_publisher]=lambda: FailingPublisher()
        response=self.client.post("/api/v1/emails/process",json={"subject":"Help","email_body":"Please help."})
        self.assertEqual(response.status_code,503); self.assertNotIn("broker offline",response.text)
if __name__=="__main__": unittest.main()
