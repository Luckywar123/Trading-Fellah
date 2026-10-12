import os

os.environ.setdefault("ENV", "test")
os.environ.setdefault("FRONTEND_ORIGIN", "https://trading-fellah.vercel.app")

import asyncio

import pytest
from fastapi.testclient import TestClient

from backend.config import Settings
from backend.main import app
from backend.services import mt5_service
from backend.services.ai_agent import rule_based_news_sentiment

client = TestClient(app)


def test_health():
    r = client.get("/api/health")
    assert r.status_code == 200 and r.json()["status"] == "online"


def test_cors_allows_frontend_origin():
    r = client.options(
        "/api/health",
        headers={"Origin": "https://trading-fellah.vercel.app", "Access-Control-Request-Method": "GET"},
    )
    assert r.headers.get("access-control-allow-origin") == "https://trading-fellah.vercel.app"


def test_cors_blocks_unknown_origin():
    r = client.options(
        "/api/health",
        headers={"Origin": "https://evil.example", "Access-Control-Request-Method": "GET"},
    )
    assert "access-control-allow-origin" not in r.headers


def test_chat_requires_login():
    assert client.post("/api/ai/chat", json={"message": "halo"}).status_code == 401


def test_production_validation_flags_default_secrets():
    s = Settings(ENV="production", _env_file=None)
    assert len(s.validate_for_production()) == 3
    ok = Settings(ENV="production", JWT_SECRET="x" * 40, CREDENTIAL_ENCRYPTION_KEY="k",
                  SUPABASE_URL="u", SUPABASE_SERVICE_ROLE_KEY="k", _env_file=None)
    assert ok.validate_for_production() == []


def test_rule_based_sentiment_fallback():
    r = rule_based_news_sentiment("US CPI beats forecast, dollar rally")
    assert r["sentiment"] == "buy" and r["impact_level"] == "high"


def test_read_ops_retry_but_writes_do_not():
    calls = {"read": 0, "write": 0}

    @mt5_service.resilient(retries=2)
    async def read(acc):
        calls["read"] += 1
        if calls["read"] < 3:
            raise ConnectionError("boom")
        return "ok"

    @mt5_service.resilient(retries=0)
    async def write(acc):
        calls["write"] += 1
        raise ConnectionError("boom")

    async def fast_sleep(_):  # jangan nunggu backoff beneran di test
        return None

    orig = mt5_service.asyncio.sleep
    mt5_service.asyncio.sleep = fast_sleep
    try:
        assert asyncio.run(read("acc-r")) == "ok" and calls["read"] == 3
        with pytest.raises(ConnectionError):
            asyncio.run(write("acc-w"))
        assert calls["write"] == 1          # TIDAK di-retry -> gak ada order dobel
    finally:
        mt5_service.asyncio.sleep = orig


def test_circuit_breaker_opens():
    @mt5_service.resilient(retries=0)
    async def flaky(acc):
        raise ConnectionError("down")

    for _ in range(5):
        with pytest.raises(ConnectionError):
            asyncio.run(flaky("acc-cb"))
    with pytest.raises(RuntimeError, match="sementara dihentikan"):
        asyncio.run(flaky("acc-cb"))
