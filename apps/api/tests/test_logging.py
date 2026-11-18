from tutor_api.core.logging import is_sensitive_key, redact_sensitive


def test_redacts_credentials_and_nested_headers() -> None:
    event = redact_sensitive(
        None,
        "info",
        {
            "database_url": "postgresql://tutor:secret@localhost/tutor",
            "path": "/health/live",
            "headers": {"Authorization": "Bearer secret", "X-Request-ID": "req-12345678"},
        },
    )
    assert event["database_url"] == "[redacted]"
    assert event["path"] == "/health/live"
    headers = event["headers"]
    assert isinstance(headers, dict)
    assert headers["Authorization"] == "[redacted]"
    assert headers["X-Request-ID"] == "req-12345678"


def test_sensitive_key_names() -> None:
    assert is_sensitive_key("Refresh-Token")
    assert is_sensitive_key("password")
    assert not is_sensitive_key("request_id")
