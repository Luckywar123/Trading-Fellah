# CARA DEPLOY ULANG (v3)

Arsitektur: **frontend (Vite/React) -> Vercel**, **backend (FastAPI) -> Render atau Railway**.
Backend TIDAK bisa di Vercel karena punya scheduler (auto-trade, forward test, news) yang
butuh proses long-running, dan MetaApi pakai koneksi websocket.

## 1. Timpa project
Extract arsip ini ke folder repo kamu (timpa). Lalu hapus `.venv` dari git:

    git rm -r --cached .venv
    git add -A && git commit -m "fix: deploy config, backend hardening, ai chat" && git push

## 2. Backend (Render atau Railway)
- Render: New + -> Blueprint -> pilih repo (pakai `render.yaml`). Railway: New Project -> Deploy repo (pakai `railway.json`).
- Isi env var dari `.env.example`. WAJIB: `ENV=production`, `FRONTEND_ORIGIN`, `JWT_SECRET` (min 32 char),
  `CREDENTIAL_ENCRYPTION_KEY`, `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `METAAPI_TOKEN`, `ANTHROPIC_API_KEY`.
- Di production backend sengaja menolak start kalau secret fatal kosong; cek log deploy kalau gagal boot.
- Jalankan `supabase/schema.sql` di Supabase SQL Editor (kalau belum).
- Cek: buka `https://<url-backend>/api/health` -> `{"status":"online"}`.
- Jangan scale > 1 instance dan jangan pakai free tier yang sleep (scheduler berhenti / order bisa dobel).

## 3. Frontend (Vercel)
- Vercel -> Settings -> Environment Variables: `VITE_API_URL` = URL backend (tanpa slash).
- Root Directory boleh kosong ATAU `frontend`; dua-duanya sudah didukung (`vercel.json` ada di root dan di `frontend/`).
- **Redeploy** setelah set env var (nilai VITE_* masuk saat build).

## 4. Balik ke backend
Set `FRONTEND_ORIGIN` = URL Vercel final (persis, tanpa slash). Kalau pakai domain custom / preview,
isi `CORS_EXTRA_ORIGINS` (pisah koma) atau `CORS_ORIGIN_REGEX`.

## Yang berubah di versi ini
- vercel.json: tambah SPA rewrites (refresh di /dashboard dst. tadinya 404) + cache aset.
- `.venv` (874 file Windows) dihapus dari repo; kode bot lama dipindah ke `legacy/`
  (root `requirements.txt` lama berisi `asyncio==3.4.3` + tensorflow yang merusak deteksi Python).
- Backend: CORS multi-origin, validasi config production, lifespan (ganti on_event), healthcheck,
  Dockerfile pakai `$PORT` + non-root + 1 worker, render.yaml, railway.json.
- MetaApi: retry khusus operasi baca, circuit breaker per akun, order TIDAK di-retry (cegah order dobel).
- AI: panggilan LLM tidak lagi memblokir server, retry 3x, fallback rule-based untuk berita,
  endpoint baru `POST /api/ai/chat` (login wajib, rate limit 15/menit) + widget "Asisten AI" di dashboard.
- Frontend: bundle dipecah (906 KB -> 93 KB chunk utama), peringatan jika VITE_API_URL belum di-set.
- 8 smoke test: `pip install pytest && pytest backend/tests`.
