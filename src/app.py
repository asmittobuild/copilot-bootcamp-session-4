"""
Slalom Capabilities Management System API

A FastAPI application that enables Slalom consultants to register their
capabilities and manage consulting expertise across the organization.
"""

import base64
import hashlib
import hmac
import json
import os
import time
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from pydantic import BaseModel

app = FastAPI(title="Slalom Capabilities Management API",
              description="API for managing consulting capabilities and consultant expertise")

# Mount the static files directory
current_dir = Path(__file__).parent
app.mount("/static", StaticFiles(directory=os.path.join(Path(__file__).parent,
          "static")), name="static")

AUTH_FILE_PATH = current_dir / "practice_leads.json"
TOKEN_SECRET = os.getenv("TOKEN_SECRET", "dev-only-change-me")
TOKEN_EXPIRES_SECONDS = int(os.getenv("TOKEN_EXPIRES_SECONDS", "28800"))


class LoginRequest(BaseModel):
    username: str
    password: str

# In-memory capabilities database
capabilities = {
    "Cloud Architecture": {
        "description": "Design and implement scalable cloud solutions using AWS, Azure, and GCP",
        "practice_area": "Technology",
        "skill_levels": ["Emerging", "Proficient", "Advanced", "Expert"],
        "certifications": ["AWS Solutions Architect", "Azure Architect Expert"],
        "industry_verticals": ["Healthcare", "Financial Services", "Retail"],
        "capacity": 40,  # hours per week available across team
        "consultants": ["alice.smith@slalom.com", "bob.johnson@slalom.com"]
    },
    "Data Analytics": {
        "description": "Advanced data analysis, visualization, and machine learning solutions",
        "practice_area": "Technology", 
        "skill_levels": ["Emerging", "Proficient", "Advanced", "Expert"],
        "certifications": ["Tableau Desktop Specialist", "Power BI Expert", "Google Analytics"],
        "industry_verticals": ["Retail", "Healthcare", "Manufacturing"],
        "capacity": 35,
        "consultants": ["emma.davis@slalom.com", "sophia.wilson@slalom.com"]
    },
    "DevOps Engineering": {
        "description": "CI/CD pipeline design, infrastructure automation, and containerization",
        "practice_area": "Technology",
        "skill_levels": ["Emerging", "Proficient", "Advanced", "Expert"], 
        "certifications": ["Docker Certified Associate", "Kubernetes Admin", "Jenkins Certified"],
        "industry_verticals": ["Technology", "Financial Services"],
        "capacity": 30,
        "consultants": ["john.brown@slalom.com", "olivia.taylor@slalom.com"]
    },
    "Digital Strategy": {
        "description": "Digital transformation planning and strategic technology roadmaps",
        "practice_area": "Strategy",
        "skill_levels": ["Emerging", "Proficient", "Advanced", "Expert"],
        "certifications": ["Digital Transformation Certificate", "Agile Certified Practitioner"],
        "industry_verticals": ["Healthcare", "Financial Services", "Government"],
        "capacity": 25,
        "consultants": ["liam.anderson@slalom.com", "noah.martinez@slalom.com"]
    },
    "Change Management": {
        "description": "Organizational change leadership and adoption strategies",
        "practice_area": "Operations",
        "skill_levels": ["Emerging", "Proficient", "Advanced", "Expert"],
        "certifications": ["Prosci Certified", "Lean Six Sigma Black Belt"],
        "industry_verticals": ["Healthcare", "Manufacturing", "Government"],
        "capacity": 20,
        "consultants": ["ava.garcia@slalom.com", "mia.rodriguez@slalom.com"]
    },
    "UX/UI Design": {
        "description": "User experience design and digital product innovation",
        "practice_area": "Technology",
        "skill_levels": ["Emerging", "Proficient", "Advanced", "Expert"],
        "certifications": ["Adobe Certified Expert", "Google UX Design Certificate"],
        "industry_verticals": ["Retail", "Healthcare", "Technology"],
        "capacity": 30,
        "consultants": ["amelia.lee@slalom.com", "harper.white@slalom.com"]
    },
    "Cybersecurity": {
        "description": "Information security strategy, risk assessment, and compliance",
        "practice_area": "Technology",
        "skill_levels": ["Emerging", "Proficient", "Advanced", "Expert"],
        "certifications": ["CISSP", "CISM", "CompTIA Security+"],
        "industry_verticals": ["Financial Services", "Healthcare", "Government"],
        "capacity": 25,
        "consultants": ["ella.clark@slalom.com", "scarlett.lewis@slalom.com"]
    },
    "Business Intelligence": {
        "description": "Enterprise reporting, data warehousing, and business analytics",
        "practice_area": "Technology",
        "skill_levels": ["Emerging", "Proficient", "Advanced", "Expert"],
        "certifications": ["Microsoft BI Certification", "Qlik Sense Certified"],
        "industry_verticals": ["Retail", "Manufacturing", "Financial Services"],
        "capacity": 35,
        "consultants": ["james.walker@slalom.com", "benjamin.hall@slalom.com"]
    },
    "Agile Coaching": {
        "description": "Agile transformation and team coaching for scaled delivery",
        "practice_area": "Operations",
        "skill_levels": ["Emerging", "Proficient", "Advanced", "Expert"],
        "certifications": ["Certified Scrum Master", "SAFe Agilist", "ICAgile Certified"],
        "industry_verticals": ["Technology", "Financial Services", "Healthcare"],
        "capacity": 20,
        "consultants": ["charlotte.young@slalom.com", "henry.king@slalom.com"]
    }
}

# In-memory audit events
audit_logs: list[dict[str, Any]] = []


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64url_decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)


def _hash_password(password: str, salt: str) -> str:
    combined = f"{salt}:{password}".encode("utf-8")
    return hashlib.sha256(combined).hexdigest()


def _load_auth_users() -> dict[str, dict[str, Any]]:
    if not AUTH_FILE_PATH.exists():
        raise RuntimeError("practice_leads.json was not found")

    with AUTH_FILE_PATH.open("r", encoding="utf-8") as credentials_file:
        raw_data = json.load(credentials_file)

    users = raw_data.get("users", [])
    return {user["username"]: user for user in users}


def _public_user(user: dict[str, Any]) -> dict[str, Any]:
    return {
        "username": user["username"],
        "display_name": user.get("display_name", user["username"]),
        "email": user.get("email", ""),
        "role": user.get("role", "consultant"),
        "practice_areas": user.get("practice_areas", []),
        "permissions": user.get("permissions", [])
    }


def _create_access_token(user: dict[str, Any]) -> str:
    header = {"alg": "HS256", "typ": "JWT"}
    payload = {
        "sub": user["username"],
        "role": user.get("role", "consultant"),
        "email": user.get("email", ""),
        "exp": int(time.time()) + TOKEN_EXPIRES_SECONDS,
    }

    encoded_header = _b64url_encode(json.dumps(header, separators=(",", ":")).encode("utf-8"))
    encoded_payload = _b64url_encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    signing_input = f"{encoded_header}.{encoded_payload}".encode("utf-8")
    signature = hmac.new(TOKEN_SECRET.encode("utf-8"), signing_input, hashlib.sha256).digest()
    encoded_signature = _b64url_encode(signature)
    return f"{encoded_header}.{encoded_payload}.{encoded_signature}"


def _decode_access_token(token: str) -> dict[str, Any]:
    try:
        encoded_header, encoded_payload, encoded_signature = token.split(".")
    except ValueError as exc:
        raise HTTPException(status_code=401, detail="Malformed token") from exc

    signing_input = f"{encoded_header}.{encoded_payload}".encode("utf-8")
    expected_signature = hmac.new(
        TOKEN_SECRET.encode("utf-8"),
        signing_input,
        hashlib.sha256,
    ).digest()

    provided_signature = _b64url_decode(encoded_signature)
    if not hmac.compare_digest(expected_signature, provided_signature):
        raise HTTPException(status_code=401, detail="Invalid token signature")

    payload = json.loads(_b64url_decode(encoded_payload).decode("utf-8"))
    if payload.get("exp", 0) < int(time.time()):
        raise HTTPException(status_code=401, detail="Token has expired")

    return payload


def _extract_token(authorization: Optional[str]) -> Optional[str]:
    if not authorization:
        return None
    if not authorization.startswith("Bearer "):
        return None
    return authorization.split(" ", maxsplit=1)[1]


def _ensure_capability(capability_name: str) -> dict[str, Any]:
    if capability_name not in capabilities:
        raise HTTPException(status_code=404, detail="Capability not found")
    return capabilities[capability_name]


def _append_audit(action: str, capability_name: str, target_email: str, actor: dict[str, Any]) -> None:
    audit_logs.insert(0, {
        "action": action,
        "capability": capability_name,
        "target_email": target_email,
        "actor": actor.get("username"),
        "actor_role": actor.get("role"),
        "timestamp": int(time.time()),
    })


auth_users = _load_auth_users()


def get_current_user(authorization: Optional[str] = Header(default=None)) -> dict[str, Any]:
    token = _extract_token(authorization)
    if not token:
        raise HTTPException(status_code=401, detail="Authentication required")

    payload = _decode_access_token(token)
    username = payload.get("sub")
    user = auth_users.get(username)
    if not user:
        raise HTTPException(status_code=401, detail="Unknown user")
    return user


def get_optional_user(authorization: Optional[str] = Header(default=None)) -> Optional[dict[str, Any]]:
    token = _extract_token(authorization)
    if not token:
        return None
    try:
        payload = _decode_access_token(token)
    except HTTPException:
        return None
    return auth_users.get(payload.get("sub"))


def require_practice_lead(current_user: dict[str, Any] = Depends(get_current_user)) -> dict[str, Any]:
    if current_user.get("role") != "practice_lead":
        raise HTTPException(status_code=403, detail="Practice lead role required")
    return current_user


@app.post("/auth/login")
def login(payload: LoginRequest):
    user = auth_users.get(payload.username)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid username or password")

    expected_hash = _hash_password(payload.password, user["salt"])
    if not hmac.compare_digest(expected_hash, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid username or password")

    return {
        "access_token": _create_access_token(user),
        "token_type": "bearer",
        "user": _public_user(user),
    }


@app.get("/auth/me")
def auth_me(current_user: dict[str, Any] = Depends(get_current_user)):
    return {"user": _public_user(current_user)}


@app.get("/")
def root():
    return RedirectResponse(url="/static/index.html")


@app.get("/capabilities")
def get_capabilities(current_user: Optional[dict[str, Any]] = Depends(get_optional_user)):
    response: dict[str, Any] = {}
    is_practice_lead = bool(current_user and current_user.get("role") == "practice_lead")

    for capability_name, details in capabilities.items():
        capability_copy = {
            "description": details["description"],
            "practice_area": details["practice_area"],
            "skill_levels": details["skill_levels"],
            "certifications": details["certifications"],
            "industry_verticals": details["industry_verticals"],
            "capacity": details["capacity"],
            "consultants": details["consultants"],
        }

        pending_requests = details.get("pending_requests", [])
        if is_practice_lead:
            capability_copy["pending_requests"] = pending_requests
        else:
            capability_copy["pending_request_count"] = len(pending_requests)

        response[capability_name] = capability_copy

    return response


@app.post("/capabilities/{capability_name}/register")
def register_for_capability(
    capability_name: str,
    email: str,
    current_user: dict[str, Any] = Depends(get_current_user),
):
    """Register a consultant for a capability"""
    capability = _ensure_capability(capability_name)
    pending_requests = capability.setdefault("pending_requests", [])

    if email in capability["consultants"]:
        raise HTTPException(
            status_code=400,
            detail="Consultant is already registered for this capability"
        )

    if current_user.get("role") == "practice_lead":
        capability["consultants"].append(email)
        if email in pending_requests:
            pending_requests.remove(email)
        _append_audit("register", capability_name, email, current_user)
        return {"message": f"Registered {email} for {capability_name}"}

    if current_user.get("role") == "consultant":
        if email.lower() != current_user.get("email", "").lower():
            raise HTTPException(status_code=403, detail="Consultants can only register themselves")

        if email in pending_requests:
            raise HTTPException(status_code=400, detail="Registration request is already pending")

        pending_requests.append(email)
        _append_audit("request_registration", capability_name, email, current_user)
        return {
            "message": (
                f"Submitted registration request for {email} on {capability_name}. "
                "A practice lead must approve it."
            )
        }

    raise HTTPException(status_code=403, detail="Unknown role")


@app.post("/capabilities/{capability_name}/approve")
def approve_registration(
    capability_name: str,
    email: str,
    current_user: dict[str, Any] = Depends(require_practice_lead),
):
    """Approve a consultant's registration request for a capability"""
    capability = _ensure_capability(capability_name)
    pending_requests = capability.setdefault("pending_requests", [])

    if email in capability["consultants"]:
        raise HTTPException(status_code=400, detail="Consultant is already registered")

    if email not in pending_requests:
        raise HTTPException(status_code=404, detail="No pending registration found for this consultant")

    pending_requests.remove(email)
    capability["consultants"].append(email)
    _append_audit("approve_registration", capability_name, email, current_user)
    return {"message": f"Approved {email} for {capability_name}"}


@app.delete("/capabilities/{capability_name}/unregister")
def unregister_from_capability(
    capability_name: str,
    email: str,
    current_user: dict[str, Any] = Depends(require_practice_lead),
):
    """Unregister a consultant from a capability"""
    capability = _ensure_capability(capability_name)

    if email not in capability["consultants"]:
        raise HTTPException(
            status_code=400,
            detail="Consultant is not registered for this capability"
        )

    capability["consultants"].remove(email)
    _append_audit("unregister", capability_name, email, current_user)
    return {"message": f"Unregistered {email} from {capability_name}"}


@app.get("/audit-logs")
def get_audit_logs(current_user: dict[str, Any] = Depends(require_practice_lead)):
    _ = current_user
    return {"items": audit_logs[:200]}
