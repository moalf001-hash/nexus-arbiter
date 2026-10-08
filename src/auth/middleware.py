from fastapi import Security, HTTPException, status
from fastapi.security import APIKeyHeader
from src.storage.database import StorageManager

API_KEY_HEADER = APIKeyHeader(name="X-Nexus-API-Key", auto_error=False)

async def verify_tenant_access(api_key: str = Security(API_KEY_HEADER)):
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed: Missing X-Nexus-API-Key header."
        )

    tenant = StorageManager.authenticate_api_key(api_key)
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed: Invalid or inactive API key."
        )

    # استهلاك ذري يمنع هجمات التزامن
    is_allowed = StorageManager.increment_and_check_quota(tenant["tenant_id"])
    if not is_allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Monthly quota exceeded ({tenant['monthly_limit']}/{tenant['monthly_limit']}). Please upgrade your tier."
        )

    return tenant