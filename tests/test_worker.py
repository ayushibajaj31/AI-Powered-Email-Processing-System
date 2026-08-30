"""Worker persistence and failure behavior with no broker or LLM dependency."""
import unittest
from unittest.mock import patch

from src.workers.email_worker import process_job


class Repository:
    latest = None
    def __init__(self, session): self.failed = None; self.completed = None; Repository.latest = self
    def mark_job_processing(self, job_id): self.processing = job_id
    def complete_job(self, *args): self.completed = args
    def fail_job(self, job_id, error): self.failed = (job_id, str(error))


class Session:
    def __enter__(self): return self
    def __exit__(self, *args): pass


class Generator:
    def process_email(self, *args):
        return {"predicted_category":"Exchange", "response":"Support can help with the exchange.", "sources":[], "classification_time":0.01, "retrieval_time":0.02, "response_generation_time":0.03}


class WorkerTestCase(unittest.TestCase):
    @patch("src.workers.email_worker.ResponseGenerator", Generator)
    @patch("src.workers.email_worker.DatabaseRepository", Repository)
    @patch("src.database.database.SessionLocal", return_value=Session())
    @patch("src.workers.email_worker.configure_database")
    def test_completed_job_stores_measured_timings(self, *_):
        process_job({"job_id":"JOB1","subject":"Exchange","email_body":"Need size swap","customer_id":"C101"})
        completed = Repository.latest.completed
        self.assertEqual(completed[1], "Exchange")
        self.assertIn("classification_time", completed[-1])

    @patch("src.workers.email_worker.ResponseGenerator", side_effect=RuntimeError("LLM unavailable"))
    @patch("src.workers.email_worker.DatabaseRepository", Repository)
    @patch("src.database.database.SessionLocal", return_value=Session())
    @patch("src.workers.email_worker.configure_database")
    def test_worker_failure_is_recorded_and_reraised(self, *_):
        with self.assertRaises(RuntimeError):
            process_job({"job_id":"JOB2","subject":"Help","email_body":"Help","customer_id":"C101"})
        self.assertEqual(Repository.latest.failed[0], "JOB2")


if __name__ == "__main__": unittest.main()
