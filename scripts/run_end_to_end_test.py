"""Exercise a running Docker deployment from login through completed job retrieval."""

import argparse
import os
import sys
import time

import requests


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default=os.getenv("API_BASE_URL", "http://localhost:8000"))
    parser.add_argument("--email", default=os.getenv("E2E_EMAIL"))
    parser.add_argument("--password", default=os.getenv("E2E_PASSWORD"))
    parser.add_argument("--order-id", default=os.getenv("E2E_ORDER_ID"))
    parser.add_argument("--timeout", type=float, default=float(os.getenv("E2E_TIMEOUT_SECONDS", "120")))
    args = parser.parse_args()
    if not all((args.email, args.password, args.order_id)):
        parser.error("Set E2E_EMAIL, E2E_PASSWORD, and E2E_ORDER_ID (or pass the matching options).")
    login = requests.post(f"{args.base_url}/api/v1/auth/login", json={"email": args.email, "password": args.password}, timeout=15)
    login.raise_for_status()
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    started = time.perf_counter()
    queued = requests.post(f"{args.base_url}/api/v1/emails/process", headers=headers, json={"subject": "Exchange request", "email_body": "I received the wrong size. Can I exchange it for another size?", "order_id": args.order_id}, timeout=15)
    api_seconds = time.perf_counter() - started
    queued.raise_for_status()
    job_id = queued.json()["job_id"]
    deadline = time.monotonic() + args.timeout
    result = None
    while time.monotonic() < deadline:
        result = requests.get(f"{args.base_url}/api/v1/emails/jobs/{job_id}", headers=headers, timeout=15)
        result.raise_for_status()
        body = result.json()
        if body["status"] in {"completed", "failed"}:
            break
        time.sleep(1)
    else:
        raise TimeoutError(f"Job {job_id} did not finish in {args.timeout:.0f} seconds.")
    print(f"Customer: {args.email}\nJob ID: {job_id}\nAPI response time: {api_seconds:.3f}s\nProcessing status: {body['status']}")
    print(f"Predicted category: {body.get('predicted_category')}\nProcessing time: {body.get('processing_time')}\nGenerated response: {body.get('response')}\nRetrieved sources: {body.get('sources')}")
    if body["status"] != "completed":
        sys.exit(1)


if __name__ == "__main__":
    main()
