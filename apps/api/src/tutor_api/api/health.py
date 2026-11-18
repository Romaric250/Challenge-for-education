from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from tutor_api.core.readiness import build_readiness_report
from tutor_api.core.settings import Settings
from tutor_api.schemas.health import LiveStatus, ReadinessReport

router = APIRouter(tags=["health"])


@router.get("/health/live", response_model=LiveStatus, operation_id="getLiveness")
async def get_liveness() -> LiveStatus:
    return LiveStatus(status="live")


@router.get(
    "/health/ready",
    response_model=ReadinessReport,
    operation_id="getReadiness",
    responses={503: {"model": ReadinessReport}},
)
async def get_readiness(request: Request) -> JSONResponse:
    settings: Settings = request.app.state.settings
    report = await build_readiness_report(request.app.state.engine, settings)
    status_code = 200 if report.status == "ready" else 503
    return JSONResponse(status_code=status_code, content=report.model_dump())
