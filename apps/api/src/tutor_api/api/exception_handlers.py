from http import HTTPStatus

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException

from tutor_api.core.errors import PROBLEM_MEDIA_TYPE, DomainError, http_error_code, problem_body
from tutor_api.core.logging import get_logger

_log = get_logger(__name__)


def problem_response(
    *,
    status_code: int,
    code: str,
    title: str,
    detail: str,
    instance: str,
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content=problem_body(
            status_code=status_code,
            code=code,
            title=title,
            detail=detail,
            instance=instance,
        ),
        media_type=PROBLEM_MEDIA_TYPE,
    )


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(DomainError)
    async def handle_domain_error(request: Request, exc: DomainError) -> JSONResponse:
        return problem_response(
            status_code=exc.status_code,
            code=exc.code,
            title=exc.title,
            detail=exc.detail,
            instance=request.url.path,
        )

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(
        request: Request,
        exc: RequestValidationError,
    ) -> JSONResponse:
        detail = "The request is invalid."
        errors = exc.errors()
        if errors:
            message = errors[0].get("msg")
            if isinstance(message, str) and message:
                detail = message.removeprefix("Value error, ")
        return problem_response(
            status_code=422,
            code="validation_error",
            title="Validation failed",
            detail=detail,
            instance=request.url.path,
        )

    @app.exception_handler(HTTPException)
    async def handle_http_exception(request: Request, exc: HTTPException) -> JSONResponse:
        detail = exc.detail if isinstance(exc.detail, str) else "The request could not be completed."
        try:
            title = HTTPStatus(exc.status_code).phrase
        except ValueError:
            title = "Error"
        return problem_response(
            status_code=exc.status_code,
            code=http_error_code(exc.status_code),
            title=title,
            detail=detail,
            instance=request.url.path,
        )

    @app.exception_handler(Exception)
    async def handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
        _log.exception("unhandled_error", path=request.url.path, error_type=exc.__class__.__name__)
        return problem_response(
            status_code=500,
            code="internal_error",
            title="Internal error",
            detail="The request could not be completed.",
            instance=request.url.path,
        )
