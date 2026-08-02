"""
Jembatan ke MT5 lewat MetaApi.cloud (https://metaapi.cloud).

KENAPA METAAPI, BUKAN LIBRARY `MetaTrader5` RESMI?
Library python `MetaTrader5` resmi cuma bisa jalan bareng terminal MT5 yang
lagi kebuka di Windows yang sama, dan cuma pegang SATU koneksi akun aktif per
proses. Itu gak cocok buat SaaS multi-tenant (banyak user, banyak akun,
jalan bareng, di server Linux). MetaApi nyediain REST/WebSocket API ke MT5
APAPUN brokernya, tanpa perlu install terminal — cocok buat use-case ini.
Ini layanan pihak ketiga berbayar (ada free tier terbatas), bukan produk
Anthropic. Kalau di masa depan mau pindah provider lain (misal broker kamu
punya Manager API sendiri), tinggal ganti isi class ini — router/service
lain di atasnya gak perlu berubah karena kontraknya (method signature) sama.

SDK method di bawah ini mengikuti pola resmi metaapi-cloud-sdk python
(https://metaapi.cloud/docs/client/python/). Cek versi terbaru sebelum
deploy production karena SDK third-party ini kadang berubah antar rilis.
"""
import logging
from typing import Optional

from metaapi_cloud_sdk import MetaApi

from backend.config import settings
from backend.services.encryption import get_cipher

logger = logging.getLogger(__name__)

_api: Optional[MetaApi] = None
_connection_cache: dict = {}  # metaapi_account_id -> streaming connection (RPC)


def _client() -> MetaApi:
    global _api
    if _api is None:
        if not settings.METAAPI_TOKEN:
            raise RuntimeError("METAAPI_TOKEN belum di-set di .env (daftar di https://metaapi.cloud).")
        _api = MetaApi(settings.METAAPI_TOKEN)
    return _api


async def provision_account(mt5_login: str, password: str, server: str, label: str, is_live: bool) -> str:
    """
    Daftarin akun MT5 user ke MetaApi (sekali per akun). Return metaapi_account_id
    yang disimpan di tabel mt5_accounts dan dipakai buat semua operasi berikutnya.
    """
    api = _client()
    account = await api.metatrader_account_api.create_account({
        "name": label,
        "type": "cloud",
        "login": mt5_login,
        "password": password,
        "server": server,
        "platform": "mt5",
        "magic": 20260001,
    })
    await account.deploy()
    await account.wait_connected()
    return account.id


async def _get_connection(metaapi_account_id: str):
    if metaapi_account_id in _connection_cache:
        return _connection_cache[metaapi_account_id]

    api = _client()
    account = await api.metatrader_account_api.get_account(metaapi_account_id)
    connection = account.get_rpc_connection()
    await connection.connect()
    await connection.wait_synchronized()
    _connection_cache[metaapi_account_id] = connection
    return connection


async def get_account_info(metaapi_account_id: str) -> dict:
    """Balance, equity, margin, free margin, margin level — buat dashboard."""
    conn = await _get_connection(metaapi_account_id)
    info = await conn.get_account_information()
    return {
        "balance": info.get("balance"),
        "equity": info.get("equity"),
        "margin": info.get("margin"),
        "free_margin": info.get("freeMargin"),
        "margin_level": info.get("marginLevel"),
        "currency": info.get("currency"),
        "leverage": info.get("leverage"),
        "server": info.get("server"),
        "name": info.get("name"),
    }


async def get_open_positions(metaapi_account_id: str) -> list[dict]:
    conn = await _get_connection(metaapi_account_id)
    positions = await conn.get_positions()
    return [{
        "ticket": p.get("id"),
        "symbol": p.get("symbol"),
        "direction": "LONG" if p.get("type") == "POSITION_TYPE_BUY" else "SHORT",
        "volume": p.get("volume"),
        "open_price": p.get("openPrice"),
        "current_price": p.get("currentPrice"),
        "stop_loss": p.get("stopLoss"),
        "take_profit": p.get("takeProfit"),
        "profit": p.get("profit"),
        "swap": p.get("swap"),
        "opened_at": p.get("time"),
        "comment": p.get("comment"),
    } for p in positions]


async def open_market_order(metaapi_account_id: str, symbol: str, direction: str,
                             volume: float, stop_loss: float | None = None,
                             take_profit: float | None = None, comment: str = "") -> dict:
    conn = await _get_connection(metaapi_account_id)
    if direction.upper() == "LONG":
        result = await conn.create_market_buy_order(symbol, volume, stop_loss, take_profit,
                                                      {"comment": comment[:26]})
    else:
        result = await conn.create_market_sell_order(symbol, volume, stop_loss, take_profit,
                                                       {"comment": comment[:26]})
    return {
        "ticket": result.get("orderId") or result.get("positionId"),
        "price": result.get("price"),
        "raw": result,
    }


async def close_position(metaapi_account_id: str, ticket: str) -> dict:
    conn = await _get_connection(metaapi_account_id)
    result = await conn.close_position(ticket)
    return {"ticket": ticket, "raw": result}


async def modify_position(metaapi_account_id: str, ticket: str,
                           stop_loss: float | None = None, take_profit: float | None = None) -> dict:
    conn = await _get_connection(metaapi_account_id)
    result = await conn.modify_position(ticket, stop_loss, take_profit)
    return {"ticket": ticket, "raw": result}


async def get_historical_candles(metaapi_account_id: str, symbol: str,
                                  timeframe: str, start_time, limit: int = 1000) -> list[dict]:
    """Buat backtest engine & swing/order-block detection."""
    conn = await _get_connection(metaapi_account_id)
    candles = await conn.get_historical_candles(symbol, timeframe, start_time, limit)
    return candles


def decrypt_password(encrypted_password: str) -> str:
    return get_cipher().decrypt(encrypted_password)
