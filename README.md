# Trading Fellah — Sniper Terminal

Platform web multi-tenant buat trading MT5: login pakai wallet crypto,
membership berlangganan (dibayar crypto), tautkan akun MT5 broker manapun,
eksekusi order/lihat balance/posisi real-time, AI swing + order block +
support/resistance detector dengan mode full-margin yang bisa diatur
sendiri agresivitasnya, news sentiment AI, behavior profiling AI, backtest
engine, dan forward test (paper trading pakai harga live).

## Arsitektur singkat

```
frontend/  React + Vite + Tailwind — dashboard, trade, risk settings, backtest, AI, billing
backend/   FastAPI (Python) — auth, MT5 bridge, risk engine, AI agent, payments
supabase/  schema.sql — database (Postgres, di-hosting Supabase gratis)
```

| Kebutuhan | Solusi dipakai | Kenapa |
|---|---|---|
| Database + tabel user | **Supabase** (free tier) | sesuai request, gratis, Postgres asli |
| Koneksi ke MT5 | **MetaApi.cloud** | satu-satunya cara realistis buat multi-user, banyak broker, dari server Linux — library resmi `MetaTrader5` python cuma jalan di Windows + 1 koneksi aktif |
| Login | **Wallet (SIWE-style)** | sesuai request "login wallet", gak perlu email/password |
| Bayar membership | **NOWPayments** | crypto invoicing + webhook, gak perlu bikin infra blockchain sendiri |
| AI (news, rationale, behavior) | **Pluggable — Anthropic/OpenAI** | kamu pilih sendiri lewat `.env`, ganti kapan aja |
| Auto-trade LIVE | **Opt-in berlapis, default OFF** | lihat bagian "Live Auto-Trade" di bawah |

MetaApi dan NOWPayments itu layanan pihak ketiga berbayar (ada tier gratis
terbatas) — bukan produk Anthropic, dan kamu perlu daftar akun sendiri di
masing-masing.

## Live Auto-Trade — cara kerja & lapisan pengaman

Halaman **Automation** (`/automation`) yang ngatur ini. AI eksekusi order
ASLI tanpa klik manusia, jadi sengaja dibikin berlapis dan default MATI:

1. **Master switch** (`risk_settings.live_autotrade_enabled`) — per akun MT5,
   default `false`. Nyalain lewat modal konfirmasi yang minta kamu ketik
   "AKTIFKAN" (bukan cuma klik sekali).
2. **Watchlist per simbol** (`live_autotrade_configs`) — kamu pilih simbol
   mana aja yang boleh diawasi. Dua-duanya (master + watchlist) harus nyala
   bareng baru order beneran dikirim.
3. **News blackout net** — auto-pause pas rilis berita high-impact.
4. **Circuit breaker** — 5 loss beruntun atau drawdown 20% dari modal awal
   hari itu bikin sistem berhenti buka posisi baru (dihitung dari histori
   trade ASLI, bukan angka hardcode).
5. **Emergency Stop** — satu tombol (ada permanen di topbar pas live nyala,
   juga di halaman Automation) yang langsung matiin master switch DAN nutup
   semua posisi terbuka di akun itu.
6. **Ambang confidence AI** — sinyal swing/order block/S&R harus lolos
   `ai_confidence_threshold` (diatur di Risk Settings) sebelum dieksekusi.

Scheduler ngecek tiap 5 menit, logic-nya PERSIS SAMA dengan yang dipakai
forward test (satu sumber kode di `backend/services/signal_engine.py`) —
bedanya forward test cuma nyatet ke database, live auto-trade beneran kirim
order ke `mt5_service.open_market_order()`.

**Saran rollout**: nyalain Forward Test dulu di simbol yang kamu mau, biarin
jalan beberapa hari, lihat di halaman Automation seberapa sering dan
seberapa akurat sinyalnya — baru pertimbangkan nyalain live dengan preset
kecil (Conservative/Balanced) dulu sebelum naikin ke Aggressive/Full Send.

---

## 1. Setup Supabase (database)

1. Daftar gratis di https://supabase.com, bikin project baru.
2. Buka **SQL Editor**, copy-paste seluruh isi `supabase/schema.sql`, run.
3. Buka **Settings → API**, copy:
   - `Project URL` → `SUPABASE_URL`
   - `service_role` key (bukan `anon` key!) → `SUPABASE_SERVICE_ROLE_KEY`

## 2. Setup MetaApi (jembatan ke MT5)

1. Daftar di https://metaapi.cloud, ambil API token dari dashboard.
2. Isi ke `METAAPI_TOKEN`.
3. Cek free tier mereka cukup buat berapa akun — kalau user udah banyak,
   ini jadi biaya operasional bulanan (charge per akun MT5 yang konek).

## 3. Setup AI provider

Pilih salah satu (atau isi dua-duanya biar gampang switch via `AI_PROVIDER`):
- **Anthropic**: https://console.anthropic.com → API key
- **OpenAI**: https://platform.openai.com → API key

## 4. Setup News data (opsional tapi disarankan buat fitur news sentiment)

Daftar di https://finnhub.io (ada free tier), isi `NEWS_API_KEY`.
Provider lain bisa disambung — tinggal tambah cabang di
`backend/services/news_service.py` fungsi `_fetch_raw_news()`.

## 5. Setup NOWPayments (billing crypto)

1. Daftar di https://nowpayments.io, verifikasi akun.
2. Store Settings → ambil API Key → `NOWPAYMENTS_API_KEY`.
3. Aktifkan IPN (webhook), set secret → `NOWPAYMENTS_IPN_SECRET`.
4. Pas deploy ke production, endpoint webhook kamu
   (`https://domain-kamu.com/api/billing/webhook`) didaftarin di dashboard
   NOWPayments sebagai IPN callback URL.

## 6. Generate secret keys

```bash
# JWT_SECRET
python3 -c "import secrets; print(secrets.token_hex(32))"

# CREDENTIAL_ENCRYPTION_KEY (buat enkripsi password MT5 user)
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

**Backup `CREDENTIAL_ENCRYPTION_KEY` di tempat aman** (password manager /
secret vault). Kalau hilang, semua password MT5 yang tersimpan gak bisa
didekripsi lagi dan semua user harus re-link akun mereka.

## 7. Isi environment file

```bash
cp .env.example .env         # isi semua value dari langkah 1-6 di atas
cp frontend/.env.example frontend/.env
```

## 8. Jalankan backend

```bash
python3 -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r backend/requirements.txt
uvicorn backend.main:app --reload --port 8000
```
Buka http://localhost:8000/docs buat coba semua endpoint langsung dari Swagger UI.

## 9. Jalankan frontend

```bash
cd frontend
npm install
npm run dev
```
Buka http://localhost:5173 — connect wallet (MetaMask atau kompatibel), tautkan akun MT5, mulai trading.

---

## Deploy ke production (rekomendasi)

**Opsi A — Docker (paling cepat, satu server):**
```bash
cp .env.example .env   # isi semua value
docker compose up -d --build
```
Backend jalan di `:8000`, frontend (nginx, hasil build) di `:5173`. Set
`VITE_API_URL` di `.env` ke domain publik backend kamu sebelum build kalau
deploy ke server beneran (bukan localhost).

**Opsi B — Platform terpisah (lebih gampang di-scale):**
- **Backend**: Railway.app atau Fly.io — jalan di Linux, gak butuh Windows
  karena MetaApi yang handle koneksi MT5-nya. `docker build -f backend/Dockerfile .`
  atau langsung `uvicorn backend.main:app`.
- **Frontend**: Vercel atau Netlify — build `frontend/`, set `VITE_API_URL`
  ke URL backend production.
- **Scheduler** (news refresh, forward test, live auto-trade, subscription
  expiry) jalan otomatis di dalam proses backend (`APScheduler`) — kalau
  user udah banyak, pisahin ke worker process terpisah (lihat komentar di
  `backend/main.py`).

---

## Yang perlu kamu tahu (jujur soal scope)

Ini kerangka **fungsional dan lengkap secara struktur** — semua endpoint
konek beneran ke Supabase, MetaApi, dan AI provider, bukan data dummy/random
kayak repo lama. Backend + frontend udah divalidasi (compile bersih, semua
route ke-load, logic risk sizing & signal detection dites pakai data
sintetis). Beberapa catatan jujur:

- **Bug yang ketemu & diperbaiki saat testing**: deteksi order block awalnya
  cuma nge-cek candle turun yang PERSIS sebelah candle yang nembus swing
  high — di market yang trending halus, dua kondisi itu nyaris gak pernah
  ketemu di candle yang sama (breakout beneran biasanya butuh beberapa
  candle momentum dulu), jadi order block nyaris gak pernah kedeteksi.
  Sekarang jalan mundur dari candle breakout buat nemuin candle
  berlawanan warna yang bener (`backend/services/swing_detector.py`,
  method `_find_order_blocks`). Diverifikasi lewat smoke test: sebelum
  fix = 0 sinyal di 500 bar data trending sintetis, sesudah fix = 23 sinyal
  tervalidasi dengan frekuensi yang masuk akal.
- **Belum pernah dites pakai data pasar ASLI** — semua testing pakai data
  sintetis buatan sendiri buat verifikasi logic-nya jalan, bukan buat
  klaim performa/win-rate di pasar beneran. Sebelum percaya nyalain live,
  jalanin Forward Test dulu beberapa hari (lihat halaman Automation).
- **Backtest** pakai model eksekusi simpel (fill di harga close, spread
  flat) — cukup buat riset awal, tapi gak 100% presisi kayak live.
- **Trailing stop di live auto-trade** masih pakai asumsi pip 0.0001 buat
  semua pair (lihat catatan di `live_autotrader.py`) — buat pair yang ada
  JPY-nya, ganti ke `spec['pip_size']` (fungsi `get_symbol_spec` udah ada,
  tinggal disambungkan ke fungsi trailing-nya).
- **News blackout** pakai daftar keyword + data dari `ai_news_events` —
  buat produksi, idealnya tarik kalender ekonomi resmi (bukan cuma
  headline) biar jadwal rilis presisi ke menit.
- **MetaApi rate limit & biaya**: makin banyak akun MT5 konek bersamaan,
  makin besar tagihan bulanan — masukin ini ke perhitungan harga plan
  membership kamu.
- **Regulasi**: nyediain layanan eksekusi trading otomatis + terima
  pembayaran dari publik biasanya kena aturan finansial tergantung negara
  (butuh lisensi/izin di sebagian yurisdiksi kalau ini dijalankan sebagai
  bisnis komersial ke banyak orang asing). Ini bukan nasihat hukum — cek ke
  konsultan legal sebelum go-live publik.
- **Full margin mode** — sesuai request, TAPI selalu dibatasi
  `max_margin_pct_per_trade` yang user atur sendiri di Risk Settings
  (default preset "Full Send" = 90%, bisa didorong lebih tinggi manual).
  Ini murni soal matematika leverage: makin dekat ke 100%, makin kecil
  ruang gerak sebelum margin call.
- **Belum ada automated test suite** (pytest/vitest) — validasi sejauh ini
  lewat smoke test manual. Buat production beneran, tambahin test suite
  proper, terutama buat `risk_manager.py` dan `signal_engine.py`.

## Struktur file penting

```
backend/
  main.py                    entry point + scheduler (news, forward test, LIVE AUTOTRADE, subscription expiry)
  config.py                  semua env var
  auth/siwe.py                wallet login (nonce + verify signature + JWT)
  services/
    mt5_service.py            jembatan ke MetaApi (balance/posisi/order/spek simbol)
    risk_manager.py           position sizing, preset, full-margin ceiling
    swing_detector.py         swing high/low, order block, S&R, validasi breakout
    signal_engine.py          logic "cari sinyal tervalidasi" — 1 sumber dipakai backtest+forward+live
    trade_stats.py             consecutive losses & daily count dari histori trade ASLI
    live_autotrader.py         eksekusi order ASLI berdasar sinyal AI (opt-in berlapis)
    forward_test.py            paper trading pakai harga live (aman, gak kirim order asli)
    backtest_engine.py         replay historis pakai logic yang sama dgn live
    ai_agent.py                LLM pluggable — news sentiment, rationale, behavior
    news_service.py           fetch berita + news blackout gate
    payment_service.py        NOWPayments invoice + webhook
  routers/                    semua endpoint REST (lihat /docs)
frontend/src/
  pages/                      Dashboard, Trade, RiskSettings, Backtest, Automation, AIInsights, Billing, Login
  components/                 Layout (+ tombol Emergency Stop), RiskGauge, ConfirmModal, LinkAccountForm
  context/                    AuthContext (wallet session), AccountContext (akun MT5 aktif)
supabase/schema.sql            seluruh skema database
backend/Dockerfile, frontend/Dockerfile, docker-compose.yml    deploy siap pakai
```
