"""
Wrapper tipis di atas supabase-py. Backend selalu pakai SERVICE_ROLE key
(bukan anon key) karena semua akses tabel divalidasi di level backend
(lewat JWT session kita sendiri), bukan lewat Supabase RLS + auth.uid().
"""
from functools import lru_cache
from supabase import create_client, Client
from backend.config import settings


@lru_cache
def get_supabase() -> Client:
    if not settings.SUPABASE_URL or not settings.SUPABASE_SERVICE_ROLE_KEY:
        raise RuntimeError(
            "SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY belum di-set di .env. "
            "Buat project gratis di https://supabase.com, lalu jalankan "
            "supabase/schema.sql di SQL Editor."
        )
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)
