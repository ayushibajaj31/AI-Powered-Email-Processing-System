"""Email-processing endpoint that delegates work to the existing response generator."""

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import SQLAlchemyError

from src.api.schemas.email_schemas import EmailJobStatusResponse, EmailProcessRequest, EmailQueuedResponse
from src.auth.dependencies import AuthenticatedUser, get_current_user
from src.database.database import get_session
from src.database.repositories import DatabaseRepository, DatabaseServiceError, OrderOwnershipError, RecordNotFoundError
from src.messaging.publisher import EmailJobPublisher


LOGGER = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/emails", tags=["Email Processing"])


def get_job_publisher():
    return EmailJobPublisher()


def get_database_repository():
    """Provide a request-scoped repository for authorization checks."""
    for session in get_session():
        yield DatabaseRepository(session)


@router.post(
    "/process", response_model=EmailQueuedResponse,
    summary="Validate an email and queue it for asynchronous processing.",
    description="Returns immediately; a RabbitMQ worker runs the existing AI pipeline.",
)
def process_email(
    request: EmailProcessRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
    repository: DatabaseRepository = Depends(get_database_repository),
    publisher: EmailJobPublisher = Depends(get_job_publisher),
):
    LOGGER.info("Email processing request received.")
    try:
        # The body deliberately has no customer_id. The signed token is the only
        # identity source and PostgreSQL remains the ownership authority.
        customer_id = current_user.customer_id
        if not customer_id:
            raise OrderOwnershipError("This account is not linked to a customer.")
        if not repository.get_customer(customer_id):
            raise RecordNotFoundError("Customer was not found.")
        if request.order_id:
            repository.get_verified_order(customer_id, request.order_id)
        job_id = f"JOB-{uuid.uuid4().hex}"
        email_id = f"EMAIL-{uuid.uuid4().hex[:24]}"
        repository.create_email_job(job_id, email_id, customer_id, request.subject, request.email_body)
        publisher.publish({"job_id": job_id, "email_id": email_id, "customer_id": customer_id, "subject": request.subject, "email_body": request.email_body, "order_id": request.order_id})
    except OrderOwnershipError as error:
        LOGGER.warning("Order access denied.")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You do not have access to this order.") from error
    except RecordNotFoundError as error:
        LOGGER.warning("Requested database record was not found.")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="The requested customer or order was not found.") from error
    except DatabaseServiceError as error:
        LOGGER.error("Database service error: %s", error)
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="The database service is unavailable.") from error
    except SQLAlchemyError as error:
        LOGGER.error("Database query failed: %s", error)
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="The database service is unavailable.") from error
    except (ValueError, FileNotFoundError) as error:
        LOGGER.warning("Invalid processing request: %s", error)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="The request could not be processed.") from error
    except Exception as error:
        # Keep the durable job record honest if publishing to RabbitMQ fails.
        try:
            if "job_id" in locals():
                repository.fail_job(job_id, "Queue publishing failed.")
        except Exception:
            LOGGER.exception("Could not mark unpublished job as failed.")
        LOGGER.exception("Queue publishing failed.")
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Email queue service is unavailable.") from error
    return EmailQueuedResponse(job_id=job_id, status="queued", message="Email received and queued for processing.")


@router.get("/jobs/{job_id}", response_model=EmailJobStatusResponse, summary="Get an authenticated customer's email job status.")
def get_job_status(job_id: str, current_user: AuthenticatedUser = Depends(get_current_user), repository: DatabaseRepository = Depends(get_database_repository)):
    try:
        if not current_user.customer_id:
            raise OrderOwnershipError("This account is not linked to a customer.")
        job = repository.get_job_for_customer(job_id, current_user.customer_id)
    except OrderOwnershipError as error:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You do not have access to this job.") from error
    except RecordNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="The requested job was not found.") from error
    result = job.email.processing_results[-1] if job.email.processing_results else None
    return EmailJobStatusResponse(
        job_id=job.job_id, status=job.status, predicted_category=result.predicted_category if result else None,
        response=result.generated_response if result else None,
        sources=getattr(result, "retrieved_sources", None) if result else None,
        processing_time=getattr(result, "processing_time", None) if result else None,
    )
