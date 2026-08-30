"""Repository tests using an in-memory database; no PostgreSQL server is required."""

import unittest
from datetime import date
from decimal import Decimal

from src.database.database import Base, configure_database
from src.database.models import Customer, Order, OrderItem, Product
from src.database.repositories import DatabaseRepository, OrderOwnershipError, RecordNotFoundError


class DatabaseRepositoryTestCase(unittest.TestCase):
    def setUp(self):
        self.engine = configure_database("sqlite+pysqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        from src.database.database import SessionLocal
        self.session = SessionLocal()
        first = Customer(customer_id="C101", name="Asha Test", email="asha@example.test")
        second = Customer(customer_id="C205", name="Ravi Test", email="ravi@example.test")
        product = Product(product_id="P023", product_name="Trail Shoe", category="Shoes", description="Synthetic test product", price=Decimal("60.00"), stock=8)
        self.session.add_all([first, second, product])
        self.session.flush()
        own_order = Order(order_id="ORD500", customer_id=first.id, order_date=date(2026, 1, 1), status="Processing", payment_status="Paid", total_amount=Decimal("60.00"))
        other_order = Order(order_id="ORD900", customer_id=second.id, order_date=date(2026, 1, 2), status="Shipped", payment_status="Paid", total_amount=Decimal("60.00"))
        self.session.add_all([own_order, other_order])
        self.session.flush()
        self.session.add_all([
            OrderItem(order_id=own_order.id, product_id=product.id, quantity=1, unit_price=Decimal("60.00")),
            OrderItem(order_id=other_order.id, product_id=product.id, quantity=1, unit_price=Decimal("60.00")),
        ])
        self.session.commit()
        self.repository = DatabaseRepository(self.session)

    def tearDown(self):
        self.session.close()
        Base.metadata.drop_all(self.engine)
        self.engine.dispose()

    def test_customer_and_product_lookup(self):
        self.assertEqual(self.repository.get_customer("C101")["customer_name"], "Asha Test")
        self.assertEqual(self.repository.get_product("P023")["product_name"], "Trail Shoe")

    def test_order_and_relationship_lookups(self):
        self.assertEqual(self.repository.get_order("ORD500")["customer_id"], "C101")
        self.assertEqual(self.repository.get_customer_orders("C101")[0]["order_id"], "ORD500")
        self.assertEqual(self.repository.get_order_items("ORD500")[0]["product_id"], "P023")
        self.assertEqual(self.repository.get_products_for_order("ORD500")[0]["product_id"], "P023")

    def test_valid_order_ownership(self):
        self.assertTrue(self.repository.verify_order_ownership("C101", "ORD500"))
        self.assertEqual(self.repository.get_verified_order("C101", "ORD500")["order_id"], "ORD500")

    def test_invalid_order_ownership_never_returns_order(self):
        self.assertFalse(self.repository.verify_order_ownership("C101", "ORD900"))
        with self.assertRaises(OrderOwnershipError):
            self.repository.get_verified_order("C101", "ORD900")

    def test_nonexistent_customer_and_order(self):
        with self.assertRaises(RecordNotFoundError):
            self.repository.get_verified_order("C404", "ORD500")
        with self.assertRaises(RecordNotFoundError):
            self.repository.get_verified_order("C101", "ORD404")


if __name__ == "__main__":
    unittest.main()
