"""Submit an authenticated email job and poll until it finishes or times out."""
import os
import sys
import time
import requests

BASE_URL=os.getenv("API_BASE_URL","http://127.0.0.1:8000")
def main():
    login=requests.post(f"{BASE_URL}/api/v1/auth/login",json={"email":"customer101@example.com","password":"TestPassword123!"},timeout=10)
    login.raise_for_status(); headers={"Authorization":"Bearer "+login.json()["access_token"]}
    queued=requests.post(f"{BASE_URL}/api/v1/emails/process",headers=headers,json={"subject":"Where is my order?","email_body":"Please tell me my order status.","order_id":"ORD00598"},timeout=10)
    queued.raise_for_status(); job_id=queued.json()["job_id"]; print(f"Job ID: {job_id}")
    for _ in range(30):
        job=requests.get(f"{BASE_URL}/api/v1/emails/jobs/{job_id}",headers=headers,timeout=10); job.raise_for_status(); data=job.json(); print(f"Status: {data['status']}")
        if data["status"] in {"completed","failed"}:
            print(f"Predicted category: {data.get('predicted_category')}"); print(f"Generated response: {data.get('response')}"); return
        time.sleep(2)
    print("Timed out waiting for the worker."); raise SystemExit(1)
if __name__=="__main__":
    try: main()
    except requests.RequestException as error: print(f"Async test failed: {error}"); sys.exit(1)
