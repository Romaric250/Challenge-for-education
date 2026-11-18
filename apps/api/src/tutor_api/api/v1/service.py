from fastapi import APIRouter, Request

from tutor_api import __version__
from tutor_api.core.settings import Settings
from tutor_api.schemas.health import ServiceIdentity

router = APIRouter(tags=["service"])


@router.get("/service", response_model=ServiceIdentity, operation_id="getServiceIdentity")
async def get_service_identity(request: Request) -> ServiceIdentity:
    settings: Settings = request.app.state.settings
    return ServiceIdentity(name=settings.app_name, version=__version__, api_version="v1")
