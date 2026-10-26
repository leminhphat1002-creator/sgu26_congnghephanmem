from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.modules.presence.service import COOKIE_NAME, VisitorPresence


def test_presence_refreshes_existing_browser_and_expires_without_sleep():
    now = [0.0]
    presence = VisitorPresence(clock=lambda: now[0])
    first = presence.heartbeat(None)
    now[0] = 60
    second = presence.heartbeat(None)
    assert presence.heartbeat(first) == first
    now[0] = 120
    assert presence.snapshot()["active_visitors"] == 2
    now[0] = 179
    assert presence.heartbeat(second) == second
    now[0] = 180
    assert presence.snapshot()["active_visitors"] == 1
    now[0] = 299
    assert presence.snapshot()["active_visitors"] == 0
    # An expired cookie can rejoin, but its old identifier is no longer retained.
    assert presence.heartbeat(first) != first


def test_presence_limits_new_browsers_but_keeps_heartbeats_and_reclaims_expired_slots():
    now = [0.0]
    presence = VisitorPresence(clock=lambda: now[0], capacity=1)
    token = presence.heartbeat(None)
    with pytest.raises(OverflowError):
        presence.heartbeat(None)
    assert presence.heartbeat(token) == token
    now[0] = 120
    assert presence.heartbeat(None) != token


def test_simultaneous_tabs_share_one_visitor():
    presence = VisitorPresence()
    token = presence.heartbeat(None)
    with ThreadPoolExecutor(max_workers=8) as executor:
        assert set(executor.map(presence.heartbeat, [token] * 30)) == {token}
    assert presence.snapshot()["active_visitors"] == 1


def test_presence_secure_cookie_capacity_and_application_isolation():
    application = create_app()
    application.state.visitor_presence = VisitorPresence(capacity=1)
    with TestClient(application, base_url="https://testserver") as browser:
        response = browser.post("/api/presence/heartbeat")
        assert response.status_code == 204
        assert "Secure" in response.headers["set-cookie"]
        assert browser.cookies.get(COOKIE_NAME)
        assert browser.post("/api/presence/heartbeat").status_code == 204
        with TestClient(application) as other_browser:
            assert other_browser.post("/api/presence/heartbeat").status_code == 429
    assert create_app().state.visitor_presence.snapshot()["active_visitors"] == 0
