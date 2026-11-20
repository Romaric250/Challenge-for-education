from fastapi import APIRouter

from tutor_api.api.v1.accounts import router as accounts_router
from tutor_api.api.v1.admin import router as admin_router
from tutor_api.api.v1.auth import router as auth_router
from tutor_api.api.v1.documents import router as documents_router
from tutor_api.api.v1.learning import router as learning_router
from tutor_api.api.v1.service import router as service_router

router = APIRouter()
router.include_router(service_router)
router.include_router(auth_router)
router.include_router(accounts_router)
router.include_router(documents_router)
router.include_router(learning_router)
router.include_router(admin_router)
