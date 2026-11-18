PROBLEM_MEDIA_TYPE = "application/problem+json"

_HTTP_CODES = {
    400: "bad_request",
    401: "unauthorized",
    403: "forbidden",
    404: "not_found",
    405: "method_not_allowed",
    409: "conflict",
    413: "payload_too_large",
    415: "unsupported_media_type",
    422: "validation_error",
    429: "rate_limited",
    500: "internal_error",
    503: "not_ready",
}


class DomainError(Exception):
    def __init__(self, *, status_code: int, code: str, title: str, detail: str) -> None:
        super().__init__(detail)
        self.status_code = status_code
        self.code = code
        self.title = title
        self.detail = detail


def http_error_code(status_code: int) -> str:
    return _HTTP_CODES.get(status_code, "http_error")


def problem_body(
    *,
    status_code: int,
    code: str,
    title: str,
    detail: str,
    instance: str,
) -> dict[str, object]:
    return {
        "type": "about:blank",
        "title": title,
        "status": status_code,
        "detail": detail,
        "code": code,
        "instance": instance,
    }
