# GeoSync — Backend Replika (Firebase Realtime Database)

Backend replika untuk GeoSync, modul traktor pertanian otonom. Proyek ini mensimulasikan alur telemetri perangkat IoT, remote control, perencanaan lintasan pembajakan, dan autentikasi multi-role (User & Admin) untuk PBL Keamanan Siber TEK1314 menggunakan **Full Firebase Realtime Database (NoSQL Cloud)** tanpa database lokal dan tanpa kredensial hardcoded.

## Fitur

- **Full Firebase Realtime Database:** seluruh node (`/telemetry`, `/commands`, `/routes`, `/users`) disimpan dan dibaca langsung dari Firebase Cloud.
- **Autentikasi Multi-Role Dinamis:**
  - **Role `admin`:** Akses monitoring telemetri penuh, tombol kendali remote traktor (`engine_start`, `cooling_on/off`, `emergency_stop`), dan tabel manajemen akun dari Firebase `/users`.
  - **Role `user`:** Akses monitoring lapangan read-only (telemetri & rute lintasan).
  - Penambahan/perubahan user langsung di Firebase Console seketika aktif tanpa perlu restart server.
- **Telemetri Mesin:** suhu mesin, RPM, koordinat GPS, kecepatan, heading, dan bahan bakar.
- **Thermal Management Otomatis:** status `normal` (<95 C), `warning` (95-105 C), `critical` (>105 C) dengan aktivasi pendingin otomatis.
- **Remote Engine Start Sequence:** simulasi otomatis pemutar engkol (`crank`) dan tuas dekompresi elektronik.
- **Rute Pembajakan:** validasi waypoint dan perhitungan jarak Haversine.

## Kontrol Keamanan (Kategori C — Data & Application)

1. **Kredensial Tidak Hardcoded:** Tidak ada akun atau password di dalam source code Python (`app.py`). Kunci API (`API_KEY`), URL database (`FIREBASE_DB_URL`), dan path kunci akun layanan (`FIREBASE_CRED_PATH`) dibaca dari `.env`. File rahasia `.env` dan `serviceAccountKey.json` dimasukkan ke `.gitignore`.
2. **Perbandingan API Key Timing-Safe:** Endpoint API dilindungi autentikasi header `X-API-Key` dengan `secrets.compare_digest`.
3. **Validasi Input Ketat:** Seluruh field telemetri divalidasi tipe data dan rentang fisik; perintah remote dibatasi allowlist; batas ukuran payload request 64 KB.
4. **Logging Aktivitas Mencurigakan:** Request tanpa API key, login gagal, perintah asing, dan payload di luar batas rentang otomatis dicatat dengan tag `[SUSPICIOUS]`/`[AUTH-FAIL]`.

## Struktur Folder

```text
backend-replika/
├── app.py
├── requirements.txt
├── .env.example
├── .env                     # dibuat lokal, TIDAK di-commit
├── serviceAccountKey.json   # diunduh dari Firebase, TIDAK di-commit
├── .gitignore
├── README.md
└── templates/
    ├── login.html
    └── dashboard.html
```

## Persiapan Database Firebase

1. Buka [Firebase Console](https://console.firebase.google.com/) -> project replika Anda.
2. Di menu **Build -> Realtime Database**, pastikan database aktif dan salin URL database (contoh: `https://geosync-d79da-default-rtdb.asia-southeast1.firebasedatabase.app`).
3. Masuk ke **Project Settings -> Service accounts -> Python -> Generate new private key**.
4. Simpan file JSON hasil unduhan dengan nama `serviceAccountKey.json` di dalam folder `backend-replika/`.
5. Di tab **Data** pada Realtime Database, pastikan struktur `/users` sudah tersedia (berisi akun `admin`, `kelompok1`, dll.).

## Setup di Ubuntu Server CLI (Target-Node)

Pastikan VM Target-Node memiliki akses internet (misal via Adapter 2: NAT di VirtualBox) untuk berkomunikasi dengan Firebase Cloud.

```bash
sudo apt update
sudo apt install -y git python3-pip python3-venv
git clone https://github.com/cycwag/TEK1314-2026-Kel1-A1.git
cd TEK1314-2026-Kel1-A1/backend-replika
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Isi `.env` dan letakkan file kunci:

```bash
nano .env
# Masukkan API_KEY, SECRET_KEY, dan FIREBASE_DB_URL
nano serviceAccountKey.json
# Paste isi kunci JSON dari Firebase
chmod 600 .env serviceAccountKey.json
python3 app.py
```

## Setup di Windows (Laptop Host)

```powershell
git clone https://github.com/cycwag/TEK1314-2026-Kel1-A1.git
cd TEK1314-2026-Kel1-A1\backend-replika
py -3 -m venv venv
.\venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
notepad .env
# Taruh serviceAccountKey.json di folder ini
.\venv\Scripts\python.exe app.py
```

Akses portal web melalui browser di: `http://localhost:5000/login`

## Endpoint API & Web

| Method | Endpoint | Akses | Fungsi |
|---|---|---|---|
| GET/POST | `/login` | Publik | Halaman & proses autentikasi Firebase NoSQL |
| GET | `/logout` | Session | Mengakhiri sesi login |
| GET | `/` | Session (User/Admin) | Dashboard GeoSync Control Center |
| GET | `/dashboard/data` | Session | Data telemetri & users untuk dashboard |
| POST | `/api/telemetry` | `X-API-Key` / Admin | Mengirim telemetri traktor ke Firebase `/telemetry` |
| GET | `/api/telemetry/history` | `X-API-Key` / Admin | Mengambil riwayat telemetri dari Firebase |
| POST | `/api/command` | `X-API-Key` / Admin | Mengirim perintah remote ke Firebase `/commands` |
| POST | `/api/route` | `X-API-Key` / Admin | Menyimpan rute pembajakan ke Firebase `/routes` |
| GET | `/api/users` | `X-API-Key` / Admin | Mendapatkan daftar pengguna dari Firebase `/users` |
| GET | `/api/status` | `X-API-Key` / Admin | Mengambil status perangkat terakhir |
