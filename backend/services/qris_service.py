"""
Pembayaran membership pakai QRIS lewat Midtrans (https://midtrans.com).

Kenapa Midtrans? QRIS itu standar QR pembayaran nasional (BI/ASPI) — gak ada
cara sah buat nerbitin kode QRIS tanpa lewat PJP (Penyedia Jasa Pembayaran)
berizin BI. Midtrans salah satu PJP yang paling umum dipakai buat integrasi
kayak gini dan Core API-nya cukup simpel buat charge QRIS langsung tanpa
redirect ke halaman pihak ketiga. Kalau kamu udah punya PJP lain (Xendit,
DOKU, dst), service ini bisa diganti — interface-nya sama kayak
payment_service.py (create + handle notification), tinggal pasang provider
baru di router.

Beda sama login wallet (auth/siwe.py) dan invoice crypto (payment_service.py)
— dua-duanya itu metode BEDA buat nagih fee membership yang sama, user pilih
salah satu pas checkout.

CATATAN: Midtrans charge dalam IDR, bukan USD kayak NOWPayments. Nominal IDR
disimpen di kolom `amount_usd` tabel payments (biar gak nambah kolom baru di
schema) — frontend format ulang jadi "Rp" berdasar `pay_currency == 'QRIS'`.
Kalau butuh histori pembayaran yang lebih rapi, tambahin kolom
`amount_local numeric` + `currency_local text` di supabase/schema.sql.
"""
import hashlib
import hmac
from datetime import datetime, timedelta, timezone

import httpx

from backend.config import settings
from backend.db.supabase_client import get_supabase

PLAN_PRICES_IDR = {
    "basic": settings.PLAN_PRICE_BASIC_IDR,
    "pro": settings.PLAN_PRICE_PRO_IDR,
    "elite": settings.PLAN_PRICE_ELITE_IDR,
}


def _base_url() -> str:
    return (
        "https://api.midtrans.com/v2"
        if settings.MIDTRANS_IS_PRODUCTION
        else "https://api.sandbox.midtrans.com/v2"
    )


async def create_qris_charge(user_id: str, plan: str) -> dict:
    if plan not in PLAN_PRICES_IDR:
        raise ValueError(f"Plan tidak dikenal: {plan}")
    if not settings.MIDTRANS_SERVER_KEY:
        raise RuntimeError("MIDTRANS_SERVER_KEY belum di-set di .env (daftar di midtrans.com).")

    order_id = f"{user_id}:{plan}:{int(datetime.now(timezone.utc).timestamp())}"
    amount = int(PLAN_PRICES_IDR[plan])

    payload = {
        "payment_type": "qris",
        "transaction_details": {"order_id": order_id, "gross_amount": amount},
        "qris": {"acquirer": "gopay"},
    }

    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(
            f"{_base_url()}/charge",
            json=payload,
            auth=(settings.MIDTRANS_SERVER_KEY, ""),  # Basic auth: server key sbg username, password kosong
        )
        resp.raise_for_status()
        charge = resp.json()

    qr_action = next((a for a in charge.get("actions", []) if a.get("name") == "generate-qr-code"), None)
    if not qr_action:
        raise RuntimeError("Midtrans gak balikin QR code — cek transaction_status di response.")

    sb = get_supabase()
    sb.table("payments").insert({
        "user_id": user_id,
        "provider": "midtrans_qris",
        "provider_payment_id": order_id,
        "plan": plan,
        "amount_usd": amount,          # nominal IDR, lihat catatan di docstring atas
        "pay_currency": "QRIS",
        "status": "waiting",
        "raw_payload": charge,
    }).execute()

    return {
        "order_id": order_id,
        "qr_image_url": qr_action["url"],
        "gross_amount": amount,
        "expiry_minutes": 15,
        "transaction_status": charge.get("transaction_status"),
    }


def _verify_notification_signature(payload: dict) -> bool:
    order_id = str(payload.get("order_id", ""))
    status_code = str(payload.get("status_code", ""))
    gross_amount = str(payload.get("gross_amount", ""))
    signature_key = payload.get("signature_key", "")
    raw = f"{order_id}{status_code}{gross_amount}{settings.MIDTRANS_SERVER_KEY}"
    computed = hashlib.sha512(raw.encode()).hexdigest()
    return hmac.compare_digest(computed, signature_key)


_STATUS_MAP = {
    "settlement": "finished",
    "capture": "finished",
    "pending": "waiting",
    "deny": "failed",
    "cancel": "failed",
    "expire": "expired",
    "failure": "failed",
}


async def handle_notification(payload: dict) -> dict:
    """Dipanggil dari webhook publik Midtrans. Keamanan dijamin lewat
    signature_key (SHA512), bukan auth token — endpoint ini gak boleh
    ditaruh di belakang login."""
    if not _verify_notification_signature(payload):
        raise ValueError("Signature notifikasi Midtrans tidak valid — request ditolak.")

    order_id = str(payload.get("order_id", ""))
    transaction_status = payload.get("transaction_status")
    fraud_status = payload.get("fraud_status", "accept")

    status = _STATUS_MAP.get(transaction_status, "waiting")
    if transaction_status == "capture" and fraud_status != "accept":
        status = "failed"

    sb = get_supabase()
    sb.table("payments").update({"status": status, "raw_payload": payload}) \
        .eq("provider_payment_id", order_id).execute()

    if status == "finished" and ":" in order_id:
        parts = order_id.split(":")
        user_id, plan = parts[0], parts[1]
        period_end = datetime.now(timezone.utc) + timedelta(days=30)
        sb.table("subscriptions").update({
            "plan": plan,
            "status": "active",
            "current_period_end": period_end.isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }).eq("user_id", user_id).execute()

    return {"received": True, "status": status}


async def check_status(order_id: str) -> dict:
    """Polling manual buat frontend. Notification webhook Midtrans kadang
    delay beberapa detik — ini fallback biar user gak nunggu doang tanpa
    kepastian pas QR udah di-scan."""
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(
            f"{_base_url()}/{order_id}/status",
            auth=(settings.MIDTRANS_SERVER_KEY, ""),
        )
        resp.raise_for_status()
        data = resp.json()

    transaction_status = data.get("transaction_status")
    status = _STATUS_MAP.get(transaction_status, "waiting")

    # Sinkronin ke DB juga di sini — jaga-jaga kalau webhook belum/gagal masuk.
    if transaction_status in _STATUS_MAP:
        sb = get_supabase()
        sb.table("payments").update({"status": status, "raw_payload": data}) \
            .eq("provider_payment_id", order_id).execute()
        if status == "finished" and ":" in order_id:
            parts = order_id.split(":")
            user_id, plan = parts[0], parts[1]
            period_end = datetime.now(timezone.utc) + timedelta(days=30)
            sb.table("subscriptions").update({
                "plan": plan,
                "status": "active",
                "current_period_end": period_end.isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }).eq("user_id", user_id).execute()

    return {"order_id": order_id, "status": status, "transaction_status": transaction_status}
