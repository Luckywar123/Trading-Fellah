"""
Pembayaran membership pakai crypto lewat NOWPayments (https://nowpayments.io).

Kenapa NOWPayments dan bukan nerima langsung ke wallet kita terus mantau
blockchain manual? Karena mantau banyak chain/koin manual itu pekerjaan
infra sendiri (node, konfirmasi block, reorg, dst) — riskan salah kalau
dibikin buru-buru. NOWPayments nanganin itu semua dan kasih kita 1 webhook
(IPN) pas pembayaran confirmed. Login wallet (SIWE, lihat auth/siwe.py) itu
hal BEDA — itu buat identitas/login, ini buat nagih/nerima duit membership.

Kalau nanti mau terima langsung on-chain tanpa perantara, service ini bisa
diganti (interface-nya sama: create_invoice + handle webhook) tanpa ubah
router atau frontend.
"""
import hashlib
import hmac
import json
from datetime import datetime, timedelta, timezone

import httpx

from backend.config import settings
from backend.db.supabase_client import get_supabase

PLAN_PRICES = {
    "basic": settings.PLAN_PRICE_BASIC,
    "pro": settings.PLAN_PRICE_PRO,
    "elite": settings.PLAN_PRICE_ELITE,
}


async def create_invoice(user_id: str, plan: str, success_url: str, cancel_url: str) -> dict:
    if plan not in PLAN_PRICES:
        raise ValueError(f"Plan tidak dikenal: {plan}")
    if not settings.NOWPAYMENTS_API_KEY:
        raise RuntimeError("NOWPAYMENTS_API_KEY belum di-set di .env (daftar di nowpayments.io).")

    order_id = f"{user_id}:{plan}:{int(datetime.now(timezone.utc).timestamp())}"
    payload = {
        "price_amount": PLAN_PRICES[plan],
        "price_currency": "usd",
        "order_id": order_id,
        "order_description": f"Trading Fellah — {plan.upper()} membership (1 bulan)",
        "ipn_callback_url": f"{settings.FRONTEND_ORIGIN.replace('5173', '8000')}/api/billing/webhook",
        "success_url": success_url,
        "cancel_url": cancel_url,
    }

    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(
            f"{settings.NOWPAYMENTS_BASE_URL}/invoice",
            json=payload,
            headers={"x-api-key": settings.NOWPAYMENTS_API_KEY},
        )
        resp.raise_for_status()
        invoice = resp.json()

    sb = get_supabase()
    sb.table("payments").insert({
        "user_id": user_id,
        "provider": "nowpayments",
        "provider_payment_id": invoice.get("id"),
        "plan": plan,
        "amount_usd": PLAN_PRICES[plan],
        "status": "waiting",
        "raw_payload": invoice,
    }).execute()

    return {"invoice_url": invoice.get("invoice_url"), "invoice_id": invoice.get("id")}


def _verify_ipn_signature(raw_body: bytes, signature: str) -> bool:
    if not settings.NOWPAYMENTS_IPN_SECRET:
        return False
    parsed = json.loads(raw_body)
    sorted_payload = json.dumps(parsed, sort_keys=True, separators=(",", ":"))
    computed = hmac.new(
        settings.NOWPAYMENTS_IPN_SECRET.encode(), sorted_payload.encode(), hashlib.sha512
    ).hexdigest()
    return hmac.compare_digest(computed, signature)


async def handle_ipn_webhook(raw_body: bytes, signature: str) -> dict:
    if not _verify_ipn_signature(raw_body, signature):
        raise ValueError("IPN signature tidak valid — request ditolak.")

    payload = json.loads(raw_body)
    payment_id = payload.get("payment_id") or payload.get("invoice_id")
    status = payload.get("payment_status", "waiting")
    order_id = payload.get("order_id", "")

    sb = get_supabase()
    sb.table("payments").update({"status": status, "raw_payload": payload}) \
        .eq("provider_payment_id", payment_id).execute()

    if status == "finished":
        user_id, plan = order_id.split(":")[0], order_id.split(":")[1]
        period_end = datetime.now(timezone.utc) + timedelta(days=30)
        sb.table("subscriptions").update({
            "plan": plan,
            "status": "active",
            "current_period_end": period_end.isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }).eq("user_id", user_id).execute()

    return {"received": True, "status": status}
