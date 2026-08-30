"""Send one manual request to a running local FastAPI server."""

import requests


def main():
    try:
        response = requests.post("http://127.0.0.1:8000/api/v1/emails/process", json={
            "subject": "Need a different size",
            "email_body": "I received size 8 but I need size 9. Can I exchange it?",
        }, timeout=180)
    except requests.ConnectionError:
        print("Could not reach the API at http://127.0.0.1:8000.")
        print("Start the server in another terminal: uvicorn src.api.main:app --reload")
        return
    print(f"HTTP Status: {response.status_code}")
    data = response.json()
    print(f"Predicted Category: {data.get('predicted_category')}")
    print(f"Response: {data.get('response')}")
    print(f"Sources: {data.get('sources')}")


if __name__ == "__main__":
    main()
