# Update: Landing page + QRIS payment

## 1. Kenapa "Failed to fetch" muncul di deploy Vercel

Build Vercel kamu itu **sukses** (warning chunk >500kB cuma saran optimisasi,
bukan error). "Failed to fetch" adalah error runtime di browser, bukan error
build — penyebabnya:

- `frontend/src/lib/api.js` fallback ke `http://localhost:8000` kalau env var
  `VITE_API_URL` gak di-set. Vite nge-bake env var itu SAAT BUILD, jadi kalau
  gak diisi di Vercel project settings, hasil build bakal selalu coba fetch
  ke `localhost:8000` — yang gak ada apa-apanya di komputer pengunjung situs.
- Backend FastAPI kamu (folder `backend/`) itu server yang perlu jalan terus
  (bukan static site) — Vercel yang kamu build cuma `frontend/`. Backend-nya
  harus di-deploy terpisah (Railway/Fly.io/VPS, lihat README bagian Deploy).

**Cara benerin:**
1. Deploy `backend/` ke Railway/Fly.io/VPS dulu (kalau belum), catat URL-nya
   misal `https://api-tradingfellah.up.railway.app`.
2. Di Vercel dashboard → project frontend kamu → Settings → Environment
   Variables → tambahin `VITE_API_URL` = URL backend itu.
3. Redeploy (env var Vite cuma kepake abis build baru).
4. Di backend, set `FRONTEND_ORIGIN` = URL Vercel kamu (misal
   `https://trading-fellah.vercel.app`) biar CORS ngizinin request dari situ.
   Tanpa ini browser bakal nge-block fetch-nya juga meskipun URL-nya bener.

## 2. Landing page publik sebelum login

- `frontend/src/pages/Landing.jsx` (baru) — halaman marketing publik: hero,
  fitur, cara mulai, lapisan keamanan auto-trade, preview pricing, CTA.
  Gak butuh wallet buat lihat halaman ini.
- Routing (`App.jsx`) diubah: `/` sekarang Landing (publik), dashboard
  pindah ke `/dashboard` (tetap protected, wajib login wallet).
- `Layout.jsx` nav & `Login.jsx` redirect abis login disesuain ke
  `/dashboard`.
- Gak ada statistik/testimoni palsu di landing ini — cuma fitur yang emang
  ada di kode + disclaimer risiko yang sama kayak di README kamu. Silakan
  tambahin social proof beneran (jumlah user asli, dst) kalau udah ada.

## 3. QRIS sebagai opsi bayar (selain crypto)

Login tetap wallet-only (gak butuh crypto buat sekadar masuk) — QRIS cuma
muncul di halaman **Billing**, sebagai pilihan kedua di samping "Bayar
Crypto" yang udah ada.

- `backend/services/qris_service.py` (baru) — integrasi Midtrans Core API
  (charge QRIS + verifikasi webhook + polling status).
- `backend/routers/subscription_routes.py` — endpoint baru:
  `POST /api/billing/checkout-qris`, `GET /api/billing/qris-status/{id}`,
  `POST /api/billing/webhook-qris`.
- `backend/config.py` + `.env.example` — env var baru: `MIDTRANS_SERVER_KEY`,
  `MIDTRANS_IS_PRODUCTION`, `PLAN_PRICE_*_IDR`.
- `frontend/src/components/QrisModal.jsx` (baru) — modal nampilin QR code,
  countdown, polling status tiap 5 detik.
- `frontend/src/pages/Billing.jsx` — tiap plan sekarang punya 2 tombol:
  "Bayar Crypto" (NOWPayments, existing) dan "Bayar QRIS" (Midtrans, baru).

**Yang perlu kamu setup buat QRIS jalan:**
1. Daftar akun di https://midtrans.com (ada sandbox gratis buat testing).
2. Settings → Access Keys → copy **Server Key**.
3. Isi `MIDTRANS_SERVER_KEY` di `.env` backend. Biarin
   `MIDTRANS_IS_PRODUCTION=false` dulu buat testing pakai sandbox.
4. Pas mau nerima pembayaran beneran: ganti ke Production key, set
   `MIDTRANS_IS_PRODUCTION=true`, dan daftarin
   `https://domain-kamu.com/api/billing/webhook-qris` sebagai notification
   URL di dashboard Midtrans.
5. Sesuain `PLAN_PRICE_*_IDR` di `.env` sama kurs yang kamu mau (Midtrans
   charge QRIS dalam Rupiah, beda dari NOWPayments yang USD).

Regulasi: nerima pembayaran publik buat layanan trading otomatis biasanya
kena aturan finansial tergantung yurisdiksi — ini bukan nasihat hukum, cek
ke konsultan legal sebelum go-live publik (poin ini juga udah ada di
README asli kamu).
