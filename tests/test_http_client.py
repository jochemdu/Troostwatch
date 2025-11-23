import time

from requests import Response

from troostwatch.http_client import TroostwatchHttpClient


def _make_response(text: str, headers: dict | None = None) -> Response:
    resp = Response()
    resp._content = text.encode("utf-8")
    resp.status_code = 200
    if headers:
        resp.headers.update(headers)
    return resp


def test_extract_csrf_from_meta() -> None:
    client = TroostwatchHttpClient(session_timeout_seconds=60)
    response = _make_response('<meta name="csrf-token" content="abc123" />')
    assert client._extract_csrf(response) == "abc123"


def test_store_and_restore_session(tmp_path) -> None:
    client = TroostwatchHttpClient(session_timeout_seconds=60)
    client.csrf_token = "token"
    client.last_authenticated = time.time()
    client.session.cookies.set("sessid", "cookie123")

    path = tmp_path / "session.json"
    client._store_session(path)

    loaded = client._load_session(path)
    assert loaded is not None
    assert not loaded.is_expired(60)

    restored = TroostwatchHttpClient(session_timeout_seconds=60)
    restored._restore_from_tokens(loaded)
    assert restored.csrf_token == "token"
    assert restored.session.cookies.get("sessid") == "cookie123"
