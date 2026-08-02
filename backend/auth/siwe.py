"""
Login pakai wallet crypto (SIWE-style — Sign-In With Ethereum), bukan
email/password. Flow-nya:

  1. Frontend minta nonce  -> GET /api/auth/nonce?wallet=0xabc...
  2. Frontend suruh wallet (Metamask/WalletConnect) tanda-tangan sebuah
     pesan yang isinya nonce itu (gratis, gak butuh gas, cuma signature).
  3. Frontend kirim signature -> POST /api/auth/verify
  4. Backend recover address dari signature, cocokkan sama wallet yang
     minta nonce tadi, kalau cocok -> user dianggap login, backend
     terbitkan JWT session sendiri (dipakai buat semua request API lain).

Ini metode login standar di dunia Web3 (dipakai OpenSea, Uniswap, dll),
gak perlu password, gak nyimpan private key apa pun di server.
"""
import secrets
import time
from datetime import datetime, timedelta, timezone

import jwt
from eth_account import Account
from eth_account.messages import encode_defunct
from fastapi import Depends, HTTPException, Header, status

from backend.config import settings
from backend.db.supabase_client import get_supabase

NONCE_TTL_SECONDS = 5 * 60


def _build_message(wallet: str, nonce: str) -> str:
    return (
        f"Trading Fellah wants you to sign in with your wallet.\n\n"
        f"Address: {wallet}\n"
        f"Nonce: {nonce}\n"
        f"Issued At: {datetime.now(timezone.utc).isoformat()}\n\n"
        f"This request will not trigger a blockchain transaction or cost any gas."
    )


def create_nonce(wallet_address: str) -> dict:
    wallet_address = wallet_address.lower()
    nonce = secrets.token_hex(16)
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=NONCE_TTL_SECONDS)

    sb = get_supabase()
    sb.table("auth_nonces").upsert({
        "wallet_address": wallet_address,
        "nonce": nonce,
        "expires_at": expires_at.isoformat(),
    }).execute()

    return {"wallet": wallet_address, "nonce": nonce, "message": _build_message(wallet_address, nonce)}


def verify_signature_and_login(wallet_address: str, signature: str) -> dict:
    wallet_address = wallet_address.lower()
    sb = get_supabase()

    row = sb.table("auth_nonces").select("*").eq("wallet_address", wallet_address).execute()
    if not row.data:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Nonce tidak ditemukan, minta ulang.")
    record = row.data[0]

    expires_at = datetime.fromisoformat(record["expires_at"])
    if datetime.now(timezone.utc) > expires_at:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Nonce kadaluarsa, minta ulang.")

    message = _build_message(wallet_address, record["nonce"])
    encoded = encode_defunct(text=message)
    try:
        recovered = Account.recover_message(encoded, signature=signature)
    except Exception:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Signature tidak valid.")

    if recovered.lower() != wallet_address:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Signature tidak cocok dengan wallet.")

    # nonce cuma sekali pakai
    sb.table("auth_nonces").delete().eq("wallet_address", wallet_address).execute()

    existing = sb.table("users").select("*").eq("wallet_address", wallet_address).execute()
    if existing.data:
        user = existing.data[0]
        sb.table("users").update({"last_login_at": datetime.now(timezone.utc).isoformat()}) \
            .eq("id", user["id"]).execute()
    else:
        created = sb.table("users").insert({
            "wallet_address": wallet_address,
            "last_login_at": datetime.now(timezone.utc).isoformat(),
        }).execute()
        user = created.data[0]
        # subscription kosong default, biar user langsung kelihatan di billing page
        sb.table("subscriptions").insert({
            "user_id": user["id"], "plan": "basic", "status": "inactive"
        }).execute()

    token = issue_jwt(user["id"], wallet_address)
    return {"token": token, "user": user}


def issue_jwt(user_id: str, wallet_address: str) -> str:
    payload = {
        "sub": user_id,
        "wallet": wallet_address,
        "iat": int(time.time()),
        "exp": datetime.now(timezone.utc) + timedelta(hours=settings.JWT_EXPIRE_HOURS),
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def decode_jwt(token: str) -> dict:
    try:
        return jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Session habis, login ulang.")
    except jwt.InvalidTokenError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token tidak valid.")


async def get_current_user(authorization: str = Header(default=None)) -> dict:
    """FastAPI dependency — pasang di route yang butuh login."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Belum login.")
    token = authorization.removeprefix("Bearer ").strip()
    payload = decode_jwt(token)

    sb = get_supabase()
    res = sb.table("users").select("*").eq("id", payload["sub"]).execute()
    if not res.data:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "User tidak ditemukan.")
    return res.data[0]


async def require_active_subscription(user: dict = Depends(get_current_user)) -> dict:
    """Dependency tambahan buat route yang butuh membership aktif (misal: buka order)."""
    sb = get_supabase()
    res = sb.table("subscriptions").select("*").eq("user_id", user["id"]).execute()
    sub = res.data[0] if res.data else None
    if not sub or sub["status"] != "active":
        raise HTTPException(
            status.HTTP_402_PAYMENT_REQUIRED,
            "Membership belum aktif. Silakan berlangganan dulu di halaman Billing.",
        )
    return user
