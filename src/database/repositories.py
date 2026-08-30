"""Reusable data access and order-ownership verification services."""

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from .models import Customer, Email, EmailProcessingJob, EmailProcessingResult, Order, OrderItem, Product, User


class DatabaseServiceError(RuntimeError):
    pass


class RecordNotFoundError(DatabaseServiceError):
    pass


class OrderOwnershipError(DatabaseServiceError):
    pass


class DatabaseRepository:
    def __init__(self, session: Session):
        self.session = session

    @staticmethod
    def customer_dict(customer):
        if customer is None:
            return None
        # Address and payment details are not included. Phone is omitted from the
        # cached/shared lookup shape because it is not required for RAG or replies.
        return {
            "customer_id": customer.customer_id,
            "customer_name": customer.name,
            "email_address": customer.email,
            "customer_since": customer.created_at.date().isoformat() if customer.created_at else "",
        }

    @staticmethod
    def product_dict(product):
        return None if product is None else {"product_id": product.product_id, "product_name": product.product_name, "category": product.category, "description": product.description, "price": str(product.price), "stock_quantity": str(product.stock), "warranty_period": product.warranty or "", "available_sizes": product.available_sizes or "", "available_colors": product.available_colors or ""}

    @staticmethod
    def order_dict(order):
        return None if order is None else {"order_id": order.order_id, "customer_id": order.customer.customer_id, "order_date": order.order_date.isoformat(), "order_status": order.status, "payment_status": order.payment_status, "order_amount": str(order.total_amount)}

    def get_customer(self, customer_id):
        if not customer_id:
            return None
        return self.customer_dict(self.session.scalar(select(Customer).where(Customer.customer_id == customer_id)))

    def get_user_by_email(self, email):
        return self.session.scalar(select(User).where(User.email == email.lower()))

    def get_user_by_subject(self, subject):
        """Look up the database user represented by a minimal JWT subject."""
        if subject.startswith("user:"):
            try:
                return self.session.get(User, int(subject.removeprefix("user:")))
            except ValueError:
                return None
        return self.session.scalar(
            select(User).join(User.customer).where(Customer.customer_id == subject)
        )

    def get_product(self, product_id):
        if not product_id:
            return None
        return self.product_dict(self.session.scalar(select(Product).where(Product.product_id == product_id)))

    def _order(self, order_id):
        return self.session.scalar(select(Order).options(selectinload(Order.customer), selectinload(Order.items).selectinload(OrderItem.product)).where(Order.order_id == order_id))

    def get_order(self, order_id):
        """Unscoped lookup. Customer-specific caching happens in get_verified_order."""
        return self.order_dict(self._order(order_id))

    def get_customer_orders(self, customer_id):
        return [self.order_dict(order) for order in self.session.scalars(select(Order).join(Order.customer).options(selectinload(Order.customer)).where(Customer.customer_id == customer_id)).all()]

    def get_order_items(self, order_id):
        order = self._order(order_id)
        if not order:
            return []
        return [{"product_id": item.product.product_id, "quantity": item.quantity, "unit_price": str(item.unit_price)} for item in order.items]

    def get_product_for_order(self, order_id):
        order = self._order(order_id)
        return self.get_product(order.items[0].product.product_id) if order and order.items else None

    def get_products_for_order(self, order_id):
        """Return every product on an order, without making an ownership decision."""
        order = self._order(order_id)
        return [] if not order else [self.get_product(item.product.product_id) for item in order.items]

    def verify_order_ownership(self, customer_id, order_id):
        order = self._order(order_id)
        return bool(order and order.customer.customer_id == customer_id)

    def get_verified_order(self, customer_id, order_id):
        customer = self.get_customer(customer_id)
        if not customer:
            raise RecordNotFoundError("Customer was not found.")
        order = self._order(order_id)
        if not order:
            raise RecordNotFoundError("Order was not found.")
        # PostgreSQL is the authorization authority for every order lookup.
        if order.customer.customer_id != customer_id:
            raise OrderOwnershipError("Order does not belong to this customer.")
        return self.order_dict(order)

    def create_email_job(self, job_id, email_id, customer_id, subject, email_body):
        customer = self.session.scalar(select(Customer).where(Customer.customer_id == customer_id))
        if not customer:
            raise RecordNotFoundError("Customer was not found.")
        email = Email(email_id=email_id, customer_id=customer.id, subject=subject, body=email_body)
        self.session.add(email)
        self.session.flush()
        job = EmailProcessingJob(job_id=job_id, email_id=email.id, customer_id=customer.id, status="queued")
        self.session.add(job)
        self.session.commit()
        self.session.refresh(job)
        return job

    def get_job_for_customer(self, job_id, customer_id):
        job = self.session.scalar(
            select(EmailProcessingJob).options(selectinload(EmailProcessingJob.customer), selectinload(EmailProcessingJob.email).selectinload(Email.processing_results)).where(EmailProcessingJob.job_id == job_id)
        )
        if not job:
            raise RecordNotFoundError("Job was not found.")
        if job.customer.customer_id != customer_id:
            raise OrderOwnershipError("Job does not belong to this customer.")
        return job

    def get_job(self, job_id):
        return self.session.scalar(select(EmailProcessingJob).where(EmailProcessingJob.job_id == job_id))

    def mark_job_processing(self, job_id):
        job = self.get_job(job_id)
        if not job:
            raise RecordNotFoundError("Job was not found.")
        job.status, job.error_message, job.started_at = "processing", None, datetime.now(timezone.utc)
        self.session.commit()
        return job

    def complete_job(self, job_id, predicted_category, response, processing_time, sources, timings=None):
        job = self.get_job(job_id)
        if not job:
            raise RecordNotFoundError("Job was not found.")
        job.email.predicted_category = predicted_category
        timings = timings or {}
        self.session.add(EmailProcessingResult(
            email_id=job.email_id, predicted_category=predicted_category, generated_response=response,
            processing_time=processing_time, retrieved_sources=sources,
            classification_time=timings.get("classification_time"), retrieval_time=timings.get("retrieval_time"),
            llm_generation_time=timings.get("llm_generation_time"),
        ))
        job.status, job.error_message, job.completed_at = "completed", None, datetime.now(timezone.utc)
        self.session.commit()

    def fail_job(self, job_id, error):
        job = self.get_job(job_id)
        if job:
            job.status, job.error_message, job.completed_at = "failed", str(error)[:500], datetime.now(timezone.utc)
            self.session.commit()
