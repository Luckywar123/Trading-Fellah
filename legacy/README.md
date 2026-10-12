# legacy/

Kode bot trading generasi pertama (src/, config/, database.py, scripts/, web/).
BUKAN bagian dari web app yang sekarang (backend/ + frontend/), dipindah ke sini
supaya platform deploy (Vercel/Railway/Render) tidak salah deteksi root repo
sebagai project Python berisi tensorflow, dan supaya `asyncio==3.4.3` (paket
usang yang merusak pip di Python 3) tidak ikut ter-install.

Jalankan dari dalam folder ini kalau masih mau dipakai:
    cd legacy && pip install -r requirements-legacy.txt
