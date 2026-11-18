from fastapi import APIRouter

from tutor_api.api.v1.service import router as service_router

router = APIRouter()
router.include_router(service_router)
