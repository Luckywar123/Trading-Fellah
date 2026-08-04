"""
Sebelumnya `can_open_trade()` di risk_manager dipanggil dengan
`consecutive_losses=0` di-hardcode (lihat trading_routes.py versi awal) —
artinya circuit breaker 5-loss-beruntun itu gak pernah beneran ngecek apa-apa.
Modul ini ngitung dari histori trade ASLI (bukan forward test) biar gate-nya
beneran jalan, dipakai bareng oleh manual trading (trading_routes.py) dan
live auto-trader (live_autotrader.py) — dua-duanya harus lihat angka yang sama.
"""
from datetime import datetime, timezone


def consecutive_losses(sb, mt5_account_id: str) -> int:
    res = (
        sb.table("trades")
        .select("pnl_usd")
        .eq("mt5_account_id", mt5_account_id)
        .eq("is_forward_test", False)
        .not_.is_("closed_at", "null")
        .order("closed_at", desc=True)
        .limit(20)
        .execute()
    )
    count = 0
    for t in res.data or []:
        if (t.get("pnl_usd") or 0) <= 0:
            count += 1
        else:
            break
    return count


def daily_trade_count(sb, mt5_account_id: str) -> int:
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
    res = (
        sb.table("trades")
        .select("id", count="exact")
        .eq("mt5_account_id", mt5_account_id)
        .eq("is_forward_test", False)
        .gte("opened_at", today_start)
        .execute()
    )
    return res.count or 0
