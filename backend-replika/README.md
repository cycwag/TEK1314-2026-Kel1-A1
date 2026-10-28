# GeoSync — Backend Replika (Firebase Realtime Database)

Backend replika untuk GeoSync, modul traktor pertanian otonom. Proyek ini mensimulasikan alur telemetri perangkat IoT, remote control, dan perencanaan lintasan pembajakan untuk PBL Keamanan Siber TEK1314 menggunakan **Firebase Realtime Database** (project replika terpisah dari produksi).

## Fitur

- Penyimpanan Cloud Real-time: seluruh node (`/telemetry`, `/commands`, `/routes`) disimpan langsung ke Firebase Realtime Database via `firebase-admin`.
- Telemetri mesin: suhu, RPM, koordinat GPS, kecepatan, heading, dan bahan bakar.
- Thermal management otomatis: `normal` di bawah 95 C, `warning` 95-105 C, `critical` di atas 105 C.
- Remote command: engine start/stop, cooling on/off, dan emergency stop.
- Engine start sequence: decompression engage, crank start, crank stop, decompression release.
- Rute pembajakan: validasi waypoint dan perhitungan jarak Haversine.
- Dashboard web read-only yang refresh otomatis setiap 3 detik.

## Kontrol Keamanan (Kategori C — Data & Application)

1. **Kredensial tidak hardcoded:** `API_KEY`, `FIREBASE_DB_URL`, dan `FIREBASE_CRED_PATH` dibaca dari `.env` melalui `os.getenv`. File kunci `serviceAccountKey.json` dan `.env` masuk `.gitignore`.
2. **Perbandingan API key timing-safe:** menggunakan `secrets.compare_digest`.
3. **Validasi input ketat:** seluruh field telemetri divalidasi tipe dan rentangnya; command dibatasi allowlist; ukuran body dibatasi 64 KB.
4. **Logging aktivitas mencurigakan:** payload invalid, command asing, dan request tanpa API key dicatat sebagai `[SUSPICIOUS]`.

Catatan: dashboard `/` dan `/dashboard/data` sengaja read-only tanpa API key. Endpoint `/api/*` tetap memerlukan header `X-API-Key`.

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
    └── dashboard.html
```

## Persiapan Database Firebase (Environment Replika)

1. Buka [Firebase Console](https://console.firebase.google.com/) dan buat project baru khusus replika (misal `geosync-replika`).
2. Masuk ke menu **Build -> Realtime Database -> Create Database**, lalu salin URL database (contoh: `https://geosync-replika-default-rtdb.asia-southeast1.firebasedatabase.app`).
3. Masuk ke **Project Settings (ikon gerigi) -> Service accounts -> Python -> Generate new private key**.
4. Simpan file JSON yang terunduh dengan nama `serviceAccountKey.json` di dalam folder `backend-replika/`.

## Setup di Ubuntu Server CLI (Target-Node)

Pastikan VM Target-Node memiliki koneksi internet (Adapter 2: NAT di VirtualBox) agar dapat menghubungi Firebase Cloud.

```bash
sudo apt update
sudo apt install -y git python3-pip python3-venv
git clone https://github.com/cycwag/KELOMPOK1-KEAMANANSIBER.git
cd KELOMPOK1-KEAMANANSIBER/backend-replika
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Generate API key baru dan edit `.env`:

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(24))"
nano .env
```

Isi `.env`:

```env
API_KEY=isi_dengan_hasil_generate
FIREBASE_DB_URL=https://nama-project-default-rtdb.asia-southeast1.firebasedatabase.app
FIREBASE_CRED_PATH=serviceAccountKey.json
```

Salin file `serviceAccountKey.json` dari laptop host ke Target-Node CLI menggunakan `scp` (jalankan dari terminal laptop host):

```powershell
scp serviceAccountKey.json admin@192.168.10.20:/home/admin/KELOMPOK1-KEAMANANSIBER/backend-replika/
```

Atau buat langsung di CLI Target-Node dengan `nano serviceAccountKey.json` lalu paste isi JSON-nya, kemudian kunci permission file:

```bash
chmod 600 .env serviceAccountKey.json
python3 app.py
```

## Setup di Windows (Laptop Lokal)

```powershell
git clone https://github.com/cycwag/KELOMPOK1-KEAMANANSIBER.git
cd KELOMPOK1-KEAMANANSIBER\backend-replika
py -3 -m venv venv
.\venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
notepad .env
# Taruh serviceAccountKey.json di folder ini
.\venv\Scripts\python.exe app.py
```

## Endpoint API

| Method | Endpoint | API key | Fungsi |
|---|---|---|---|
| GET | `/` | tidak | Dashboard web |
| GET | `/dashboard/data` | tidak | Data read-only dashboard |
| POST | `/api/telemetry` | ya | Kirim telemetri ke Firebase `/telemetry` |
| GET | `/api/telemetry/history?limit=20` | ya | Riwayat telemetri dari Firebase |
| POST | `/api/command` | ya | Kirim remote command ke Firebase `/commands` |
| POST | `/api/route` | ya | Simpan rute pembajakan ke Firebase `/routes` |
| GET | `/api/status` | ya | Status terakhir perangkat |

### Contoh Pengujian cURL

```bash
# Request valid (201)
curl -X POST http://192.168.10.20:5000/api/telemetry \
  -H "X-API-Key: <API_KEY>" \
  -H "Content-Type: application/json" \
  -d '{"engine_temp_c":92.5,"rpm":1450,"latitude":-6.9147,"longitude":107.6098,"speed_kmh":4.2,"heading_deg":87,"fuel_pct":63.5}'

# Tanpa API key (401 + log [SUSPICIOUS])
curl -X POST http://192.168.10.20:5000/api/telemetry \
  -H "Content-Type: application/json" \
  -d '{"engine_temp_c":92.5,"rpm":1450,"latitude":-6.9147,"longitude":107.6098,"speed_kmh":4.2,"heading_deg":87,"fuel_pct":63.5}'

# Payload tidak valid (400 + log [SUSPICIOUS])
curl -X POST http://192.168.10.20:5000/api/telemetry \
  -H "X-API-Key: <API_KEY>" \
  -H "Content-Type: application/json" \
  -d '{"engine_temp_c":92.5,"rpm":1450,"latitude":999,"longitude":107.6098,"speed_kmh":4.2,"heading_deg":87,"fuel_pct":63.5}'
```
