import asyncio
import os


def test_health_endpoint_direct() -> None:
    """Call the /health route function directly — no ASGI server needed."""
    os.environ.setdefault("MOCK_MODE", "true")
    from backend.api.main import health_check  # noqa: PLC0415

    result = asyncio.run(health_check())

    assert result["status"] == "ok"
    assert "version" in result
    assert isinstance(result["mock_mode"], bool)
