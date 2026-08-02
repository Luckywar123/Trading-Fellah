from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status

from backend.auth.siwe import get_current_user
from backend.db.supabase_client import get_supabase
from backend.models.schemas import RiskSettingsUpdate
from backend.services.ownership import get_owned_account as _get_owned_account
from backend.services.risk_manager import PRESETS, resolve_preset

router = APIRouter(prefix="/api/risk", tags=["risk"])


@router.get("/presets")
async def list_presets():
    """Buat tombol pilihan di UI: Conservative / Balanced / Aggressive / Full Send."""
    return PRESETS


@router.get("/accounts/{account_id}/settings")
async def get_settings(account_id: str, user: dict = Depends(get_current_user)):
    _get_owned_account(account_id, user)
    sb = get_supabase()
    res = sb.table("risk_settings").select("*").eq("mt5_account_id", account_id).execute()
    if not res.data:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Belum ada risk settings buat akun ini.")
    return res.data[0]


@router.put("/accounts/{account_id}/settings")
async def update_settings(account_id: str, body: RiskSettingsUpdate, user: dict = Depends(get_current_user)):
    """
    User pilih sendiri agresivitasnya di sini — baik lewat tombol preset
    (conservative/balanced/aggressive/full_send) atau custom manual tiap
    parameter. full_margin_mode HANYA nyala kalau user eksplisit set true
    (baik lewat preset full_send atau custom).
    """
    _get_owned_account(account_id, user)
    sb = get_supabase()

    update = {k: v for k, v in body.model_dump().items() if v is not None}
    if body.preset and body.preset != "custom":
        preset_defaults = resolve_preset(body.preset)
        preset_defaults.update(update)  # override eksplisit user menang di atas default preset
        update = preset_defaults
        update["preset"] = body.preset
    update["updated_at"] = datetime.now(timezone.utc).isoformat()

    res = sb.table("risk_settings").update(update).eq("mt5_account_id", account_id).execute()
    if not res.data:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Risk settings tidak ditemukan.")
    return res.data[0]
