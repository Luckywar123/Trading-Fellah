from fastapi import HTTPException, status

from backend.db.supabase_client import get_supabase


def get_owned_account(account_id: str, user: dict) -> dict:
    """Ambil 1 row mt5_accounts dan pastikan itu benar milik user yang lagi login."""
    sb = get_supabase()
    res = sb.table("mt5_accounts").select("*").eq("id", account_id).execute()
    if not res.data:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Akun MT5 tidak ditemukan.")
    account = res.data[0]
    if account["user_id"] != user["id"]:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Bukan akun kamu.")
    return account
