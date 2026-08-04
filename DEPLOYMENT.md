# Panduan Hosting — Trading Fellah

Panduan lengkap step-by-step dari nol sampe user beneran bisa pakai
web-nya: Supabase (database) → Backend (API) → Frontend (Vercel).

---

## 0. Keputusan arsitektur — baca ini dulu sebelum mulai

Kamu bilang mau pakai **Vercel** buat hosting. Kabar baik/buruknya:

✅ **Frontend (React/Vite) di Vercel — cocok banget**, gak ada catatan.

⚠️ **Backend (FastAPI) TIDAK aku sarankan taruh di Vercel**, alasannya
konkret (bukan asumsi lama — aku cek dokumentasi Vercel per pertengahan
2026):

1. Vercel Python (FastAPI) jalan sebagai **serverless function** — stateless,
   gak ada proses yang idup terus-terusan. Padahal `backend/main.py` kita
   butuh **APScheduler jalan permanen** buat 4 job berkala: refresh news
   (10 menit), forward test (5 menit), **live auto-trade (5 menit)**, dan
   subscription expiry (1 jam). Serverless function gak bisa "nunggu" kayak
   gitu — dia mati begitu selesai jawab 1 request.
2. **Vercel Cron Jobs** bisa jadi pengganti scheduler, TAPI: paket **Hobby
   (gratis) cuma bisa jadwal 1x sehari** — jauh dari kebutuhan kita yang
   tiap 5 menit. Butuh paket **Pro ($20/bulan)** baru bisa per-menit, dan
   itu pun tiap invocation cron cuma dikasih waktu jalan 60 detik (bisa
   dinaikin sampai 300 detik) — riskan buat siklus live auto-trade yang
   perlu fetch candle + analisa + kirim order ke MetaApi.
3. Koneksi ke MetaApi kita cache di memory proses (`_connection_cache` di
   `mt5_service.py`) — asumsinya proses idup lama. Di serverless, cache itu
   ilang tiap invocation, jadi tiap request harus re-connect ke MetaApi
   dari nol (lebih lambat, lebih boros quota MetaApi).

**Rekomendasi aku**: Frontend di Vercel (sesuai maumu), Backend di host yang
"selalu nyala" — Railway atau Render. Ini bukan pilihan sok teknis, ini
supaya fitur **live auto-trade beneran jalan** tiap 5 menit kayak yang
dirancang, bukan cuma nyala pas ada yang buka web-nya.

**Realita biaya** (per Agustus 2026, bisa berubah — cek harga terbaru
sebelum commit): gak ada lagi backend host yang gratis permanen buat proses
yang harus nyala terus. Railway ~$5/bulan (Hobby), Render Starter ~$7/bulan
(paket gratisnya mati setelah 15 menit gak ada trafik — scheduler ikut mati,
gak cocok). Anggap aja **~$5-7/bulan** buat backend, di luar biaya MetaApi/
NOWPayments/AI API yang usage-based.

Kalau km TETAP mau 100% di Vercel meski tau konsekuensinya (misal buat demo
kecil-kecilan tanpa live auto-trade dulu), ada di **Bagian 6 (Opsional)**
di bawah.

---

## 1. Supabase — Database

### 1.1 Bikin project
1. Ke [supabase.com](https://supabase.com) → Sign up (gratis, gak perlu kartu kredit buat tier gratis) → **New Project**.
2. Isi nama project, password database (SIMPAN, dipakai kalau nanti butuh akses langsung), pilih region terdekat ke user kamu (misal Singapore buat Indonesia).
3. Tunggu ~2 menit sampai project selesai di-provision.

### 1.2 Jalankan schema
1. Di sidebar kiri, klik **SQL Editor** → **New query**.
2. Buka file `supabase/schema.sql` dari project ini, copy semua isinya.
3. Paste ke SQL Editor, klik **Run** (atau Ctrl/Cmd+Enter).
4. Harus muncul "Success. No rows returned" — kalau ada error, screenshot dan cek apakah ada tabel yang udah ada duluan (schema ini pakai `create table if not exists` jadi aman dijalankan ulang).
5. Cek di sidebar **Table Editor** — harusnya muncul ~14 tabel (`users`, `mt5_accounts`, `risk_settings`, `trades`, `subscriptions`, `payments`, `live_autotrade_configs`, `forward_test_configs`, `backtest_runs`, `ai_news_events`, `ai_knowledge_base`, `ai_behavior_profiles`, `auth_nonces`, `ai_signals`).

### 1.3 Ambil kredensial
1. Sidebar → **Project Settings** (ikon gear) → **API**.
2. Copy **Project URL** → nanti jadi `SUPABASE_URL`.
3. Copy key di bagian **Project API keys** yang labelnya **`service_role`** (BUKAN `anon` `public`!) → nanti jadi `SUPABASE_SERVICE_ROLE_KEY`.

> ⚠️ `service_role` key itu setara admin penuh ke database kamu — jangan
> pernah taruh di kode frontend/`.env` yang ke-expose ke browser. Ini
> HANYA dipakai backend.

**Itu aja buat database — Supabase udah nyediain Postgres-nya, gak perlu install/setup server database terpisah.** Yang perlu kamu tambah nanti cuma layanan LAIN yang backend kita pakai (MetaApi, AI provider, dst — bukan bagian dari "database" tapi bagian dari fitur).

---

## 2. Backend — Railway (direkomendasikan)

### 2.1 Siapin API key layanan pendukung dulu

Sebelum deploy backend, siapin ini (bisa didaftar belakangan juga, tapi
backend gak akan berfungsi penuh tanpanya):

| Layanan | Buat apa | Link daftar |
|---|---|---|
| MetaApi.cloud | Konek ke MT5 | metaapi.cloud |
| Anthropic **atau** OpenAI | AI agent (news, rationale, behavior) | console.anthropic.com / platform.openai.com |
| Finnhub | Data berita (opsional, buat fitur news sentiment) | finnhub.io |
| NOWPayments | Bayar membership pakai crypto | nowpayments.io |

### 2.2 Push kode ke GitHub
Railway deploy dari GitHub repo. Kalau belum:
```bash
cd trading-fellah
git init
git add .
git commit -m "initial commit"
# bikin repo baru di github.com, terus:
git remote add origin https://github.com/USERNAME/trading-fellah.git
git push -u origin main
```
Pastikan `.env` **TIDAK** ikut ke-commit (udah ada di `.gitignore`).

### 2.3 Deploy ke Railway
1. Ke [railway.app](https://railway.app) → Sign up pakai GitHub.
2. **New Project** → **Deploy from GitHub repo** → pilih repo `trading-fellah`.
3. Railway bakal nyoba auto-detect — karena project ini ada `backend/` dan `frontend/` dalam satu repo, kamu perlu set **Root Directory** ke kosong (root) dan arahkan build pakai Dockerfile:
   - Klik service yang baru dibuat → **Settings** → **Build**.
   - **Builder**: pilih `Dockerfile`.
   - **Dockerfile Path**: `backend/Dockerfile`.
4. **Settings → Networking** → klik **Generate Domain** — ini jadi URL backend kamu (misal `trading-fellah-backend-production.up.railway.app`). Catat ini, dipakai buat `VITE_API_URL` di frontend nanti.
5. **Variables** tab → masukin SEMUA isi `.env.example` yang udah kamu isi (lihat daftar lengkap di Bagian 4). Railway apply otomatis & redeploy tiap kali kamu ubah variable.
6. Tunggu build selesai (~2-3 menit), cek tab **Deployments** → **View Logs**, harus muncul:
   ```
   INFO: Uvicorn running on http://0.0.0.0:8000
   Scheduler jalan: news refresh tiap 10 menit, forward test tiap 5 menit.
   ```
7. Test: buka `https://<domain-kamu>.up.railway.app/api/health` di browser — harus balikin `{"status":"online",...}`.
8. Test docs interaktif: `https://<domain-kamu>.up.railway.app/docs`.

### Alternatif: Render
Kalau lebih suka Render (harga fix per bulan, bukan usage-based):
1. [render.com](https://render.com) → **New** → **Web Service** → connect repo.
2. **Root Directory**: kosongkan. **Dockerfile Path**: `backend/Dockerfile`.
3. Pilih plan **Starter** ($7/bln) — **JANGAN** pilih Free, karena free tier Render tidur setelah 15 menit gak ada trafik, scheduler-nya bakal ikut berhenti.
4. Masukin environment variables yang sama di tab **Environment**.
5. Deploy, catat URL-nya (`https://trading-fellah-backend.onrender.com`).

---

## 3. Frontend — Vercel

1. Ke [vercel.com](https://vercel.com) → Sign up pakai GitHub.
2. **Add New** → **Project** → pilih repo `trading-fellah`.
3. Di layar konfigurasi:
   - **Root Directory**: klik **Edit**, pilih folder `frontend`.
   - **Framework Preset**: Vercel otomatis detect **Vite**.
   - **Build Command**: `npm run build` (default, biarin).
   - **Output Directory**: `dist` (default, biarin).
4. **Environment Variables** — tambahin satu:
   - `VITE_API_URL` = URL backend kamu dari Railway/Render (contoh: `https://trading-fellah-backend-production.up.railway.app`) — **PENTING**: tanpa trailing slash, dan pastikan `https://`.
5. Klik **Deploy**. Tunggu ~1 menit.
6. Setelah selesai, Vercel kasih URL (contoh: `trading-fellah.vercel.app`) — ini yang dibuka user.

### Update CORS di backend
Backend cuma nerima request dari origin yang diizinin (`FRONTEND_ORIGIN` di `.env`). Setelah frontend live di Vercel:
1. Balik ke Railway/Render → **Variables** → update `FRONTEND_ORIGIN` jadi URL Vercel kamu (`https://trading-fellah.vercel.app`, tanpa trailing slash).
2. Redeploy backend (Railway/Render biasanya auto-redeploy begitu env var berubah).

---

## 4. Checklist lengkap environment variables

Isi semua ini di **Railway/Render** (backend). Yang bertanda 🌐 juga perlu di **Vercel** (frontend).

| Variable | Dari mana | Wajib? |
|---|---|---|
| `ENV` | isi `production` | ✅ |
| `FRONTEND_ORIGIN` | URL Vercel kamu | ✅ |
| `JWT_SECRET` | generate: `python3 -c "import secrets; print(secrets.token_hex(32))"` | ✅ |
| `CREDENTIAL_ENCRYPTION_KEY` | generate: `python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"` | ✅ **backup di tempat aman** |
| `SUPABASE_URL` | Supabase → Project Settings → API | ✅ |
| `SUPABASE_SERVICE_ROLE_KEY` | Supabase → Project Settings → API (`service_role`) | ✅ |
| `METAAPI_TOKEN` | metaapi.cloud dashboard | ✅ (buat fitur MT5) |
| `AI_PROVIDER` | `anthropic` atau `openai` | ✅ |
| `ANTHROPIC_API_KEY` / `OPENAI_API_KEY` | console.anthropic.com / platform.openai.com | ✅ (salah satu) |
| `NEWS_API_KEY` | finnhub.io | opsional (buat news sentiment) |
| `NOWPAYMENTS_API_KEY` | nowpayments.io → Store Settings | ✅ (buat billing) |
| `NOWPAYMENTS_IPN_SECRET` | nowpayments.io → aktifkan IPN | ✅ (buat billing) |
| 🌐 `VITE_API_URL` | URL backend Railway/Render | ✅ (di Vercel) |

Setelah semua keisi, redeploy backend sekali lagi biar semua env var kepakai.

---

## 5. Webhook NOWPayments (biar pembayaran auto-aktifin subscription)

1. Login ke dashboard [nowpayments.io](https://nowpayments.io).
2. **Store Settings** → **Instant Payment Notifications (IPN)**.
3. Set **IPN Callback URL** ke: `https://<domain-backend-kamu>/api/billing/webhook`.
4. Generate/copy **IPN Secret Key**, masukin ke `NOWPAYMENTS_IPN_SECRET` di env var backend.
5. Test: bikin pembayaran kecil (atau pakai mode sandbox NOWPayments kalau ada), cek tabel `payments` di Supabase Table Editor — status harus update dari `waiting` → `finished`, dan tabel `subscriptions` user itu jadi `active`.

---

## 6. Cek akhir — smoke test sebelum kasih ke user

Jalanin urutan ini buat mastiin semua tersambung bener:

1. **Buka frontend Vercel** → klik Connect Wallet → tanda tangan pesan di
   MetaMask → harus masuk ke Dashboard (bukan stuck di halaman login).
   *Kalau gagal*: cek Network tab browser, lihat request ke `/api/auth/nonce`
   gagal atau kena CORS — berarti `FRONTEND_ORIGIN` di backend belum sesuai.
2. **Tautkan akun MT5** (demo account dulu buat testing) → status harus
   berubah jadi `connected`. *Kalau gagal*: cek log Railway/Render, biasanya
   `METAAPI_TOKEN` salah atau login/password/server MT5 salah ketik.
3. **Dashboard** harus nampilin balance/equity dari akun demo tadi (bukan 0
   semua / error).
4. **Halaman Automation** → nyalain Forward Test buat 1 simbol → tunggu
   5-10 menit → cek tabel `trades` di Supabase (filter `is_forward_test =
   true`) — harus mulai keisi begitu sistem nemu sinyal.
5. **Billing** → coba klik "Bayar dengan Crypto" salah satu plan → harus
   ke-redirect ke halaman invoice NOWPayments (bukan error).
6. Baru setelah semua di atas ijo, pertimbangkan buka ke user beneran.

---

## 7. (Opsional) Kalau tetap mau backend di Vercel juga

Kalau ini cuma buat demo/prototype dulu (BUKAN buat live auto-trade beneran
jalan otomatis), backend bisa dipaksa ke Vercel dengan catatan:

1. Root project butuh `vercel.json` nunjuk ke `backend/main.py` sebagai
   Python entrypoint (Vercel auto-detect FastAPI kalau `requirements.txt`
   ketemu).
2. **Live auto-trade, forward test otomatis, dan news refresh berkala TIDAK
   akan jalan** kecuali kamu upgrade ke Vercel **Pro** ($20/bln) DAN ubah
   4 job APScheduler di `main.py` jadi endpoint API yang dipanggil lewat
   **Vercel Cron** (`vercel.json` → key `crons`, tiap entry manggil 1 route,
   diverifikasi pakai header `Authorization: Bearer $CRON_SECRET` yang
   Vercel set otomatis).
3. Trading manual (buka/tutup order lewat tombol di halaman Trade) tetap
   bisa jalan normal karena itu request langsung, bukan scheduler.

Kalau kamu mau jalan opsi ini, bilang aja — aku bisa bikinin `vercel.json` +
refactor scheduler jadi endpoint cron-triggered.
