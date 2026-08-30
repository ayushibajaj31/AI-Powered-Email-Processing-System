"""Create reproducible, connected synthetic e-commerce datasets."""

import csv
import random
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path 


SEED = 42
CUSTOMER_COUNT = 300
ORDER_COUNT = 1_200
EMAILS_PER_CATEGORY = 300  # 2,400 emails total, balanced across eight categories.
CATEGORIES = [
    "Order Status", "Return/Refund", "Cancellation", "Payment Issue",
    "Product Information", "Complaint", "Exchange", "Other",
]
STATUSES = ["Processing", "Shipped", "Out for Delivery", "Delivered", "Cancelled", "Returned"]
PAYMENT_STATUSES = ["Paid", "Pending", "Failed", "Refunded"]

FIRST_NAMES = ["Avery", "Casey", "Jordan", "Morgan", "Riley", "Taylor", "Jamie", "Quinn", "Rowan", "Skyler"]
LAST_NAMES = ["Briar", "Cove", "Dale", "Ember", "Fern", "Grove", "Hollow", "Ivy", "Juniper", "Lark"]
PRODUCT_FAMILIES = [
    ("Electronics", "Audio", "Auralis", ["Wireless Earbuds", "Noise-Canceling Headphones", "Portable Speaker", "Studio Microphone"]),
    ("Clothing", "Outerwear", "Threadline", ["Fleece Hoodie", "Rain Jacket", "Denim Jacket", "Quilted Vest"]),
    ("Footwear", "Running Shoes", "Strideway", ["Daily Runner", "Trail Runner", "Walking Shoe", "Training Shoe"]),
    ("Home Appliances", "Small Appliances", "Hearthwise", ["Compact Blender", "Air Fryer", "Electric Kettle", "Coffee Grinder"]),
    ("Beauty", "Skin Care", "Lumina", ["Hydrating Serum", "Gentle Cleanser", "Night Cream", "Vitamin C Set"]),
    ("Accessories", "Bags", "Wayfinder", ["Travel Backpack", "Crossbody Bag", "Laptop Sleeve", "Canvas Tote"]),
    ("Sports", "Fitness", "Peakform", ["Yoga Mat", "Resistance Band Set", "Foam Roller", "Insulated Bottle"]),
    ("Home & Kitchen", "Kitchenware", "Cedar & Co.", ["Ceramic Mug Set", "Bamboo Organizer", "Cast Iron Pan", "Glass Storage Set"]),
]
PRODUCT_STYLES = ["Nimbus", "Harbor", "Orbit", "Cedar", "Solace", "Nova", "Pioneer", "Atlas", "Willow", "Lumen", "Summit", "Meadow", "Ember", "Coast", "Sage", "Drift", "Echo", "Terra", "Aster", "Brook"]


def random_date(rng, start, end):
    return start + timedelta(days=rng.randint(0, (end - start).days))


def write_csv(path, rows, columns):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def create_customers(rng):
    customers = []
    for number in range(1, CUSTOMER_COUNT + 1):
        first = rng.choice(FIRST_NAMES)
        last = rng.choice(LAST_NAMES)
        customers.append({
            "customer_id": f"CUST{number:04d}",
            "customer_name": f"{first} {last}",
            "email_address": f"{first.lower()}.{last.lower()}{number}@example.test",
            "phone_number": f"+1-555-{rng.randint(100, 999)}-{rng.randint(1000, 9999)}",
            "customer_since": random_date(rng, datetime(2022, 1, 1), datetime(2025, 12, 31)).date().isoformat(),
        })
    return customers


def create_products(rng):
    """Create a 160-item catalog with attributes useful for later retrieval."""
    products = []
    number = 1
    for category, subcategory, brand, item_types in PRODUCT_FAMILIES:
        for style in PRODUCT_STYLES:
            item_type = rng.choice(item_types)
            has_sizes = category in {"Clothing", "Footwear"}
            products.append({
                "product_id": f"PRD-{number:03d}",
                "product_name": f"{style} {item_type}",
                "category": category,
                "subcategory": subcategory,
                "brand": brand,
                "description": f"The {style} {item_type} is designed for reliable everyday use, with practical materials and a thoughtful, durable finish.",
                "price": f"{rng.uniform(18, 180):.2f}",
                "available_sizes": "XS,S,M,L,XL" if category == "Clothing" else ("7,8,9,10,11" if has_sizes else ""),
                "available_colors": rng.choice(["Black, Blue, White", "Charcoal, Green, Sand", "Navy, Grey, Red", "White, Beige, Teal"]),
                "stock_quantity": str(rng.randint(8, 120)),
                "warranty_period": rng.choice(["6 months", "1 year", "2 years"]) if category in {"Electronics", "Home Appliances"} else "No warranty",
                "returnable": "Yes",
                "product_rating": f"{rng.uniform(3.6, 4.9):.1f}",
            })
            number += 1
    return products


def create_orders(rng, customers, products):
    orders = []
    customer_ids = [customer["customer_id"] for customer in customers]
    for number in range(1, ORDER_COUNT + 1):
        product = rng.choice(products)
        status = rng.choices(STATUSES, weights=[20, 22, 10, 35, 6, 7], k=1)[0]
        payment = "Refunded" if status in {"Cancelled", "Returned"} and rng.random() < 0.7 else rng.choices(PAYMENT_STATUSES, weights=[75, 10, 8, 7], k=1)[0]
        quantity = rng.choice([1, 1, 1, 2])
        orders.append({
            "order_id": f"ORD{number:05d}",
            "customer_id": rng.choice(customer_ids),
            "product_id": product["product_id"],
            "product_name": product["product_name"],
            "order_date": random_date(rng, datetime(2025, 1, 1), datetime(2026, 8, 10)).date().isoformat(),
            "order_status": status,
            "payment_status": payment,
            "order_amount": f"{float(product['price']) * quantity:.2f}",
        })
    return orders


def email_text(category, rng, customer_name, order, products):
    """Return a varied, realistic email subject and body for one category."""
    product = rng.choice(products)["product_name"] if order is None else order["product_name"]
    order_id = "" if order is None else order["order_id"]
    order_status = "processing" if order is None else order["order_status"].lower()
    greeting = rng.choice(["Hi", "Hello", "Hey", "Dear support team"])
    signoff = rng.choice(["Thanks", "Thank you", "Regards", "Please help"])

    templates = {
        "Order Status": [
            ("Where is my order?", f"{greeting}, I placed order {order_id} a few days ago and it still says {order_status}. Can you tell me when it will arrive? {signoff}, {customer_name}"),
            ("Tracking update needed", f"Could you check the delivery status of {order_id}? The tracking has not changed and I am starting to worry."),
            ("Has my package shipped?", f"Hi, I ordered a {product}. Is order {order_id} on its way yet?"),
        ],
        "Return/Refund": [
            ("I need to return an item", f"{greeting}, I received the {product} from order {order_id}, but it does not fit my needs. Please send the return instructions."),
            ("Refund status", f"I returned order {order_id} and have not received my refund. Can someone check the status for me?"),
            ("Return request", f"The {product} arrived damaged. I would like to return it and receive a refund for {order_id}."),
        ],
        "Cancellation": [
            ("Please cancel my order", f"{greeting}, please cancel order {order_id} before it ships. I made this purchase by mistake."),
            ("Cancel order", f"I no longer need the {product}. Can you cancel {order_id} and refund the payment?"),
            ("Accidental order", f"Oops, I ordered the wrong item. Is it still possible to stop order {order_id}?"),
        ],
        "Payment Issue": [
            ("I was charged twice", f"I can see two charges for order {order_id}, but I only placed one order. Please look into this."),
            ("Payment problem", f"My card payment for {order_id} is still pending in my bank app. Did the order go through?"),
            ("Checkout error", f"Hi, my payment keeps failing when I try to buy the {product}. The card works everywhere else."),
        ],
        "Product Information": [
            (f"Question about {product}", f"{greeting}, could you tell me more about the {product}? I need the size, material, and care details before ordering."),
            ("Is this in stock?", f"Do you still have the {product} available? I am looking for one as a gift."),
            ("Warranty question", f"Hi, does the {product} come with a warranty? I could not find the answer on the product page."),
        ],
        "Complaint": [
            ("Very disappointed", f"{greeting}, I am unhappy with order {order_id}. The {product} was not as described and this has been frustrating."),
            ("Complaint about delivery", f"My package for {order_id} arrived much later than promised and nobody sent an update. This is not acceptable."),
            ("Poor experience", f"I have tried to get help with {order_id} twice. Still no answer. Really disappointed with the service."),
        ],
        "Exchange": [
            ("Need a different size", f"{greeting}, I received the {product} from order {order_id}, but the size is wrong. Can I exchange it for a smaller size?"),
            ("Exchange request", f"I would like to exchange the {product} from order {order_id} for a different size or color. Please tell me the next steps."),
            ("Wrong item size", f"The item in order {order_id} does not fit. I do not need a refund; I would prefer an exchange if possible."),
            ("Can you replace this?", f"Hi, the {product} from {order_id} is the wrong size. How can I swap it for the correct one?"),
        ],
        "Other": [
            ("Need account help", f"{greeting}, I cannot log in after resetting my password. Can you help me access my account?"),
            ("Discount code question", f"Do you have a student discount or a promo code I can use for the {product}?"),
            ("Change my address", f"Hi, how do I update the delivery address saved in my account for future orders?"),
        ],
    }
    subject, body = rng.choice(templates[category])
    urgency = rng.choice(["today", "when you can", "before the weekend", "as soon as possible", "this week"])
    extra = rng.choice([
        "I checked the help page but could not find a clear answer.",
        "A quick reply would be appreciated.", "Please let me know what you need from me.",
        "Sorry if I missed this information somewhere.", "I hope this can be resolved soon.",
    ])
    return subject, f"{body} Please reply {urgency}. {extra} Kind regards, {customer_name}."


def create_emails(rng, customers, orders, products):
    emails, used_bodies = [], set()
    orders_by_customer = {}
    for order in orders:
        orders_by_customer.setdefault(order["customer_id"], []).append(order)

    number = 1
    for category in CATEGORIES:
        while sum(row["category"] == category for row in emails) < EMAILS_PER_CATEGORY:
            needs_order = category not in {"Product Information", "Other"} or rng.random() < 0.65
            eligible_customers = [
                customer for customer in customers
                if not needs_order or customer["customer_id"] in orders_by_customer
            ]
            customer = rng.choice(eligible_customers)
            customer_orders = orders_by_customer.get(customer["customer_id"], [])
            order = rng.choice(customer_orders) if needs_order else None
            subject, body = email_text(category, rng, customer["customer_name"], order, products)
            if body in used_bodies:
                continue
            used_bodies.add(body)
            base_time = datetime(2026, 1, 1) + timedelta(days=rng.randint(0, 237), hours=rng.randint(8, 20), minutes=rng.randint(0, 59))
            emails.append({
                "email_id": f"EMAIL{number:05d}",
                "customer_id": customer["customer_id"],
                "subject": subject,
                "email_body": body,
                "timestamp": base_time.isoformat(sep=" ", timespec="minutes"),
                "category": category,
                "order_id": "" if order is None else order["order_id"],
            })
            number += 1
    rng.shuffle(emails)
    return emails


def validate(customers, products, orders, emails):
    customer_ids = {row["customer_id"] for row in customers}
    order_ids = {row["order_id"] for row in orders}
    product_names = {row["product_id"]: row["product_name"] for row in products}
    assert len(customer_ids) == len(customers), "Customer IDs are not unique."
    assert len({row["email_address"] for row in customers}) == len(customers), "Email addresses are not unique."
    assert len(order_ids) == len(orders), "Order IDs are not unique."
    assert len(product_names) == len(products), "Product IDs are not unique."
    assert len({row["email_id"] for row in emails}) == len(emails), "Email IDs are not unique."
    assert all(row["customer_id"] in customer_ids for row in orders), "Unknown customer in orders."
    assert all(row["product_id"] in product_names for row in orders), "Unknown product in orders."
    assert all(row["product_name"] == product_names[row["product_id"]] for row in orders), "Product name mismatch in orders."
    assert all(row["customer_id"] in customer_ids for row in emails), "Unknown customer in emails."
    assert all(not row["order_id"] or row["order_id"] in order_ids for row in emails), "Unknown order in emails."


def main():
    rng = random.Random(SEED)
    customers = create_customers(rng)
    products = create_products(rng)
    orders = create_orders(rng, customers, products)
    emails = create_emails(rng, customers, orders, products)
    validate(customers, products, orders, emails)

    root = Path(__file__).resolve().parents[2]
    raw = root / "data" / "raw"
    write_csv(raw / "customers.csv", customers, list(customers[0]))
    write_csv(raw / "products.csv", products, list(products[0]))
    write_csv(raw / "orders.csv", orders, list(orders[0]))
    write_csv(raw / "emails.csv", emails, list(emails[0]))

    counts = Counter(row["category"] for row in emails)
    multi_order_customers = len({row["customer_id"] for row in orders if sum(o["customer_id"] == row["customer_id"] for o in orders) > 1})
    missing = sum(not value.strip() for row in customers + orders for value in row.values())
    missing += sum(not value.strip() for row in emails for key, value in row.items() if key != "order_id")
    print(f"Customers: {len(customers)}")
    print(f"Products: {len(products)}")
    print(f"Orders: {len(orders)}")
    print(f"Emails: {len(emails)}")
    print("Emails per category:")
    for category in CATEGORIES:
        print(f"  {category}: {counts[category]}")
    print(f"Customers with multiple orders: {multi_order_customers}")
    print(f"Emails linked to orders: {sum(bool(row['order_id']) for row in emails)}")
    print(f"Emails without order IDs: {sum(not row['order_id'] for row in emails)}")
    print(f"Duplicate emails: {len(emails) - len({row['email_body'] for row in emails})}")
    print(f"Missing values (excluding optional order_id): {missing}")
    print(f"Saved files to: {raw}")


if __name__ == "__main__":
    main()
