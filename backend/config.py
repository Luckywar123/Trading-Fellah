"""
Central config. Semua rahasia (API key, secret) datang dari environment
variables — JANGAN pernah hardcode di sini. Lihat .env.example di root
project buat daftar lengkap yang perlu diisi.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # --- App ---
    APP_NAME: str = "Trading Fellah"
    ENV: str = "development"                 # development | production
    FRONTEND_ORIGIN: str = "http://localhost:5173"
    # Origin tambahan (pisah koma), misal domain custom + domain vercel:
    #   CORS_EXTRA_ORIGINS=https://trading-fellah.vercel.app,https://app.domainkamu.com
    CORS_EXTRA_ORIGINS: str = ""
    # Regex opsional buat preview deployment Vercel, contoh:
    #   CORS_ORIGIN_REGEX=https://trading-fellah.*\\.vercel\\.app
    CORS_ORIGIN_REGEX: str = ""

    # --- Auth / JWT (session token setelah wallet login berhasil) ---
    JWT_SECRET: str = "CHANGE_ME_dev_only_insecure_secret"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_HOURS: int = 24 * 7            # 7 hari

    # --- Encryption key buat nyimpen password MT5 (Fernet, 32 byte urlsafe base64) ---
    # generate: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
    CREDENTIAL_ENCRYPTION_KEY: str = ""

    # --- Supabase ---
    SUPABASE_URL: str = ""
    SUPABASE_SERVICE_ROLE_KEY: str = ""       # backend pakai service_role, BUKAN anon key

    # --- MetaApi (cloud MT5 bridge, https://metaapi.cloud) ---
    METAAPI_TOKEN: str = ""
    METAAPI_REGION: str = "new-york"

    # --- AI Agent (pluggable — user pilih provider) ---
    AI_PROVIDER: str = "anthropic"            # anthropic | openai
    ANTHROPIC_API_KEY: str = ""
    ANTHROPIC_MODEL: str = "claude-sonnet-4-6"
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4.1"

    # --- News data source (dipakai news_service buat nyari berita ekonomi) ---
    NEWS_API_KEY: str = ""                    # contoh: NewsAPI.org / Finnhub / FMP, bebas swap adapter
    NEWS_PROVIDER: str = "finnhub"

    # --- Payments: NOWPayments (crypto invoicing + IPN webhook) ---
    NOWPAYMENTS_API_KEY: str = ""
    NOWPAYMENTS_IPN_SECRET: str = ""
    NOWPAYMENTS_BASE_URL: str = "https://api.nowpayments.io/v1"

    # --- Plan pricing (USD, ditagih dalam crypto via NOWPayments) ---
    PLAN_PRICE_BASIC: float = 29.0
    PLAN_PRICE_PRO: float = 79.0
    PLAN_PRICE_ELITE: float = 199.0

    # --- Payments: Midtrans (QRIS, https://midtrans.com) ---
    # QRIS cuma bisa diterbitkan lewat PJP resmi berizin BI — Midtrans salah
    # satu yang paling umum. Charge-nya jalan di IDR, bukan USD, jadi harga
    # plan didefinisikan terpisah di bawah (samain manual sama kurs kamu).
    MIDTRANS_SERVER_KEY: str = ""
    MIDTRANS_IS_PRODUCTION: bool = False
    PLAN_PRICE_BASIC_IDR: int = 470_000
    PLAN_PRICE_PRO_IDR: int = 1_270_000
    PLAN_PRICE_ELITE_IDR: int = 3_190_000


    @property
    def cors_origins(self) -> list[str]:
        raw = [self.FRONTEND_ORIGIN, *self.CORS_EXTRA_ORIGINS.split(",")]
        return sorted({o.strip().rstrip("/") for o in raw if o.strip()})

    def validate_for_production(self) -> list[str]:
        """Return daftar masalah config yang fatal kalau ENV=production."""
        problems = []
        if self.JWT_SECRET.startswith("CHANGE_ME") or len(self.JWT_SECRET) < 32:
            problems.append("JWT_SECRET belum di-set / terlalu pendek (min 32 karakter).")
        if not self.CREDENTIAL_ENCRYPTION_KEY:
            problems.append("CREDENTIAL_ENCRYPTION_KEY kosong.")
        if not self.SUPABASE_URL or not self.SUPABASE_SERVICE_ROLE_KEY:
            problems.append("SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY kosong.")
        return problems


settings = Settings()
