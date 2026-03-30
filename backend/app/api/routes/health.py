from datetime import datetime, timezone

from fastapi import APIRouter, Depends

from app.api.dependencies import check_milvus, check_redis, get_mock_bss
from app.services.mock_bss import MockBSSService

router = APIRouter()


@router.get("/health")
async def health_check(
    redis_status: dict = Depends(check_redis),
    milvus_status: dict = Depends(check_milvus),
    mock_bss: MockBSSService = Depends(get_mock_bss),
):
    """
    Health check endpoint reporting overall status and service connectivity.
    Returns 200 with service details. Status is "healthy" if all services connected,
    "degraded" if some are down, "unhealthy" if critical services are down.
    """
    mock_status = {
        "status": "ready" if mock_bss.is_loaded else "not_loaded",
        "customers": mock_bss.customer_count,
        "tariffs": mock_bss.tariff_count,
    }

    services = {
        "redis": redis_status,
        "milvus": milvus_status,
        "mock_bss": mock_status,
    }

    # Determine overall status
    all_connected = all(
        s.get("status") in ("connected", "ready") for s in services.values()
    )
    any_connected = any(
        s.get("status") in ("connected", "ready") for s in services.values()
    )

    if all_connected:
        overall = "healthy"
    elif any_connected:
        overall = "degraded"
    else:
        overall = "unhealthy"

    return {
        "status": overall,
        "version": "0.1.0",
        "services": services,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
