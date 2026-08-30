"""Create a synthetic policy knowledge base for the fictional company Northstar Market."""

import json
from pathlib import Path
from textwrap import dedent


COMPANY = "Northstar Market"
VERSION = "1.0"


def project_root():
    return Path(__file__).resolve().parents[2]


def documents():
    """Return small, focused policy documents rather than one large file."""
    return {
        "shipping/order_processing.txt": ("shipping", "order_processing", "KB_SHIPPING_001", """
            Order Processing and Confirmation
            Northstar Market begins processing paid orders within 1-2 business days. Orders placed after 5:00 PM local warehouse time, on weekends, or on public holidays start processing on the next business day. An order-confirmation email is sent immediately after checkout; a shipping-confirmation email with tracking is sent after dispatch. Customers may request changes or cancellation only while an order remains Processing.
        """),
        "shipping/order_tracking.txt": ("shipping", "order_tracking", "KB_SHIPPING_002", """
            Order Tracking
            Tracking becomes active within 24 hours after a shipment email is sent. Customers can use the tracking link in that email or their order number in the Northstar Market order page. A scan may not appear every day while a parcel is moving. Contact support if tracking has not changed for 3 business days after dispatch.
        """),
        "shipping/shipping_policy.txt": ("shipping", "shipping_policy", "KB_SHIPPING_003", """
            Shipping Methods, Delivery Times, and Charges
            Standard shipping costs $5.99 and normally arrives 3-5 business days after dispatch. Express shipping costs $14.99 and normally arrives 1-2 business days after dispatch. Orders of $75 or more receive free standard shipping. Delivery estimates do not include the 1-2 business day processing period. A delivery address can be changed only before the order is dispatched; support must confirm the change.
        """),
        "shipping/delivery_issues.txt": ("shipping", "delivery_issues", "KB_SHIPPING_004", """
            Delayed, Lost, and Failed Deliveries
            A parcel is considered delayed when it is more than 3 business days beyond its delivery estimate. Support will open a carrier inquiry for a parcel with no tracking movement for 3 business days. A parcel may be treated as lost after the carrier investigation confirms loss or after 10 calendar days without a scan. Carriers make up to 3 delivery attempts. After a failed delivery, customers should contact the carrier or support within 5 calendar days to arrange the next step.
        """),
        "returns/return_policy.txt": ("returns", "return_policy", "KB_RETURN_001", """
            Return Policy and Eligibility
            Most unused products may be returned within 30 calendar days of delivery for a refund. Items must include original accessories and be in resaleable condition. Personalized products, gift cards, and opened hygiene-sensitive beauty items are non-returnable unless they arrive damaged or incorrect. Return approval is required before sending an item back. Return shipping is free when Northstar Market sent a damaged or wrong item; otherwise the customer pays the return label cost.
        """),
        "returns/refund_policy.txt": ("returns", "refund_policy", "KB_RETURN_002", """
            Refund Process and Timing
            After an approved return reaches the warehouse, inspection is normally completed within 2 business days. Approved refunds are issued to the original payment method within 5-7 business days after inspection. A bank or card provider may take additional time to display the credit. Shipping charges are refundable only when Northstar Market made a shipping error, sent the wrong item, or the item was damaged on arrival.
        """),
        "returns/damaged_wrong_products.txt": ("returns", "damaged_wrong_products", "KB_RETURN_003", """
            Damaged or Wrong Products
            Customers should report a damaged or incorrect product within 7 calendar days of delivery and include photos of the item, packaging, and shipping label when possible. Support will offer an approved return, replacement, or refund according to stock availability and customer preference. A damaged or wrong product can be handled even if it is normally non-returnable. Do not discard the item until support gives instructions.
        """),
        "exchange/exchange_policy.txt": ("exchange", "exchange_policy", "KB_EXCHANGE_001", """
            Exchange Policy
            Exchange is separate from a refund return. Eligible unused items may be exchanged within 30 calendar days of delivery for a different size, color, or variant of the same product. The requested replacement must be available. Personalized products, gift cards, and opened hygiene-sensitive beauty items cannot be exchanged unless they arrived damaged or incorrect. An exchange does not create a cash refund unless Northstar Market cannot supply an agreed replacement.
        """),
        "exchange/exchange_process.txt": ("exchange", "exchange_process", "KB_EXCHANGE_002", """
            Exchange Process and Shipping
            Customers request an exchange through support with their order number, requested size, color, or variant, and reason. Support confirms eligibility and reserves replacement stock when possible. The customer receives return instructions. Once the original item is scanned by the carrier, the replacement is dispatched within 1-2 business days. Northstar Market pays exchange shipping for a damaged or wrong item; for preference-based size or color exchanges, the customer pays the return label and Northstar Market pays standard replacement shipping once.
        """),
        "exchange/exchange_availability.txt": ("exchange", "exchange_availability", "KB_EXCHANGE_003", """
            Exchange Availability and Exceptions
            A size, color, or product-variant exchange depends on live replacement stock. If the requested item is unavailable, customers may choose a different available variant, a comparable product with payment adjustment, store credit, or a refund under the return policy. For a damaged or wrong item, support can prioritize a replacement when stock exists. Replacement stock is not guaranteed until support confirms the exchange.
        """),
        "cancellation/cancellation_policy.txt": ("cancellation", "cancellation_policy", "KB_CANCEL_001", """
            Cancellation Policy
            An order may be cancelled only while its status is Processing. Support submits the request immediately but cannot guarantee cancellation once warehouse work begins. A cancelled paid order is refunded to the original payment method within 5-7 business days. After dispatch, an order cannot be cancelled or redirected; customers may use the return policy after delivery. A delivered order cannot be cancelled and must be handled as a return or exchange when eligible.
        """),
        "payments/payment_methods.txt": ("payments", "payment_methods", "KB_PAYMENT_001", """
            Supported Payment Methods and Verification
            Northstar Market accepts major credit and debit cards, approved digital wallets, and store credit. Payment is authorized at checkout; a temporary authorization may appear before final capture. Some orders require identity or payment verification to protect customers from fraud. Support never asks for a full card number, card security code, or account password by email.
        """),
        "payments/payment_issues.txt": ("payments", "payment_issues", "KB_PAYMENT_002", """
            Failed, Pending, and Duplicate Payments
            A failed payment does not create a confirmed order. A pending authorization normally clears or becomes a completed payment within 3-5 business days, depending on the bank. Customers who see two completed charges for one order should contact support with the order number and transaction dates; Northstar Market investigates and reverses a confirmed duplicate charge within 5-7 business days. Payment-related refunds return to the original payment method.
        """),
        "products/product_information.txt": ("products", "product_information", "KB_PRODUCT_001", """
            Product Information Source
            Northstar Market maintains detailed product specifications, live stock, sizes, colors, prices, care guidance, and ratings in the structured product catalog. Support should use the catalog for questions about a particular product. Catalog availability can change, so a product page or catalog lookup is the current source for stock. Company policy documents explain rules such as returns and exchanges; they do not replace product-specific facts.
        """),
        "products/warranty.txt": ("products", "warranty", "KB_PRODUCT_002", """
            Warranty Information
            Warranty duration is product-specific and appears in the product catalog. Electronics and home appliances may include a 6-month, 1-year, or 2-year limited warranty; products without a warranty are marked "No warranty" in the catalog. Warranties cover manufacturing defects under normal use, not accidental damage, misuse, or normal wear. Customers should provide an order number and a description or photo of the defect when requesting warranty support.
        """),
        "support/customer_support.txt": ("support", "customer_support", "KB_SUPPORT_001", """
            Customer Support and Response Time
            Customers can contact Northstar Market through the support form or reply to an order email. Standard support replies within 1 business day. Questions involving payment security, a damaged or wrong item, a lost package, or an order that must be cancelled before shipment are priority issues and are reviewed within 4 business hours on business days. Include the order number when available to help support investigate.
        """),
        "support/complaint_handling.txt": ("support", "complaint_handling", "KB_SUPPORT_002", """
            Complaint Handling
            Support acknowledges a complaint within 1 business day, records the issue, and investigates the relevant order, delivery, product, or payment information. Customers should receive a clear next step and expected resolution timeframe. Staff should not promise a refund, replacement, or compensation until eligibility and evidence have been checked.
        """),
        "support/escalation_policy.txt": ("support", "escalation_policy", "KB_SUPPORT_003", """
            Escalation and Priority Issues
            Support escalates suspected fraud, duplicate completed charges, lost-package investigations, repeated failed deliveries, damaged or wrong-item claims, and unresolved complaints. A support lead reviews escalated cases within 1 business day. For a damaged or wrong item, photos and the order number speed up review, but an incomplete photo set does not automatically close the case.
        """),
        "faq/frequently_asked_questions.txt": ("faq", "frequently_asked_questions", "KB_FAQ_001", """
            Frequently Asked Questions
            Q: How long does standard shipping take? A: Standard shipping normally takes 3-5 business days after dispatch, plus 1-2 business days for processing.
            Q: Can I return an item after 20 days? A: Yes, most unused eligible products can be returned within 30 calendar days of delivery.
            Q: How long does a refund take? A: Inspection normally takes 2 business days after receipt, then the refund is issued within 5-7 business days.
            Q: Can I exchange shoes for another size? A: Yes, eligible unused items can be exchanged within 30 calendar days if the requested size is available.
            Q: My order already shipped. Can I cancel it? A: No. After dispatch, use the return policy after delivery if eligible.
            Q: I received the wrong item. What should I do? A: Contact support within 7 calendar days with your order number and photos when possible.
            Q: Does every product have a warranty? A: No. Check the product catalog; warranty duration is product-specific.
        """),
    }


def create_knowledge_base(output_directory):
    metadata = []
    for relative_path, (category, topic, document_id, content) in documents().items():
        path = output_directory / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(dedent(content).strip() + "\n", encoding="utf-8")
        metadata.append({"document_id": document_id, "file_name": relative_path, "category": category, "topic": topic, "source": "company_policy", "version": VERSION})
    (output_directory / "metadata.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    return metadata


def validate_required_topics(metadata):
    required = {"order_processing", "order_tracking", "shipping_policy", "delivery_issues", "return_policy", "refund_policy", "damaged_wrong_products", "exchange_policy", "exchange_process", "exchange_availability", "cancellation_policy", "payment_methods", "payment_issues", "product_information", "warranty", "customer_support", "complaint_handling", "escalation_policy", "frequently_asked_questions"}
    present = {entry["topic"] for entry in metadata}
    return sorted(required - present)


def main():
    output_directory = project_root() / "data" / "knowledge_base"
    output_directory.mkdir(parents=True, exist_ok=True)
    metadata = create_knowledge_base(output_directory)
    missing_topics = validate_required_topics(metadata)
    if missing_topics:
        raise RuntimeError(f"Knowledge base is missing required topics: {missing_topics}")
    print(f"Knowledge base created for {COMPANY}.")
    print(f"Documents created: {len(metadata)}")
    print(f"Metadata file: {output_directory / 'metadata.json'}")
    print("Required topic validation: passed")


if __name__ == "__main__":
    main()
