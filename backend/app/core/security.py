from typing import List, Optional
from fastapi import Header, HTTPException, Security, status
from fastapi.security.api_key import APIKeyHeader

from app.core.config import settings

API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)

# Role & scope definitions
VALID_API_KEYS = {
    settings.DEFAULT_API_KEY: {
        "client_id": "ssb-primary-console",
        "role": "officer",
        "scopes": ["officer:screen", "officer:review", "admin:audit"],
    },
    "ssb-officer-key-2026": {
        "client_id": "ssb-checkpoint-officer",
        "role": "officer",
        "scopes": ["officer:screen", "officer:review"],
    },
    "ssb-auditor-key-2026": {
        "client_id": "ssb-audit-division",
        "role": "auditor",
        "scopes": ["admin:audit"],
    }
}


async def get_current_client(api_key: Optional[str] = Security(API_KEY_HEADER)):
    """Authenticate incoming request using X-API-Key header."""
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API Key header: X-API-Key",
            headers={"WWW-Authenticate": "ApiKey"},
        )
    
    client = VALID_API_KEYS.get(api_key)
    if not client:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid or revoked API Key",
        )
    
    return client


def require_scope(required_scope: str):
    """Enforce specific permission scope on endpoint access."""
    async def scope_checker(client: dict = Security(get_current_client)):
        scopes: List[str] = client.get("scopes", [])
        if required_scope not in scopes:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied: Requires scope '{required_scope}'",
            )
        return client
    return scope_checker
