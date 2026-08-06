from fastapi import APIRouter, Depends, HTTPException, Request, status

from backend.auth.siwe import get_current_user
from backend.db.supabase_client import get_supabase
from backend.models.schemas import CheckoutRequest, CheckoutQrisRequest
from backend.services import payment_service, qris_service

router = APIRouter(prefix="/api/billing", tags=["billing"])


@router.get("/status")
async def billing_status(user: dict = Depends(get_current_user)):
    sb = get_supabase()
    res = sb.table("subscriptions").select("*").eq("user_id", user["id"]).execute()
    return res.data[0] if res.data else {"status": "inactive", "plan": None}


@router.post("/checkout")
async def checkout(body: CheckoutRequest, user: dict = Depends(get_current_user)):
    """Bikin invoice NOWPayments (hosted checkout page), redirect user ke situ buat bayar crypto."""
    return await payment_service.create_invoice(user["id"], body.plan, body.success_url, body.cancel_url)


@router.post("/webhook")
async def nowpayments_webhook(request: Request):
    """Endpoint publik (dipanggil server NOWPayments, bukan user) — jangan taruh
    di belakang auth. Keamanan dijamin lewat verifikasi HMAC signature IPN."""
    raw_body = await request.body()
    signature = request.headers.get("x-nowpayments-sig", "")
    try:
        result = await payment_service.handle_ipn_webhook(raw_body, signature)
    except ValueError as e:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, str(e))
    return result


@router.post("/checkout-qris")
async def checkout_qris(body: CheckoutQrisRequest, user: dict = Depends(get_current_user)):
    """Generate QR code QRIS statis buat di-scan user — jalur bayar alternatif
    selain invoice crypto, ditagih dalam IDR lewat Midtrans."""
    try:
        return await qris_service.create_qris_charge(user["id"], body.plan)
    except RuntimeError as e:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, str(e))


@router.get("/qris-status/{order_id}")
async def qris_status(order_id: str, user: dict = Depends(get_current_user)):
    """Polling manual dari frontend abis user scan — jaga-jaga webhook telat."""
    return await qris_service.check_status(order_id)


@router.post("/webhook-qris")
async def midtrans_webhook(request: Request):
    """Endpoint publik (dipanggil server Midtrans, bukan user) — jangan taruh
    di belakang auth. Keamanan dijamin lewat verifikasi signature_key (SHA512)."""
    payload = await request.json()
    try:
        result = await qris_service.handle_notification(payload)
    except ValueError as e:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, str(e))
    return result


@router.get("/payments")
async def payment_history(user: dict = Depends(get_current_user)):
    sb = get_supabase()
    res = sb.table("payments").select("*").eq("user_id", user["id"]).order("created_at", desc=True).execute()
    return res.data
