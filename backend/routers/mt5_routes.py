from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status

from backend.auth.siwe import get_current_user
from backend.db.supabase_client import get_supabase
from backend.models.schemas import LinkMT5AccountRequest
from backend.services import mt5_service
from backend.services.encryption import get_cipher
from backend.services.ownership import get_owned_account as _get_owned_account
from backend.services.risk_manager import resolve_preset

router = APIRouter(prefix="/api/mt5", tags=["mt5"])


@router.get("/accounts")
async def list_accounts(user: dict = Depends(get_current_user)):
    sb = get_supabase()
    res = sb.table("mt5_accounts").select("id, label, broker_server, mt5_login, is_live, connection_status") \
        .eq("user_id", user["id"]).execute()
    return res.data


@router.post("/accounts")
async def link_account(body: LinkMT5AccountRequest, user: dict = Depends(get_current_user)):
    """
    Login akun trading MT5 milik user sendiri: nomor akun + password + nama
    server broker (BUKAN broker tertentu — bisa broker MT5 apa aja, tinggal
    isi nama server-nya, contoh 'VantageInternational-Live 3',
    'ICMarketsSC-Demo', dst).
    """
    sb = get_supabase()
    encrypted_pw = get_cipher().encrypt(body.mt5_password)

    row = sb.table("mt5_accounts").insert({
        "user_id": user["id"], "label": body.label, "broker_server": body.broker_server,
        "mt5_login": body.mt5_login, "encrypted_password": encrypted_pw,
        "is_live": body.is_live, "connection_status": "connecting",
    }).execute().data[0]

    try:
        metaapi_id = await mt5_service.provision_account(
            body.mt5_login, body.mt5_password, body.broker_server, body.label, body.is_live
        )
        sb.table("mt5_accounts").update({
            "metaapi_account_id": metaapi_id, "connection_status": "connected",
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }).eq("id", row["id"]).execute()
        row["metaapi_account_id"] = metaapi_id
        row["connection_status"] = "connected"
    except Exception as e:
        sb.table("mt5_accounts").update({"connection_status": "error"}).eq("id", row["id"]).execute()
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, f"Gagal konek ke MT5: {e}")

    # buat default risk settings (preset balanced) begitu akun kekonek
    default_cfg = resolve_preset("balanced")
    default_cfg["mt5_account_id"] = row["id"]
    sb.table("risk_settings").insert(default_cfg).execute()

    return row


@router.get("/accounts/{account_id}/balance")
async def get_balance(account_id: str, user: dict = Depends(get_current_user)):
    account = _get_owned_account(account_id, user)
    if not account.get("metaapi_account_id"):
        raise HTTPException(status.HTTP_409_CONFLICT, "Akun belum selesai konek.")
    return await mt5_service.get_account_info(account["metaapi_account_id"])


@router.get("/accounts/{account_id}/positions")
async def get_positions(account_id: str, user: dict = Depends(get_current_user)):
    account = _get_owned_account(account_id, user)
    if not account.get("metaapi_account_id"):
        raise HTTPException(status.HTTP_409_CONFLICT, "Akun belum selesai konek.")
    return await mt5_service.get_open_positions(account["metaapi_account_id"])


@router.delete("/accounts/{account_id}")
async def unlink_account(account_id: str, user: dict = Depends(get_current_user)):
    _get_owned_account(account_id, user)
    sb = get_supabase()
    sb.table("mt5_accounts").delete().eq("id", account_id).execute()
    return {"deleted": True}
