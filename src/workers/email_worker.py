"""Consume queued jobs and reuse the existing AI response generator."""

import logging
from time import perf_counter

from src.database.database import configure_database
from src.database.repositories import DatabaseRepository
from src.messaging.consumer import EmailJobConsumer
from src.rag.response_generator import ResponseGenerator

LOGGER = logging.getLogger(__name__)

def process_job(message):
    configure_database()
    from src.database.database import SessionLocal
    with SessionLocal() as session:
        repository = DatabaseRepository(session)
        job_id = message["job_id"]
        try:
            repository.mark_job_processing(job_id)
            processing_start = perf_counter()
            generator = ResponseGenerator()
            result = generator.process_email(message["subject"], message["email_body"], message["customer_id"], message.get("order_id"))
            total_time = perf_counter() - processing_start
            repository.complete_job(job_id, result["predicted_category"], result["response"], total_time, result["sources"], {
                "classification_time": result.get("classification_time"), "retrieval_time": result.get("retrieval_time"),
                "llm_generation_time": result.get("response_generation_time"),
            })
            LOGGER.info("Email job completed: %s", job_id)
        except Exception as error:
            repository.fail_job(job_id, error)
            LOGGER.exception("Email job failed: %s", job_id)
            raise

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    EmailJobConsumer(process_job).start()
