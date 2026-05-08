"""
Service C — end of the forward chain, initiates the bi-directional return leg.

Call flow:  B → C → B (/ping)

GET /          status check
GET /hello     called by B: calls B's /ping (bi-directional), returns combined response
"""

import os
import requests
import uvicorn
from fastapi import FastAPI, HTTPException, Header
from typing import Annotated, Optional

app = FastAPI(title="Service C")

SERVICE_TOKEN = os.environ["SERVICE_TOKEN"]
SERVICE_B_URL = os.environ["SERVICE_B_URL"]   # vanity URL of Service B (return leg)
VERIFY_SSL    = os.environ.get("VERIFY_SSL", "true").lower() != "false"

_IDENTITY_TOKEN_URL = "http://localhost:8899/access-token"


def get_proxy_headers() -> dict:
    try:
        r = requests.get(_IDENTITY_TOKEN_URL, timeout=5)
        r.raise_for_status()
        token = r.text.strip()
        if token:
            return {"Authorization": f"Bearer {token}"}
    except Exception:
        pass
    return {"X-Domino-Api-Key": SERVICE_TOKEN}


def verify_token(x_service_token: Annotated[Optional[str], Header()] = None):
    if x_service_token != SERVICE_TOKEN:
        raise HTTPException(status_code=401, detail="Invalid or missing X-Service-Token")


def call_service(url: str, path: str) -> dict:
    headers = {
        **get_proxy_headers(),
        "X-Service-Token": SERVICE_TOKEN,
    }
    response = requests.get(f"{url}{path}", headers=headers, timeout=10, verify=VERIFY_SSL)
    response.raise_for_status()
    return response.json()


@app.get("/")
def root():
    return {"service": "C", "status": "ok"}


@app.get("/hello")
def hello(x_service_token: Annotated[Optional[str], Header()] = None):
    """Called by B. Calls B's /ping to demonstrate the C→B (bi-directional) leg."""
    verify_token(x_service_token)
    try:
        b_ping = call_service(SERVICE_B_URL, "/ping")
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Could not reach Service B (/ping): {e}")

    return {
        "from": "C",
        "message": "Hello from C",
        "bidirectional_ping": b_ping,
    }


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8888)))
