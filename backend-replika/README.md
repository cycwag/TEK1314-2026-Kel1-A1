# GeoSync — Backend Replika

Backend replika untuk GeoSync, modul traktor pertanian otonom. Proyek ini mensimulasikan alur telemetri perangkat IoT, remote control, dan perencanaan lintasan pembajakan untuk PBL Keamanan Siber TEK1314.

Bukan sistem produksi. Data disimpan lokal di SQLite dan API dijalankan dengan Flask development server.

## Fitur

- Telemetri mesin: suhu, RPM, koordinat GPS, kecepatan, heading, dan bahan bakar.
- Thermal management otomatis: `normal` di bawah 95 C, `warning` 95-105 C, `critical` di atas 105 C.
- Remote command: engine start/stop, cooling on/off, dan emergency stop.
- Engine start sequence: decompression engage, crank start, crank stop, decompression release.
- Rute pembajakan: validasi waypoint dan perhitungan jarak Haversine.
- Dashboard web read-only yang refresh otomatis setiap 3 detik.
- Database dan tabel dibuat otomatis saat server pertama kali dijalankan.

## Kontrol Keamanan

- API key dibaca dari `.env` melalui `os.getenv`, tidak ditanam di source code.
- Perbandingan API key menggunakan `secrets.compare_digest`.
- Seluruh field telemetri divalidasi tipe dan rentangnya.
- Command hanya boleh dari allowlist.
- Payload invalid, command asing, dan request tanpa API key dicatat sebagai `[SUSPICIOUS]`.
- Ukuran body request dibatasi 64 KB.
- Query database menggunakan parameterized statement.

Catatan: dashboard `/` dan `/dashboard/data` sengaja read-only tanpa API key. Endpoint `/api/*` tetap memerlukan header `X-API-Key`. Jangan mengekspos port 5000 ke internet.

## Struktur

```text
backend-replika/
├── app.py
├── requirements.txt
├── .env.example
├── .env              # dibuat lokal, tidak di-commit
├── .gitignore
├── README.md
├── templates/
│   └── dashboard.html
└── database.db       # dibuat otomatis, tidak di-commit
```

## Prasyarat

- Python 3.9 atau lebih baru
- pip
- Git

## Setup Windows

```powershell
git clone https://github.com/cycwag/KELOMPOK1-KEAMANANSIBER.git
cd KELOMPOK1-KEAMANANSIBER\backend-replika
py -3 -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
python -c "import secrets; print(secrets.token_urlsafe(24))"
notepad .env
python app.py
```

Jika aktivasi venv diblokir execution policy:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\venv\Scripts\Activate.ps1
```

Alternatif tanpa aktivasi:

```powershell
.\venv\Scripts\python.exe -m pip install -r requirements.txt
.\venv\Scripts\python.exe app.py
```

## Setup Linux / Target-Node

```bash
sudo apt update
sudo apt install -y git python3-pip python3-venv
git clone https://github.com/cycwag/KELOMPOK1-KEAMANANSIBER.git
cd KELOMPOK1-KEAMANANSIBER/backend-replika
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python -c "import secrets; print(secrets.token_urlsafe(24))"
nano .env
python app.py
```

## Konfigurasi `.env`

Isi `.env` dengan API key sendiri:

```env
API_KEY=hasil_generate
```

Jangan commit `.env`. File `.env.example` hanya berisi placeholder.

## Menjalankan

```powershell
.\venv\Scripts\python.exe app.py
```

Server berjalan di `http://localhost:5000` dan mendengarkan di `0.0.0.0:5000`. Buka dashboard di browser:

```text
http://localhost:5000
```

Dashboard langsung menampilkan data tanpa API key. Endpoint API tetap memerlukan header `X-API-Key`.

## Endpoint API

| Method | Endpoint | API key | Fungsi |
|---|---|---|---|
| GET | `/` | tidak | Dashboard web |
| GET | `/dashboard/data` | tidak | Data read-only dashboard |
| POST | `/api/telemetry` | ya | Kirim telemetri |
| GET | `/api/telemetry/history?limit=20` | ya | Riwayat telemetri |
| POST | `/api/command` | ya | Kirim remote command |
| POST | `/api/route` | ya | Simpan rute pembajakan |
| GET | `/api/status` | ya | Status terakhir perangkat |

### Field telemetri

Semua field wajib diisi.

| Field | Tipe | Rentang |
|---|---|---|
| `engine_temp_c` | number | -20 sampai 150 |
| `rpm` | number | 0 sampai 3000 |
| `latitude` | number | -90 sampai 90 |
| `longitude` | number | -180 sampai 180 |
| `speed_kmh` | number | 0 sampai 25 |
| `heading_deg` | number | 0 sampai 360 |
| `fuel_pct` | number | 0 sampai 100 |

Status thermal dihitung server:

- `< 95` C: `normal`
- `95-104.9` C: `warning`
- `>= 105` C: `critical`, `cooling_active` otomatis `true`

### Command yang diizinkan

- `engine_start`
- `engine_stop`
- `cooling_on`
- `cooling_off`
- `emergency_stop`

### Contoh telemetri (PowerShell)

```powershell
$key = "isi-api-key"
$headers = @{ "X-API-Key" = $key }
$body = @{
  engine_temp_c = 92.5
  rpm = 1450
  latitude = -6.9147
  longitude = 107.6098
  speed_kmh = 4.2
  heading_deg = 87
  fuel_pct = 63.5
} | ConvertTo-Json

Invoke-RestMethod -Uri http://localhost:5000/api/telemetry -Method Post `
  -Headers $headers -ContentType "application/json" -Body $body
```

### Contoh command

```powershell
Invoke-RestMethod -Uri http://localhost:5000/api/command -Method Post `
  -Headers $headers -ContentType "application/json" `
  -Body '{"command":"engine_start"}'
```

### Contoh rute

```powershell
Invoke-RestMethod -Uri http://localhost:5000/api/route -Method Post `
  -Headers $headers -ContentType "application/json" `
  -Body '{"name":"Lahan A","waypoints":[[-6.9147,107.6098],[-6.915,107.6105],[-6.9155,107.6112]]}'
```

### Contoh cURL (Linux)

```bash
curl -X POST http://localhost:5000/api/telemetry \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"engine_temp_c":92.5,"rpm":1450,"latitude":-6.9147,"longitude":107.6098,"speed_kmh":4.2,"heading_deg":87,"fuel_pct":63.5}'
```

## Testing Cepat

| Skenario | Expected |
|---|---|
| Telemetri valid | `201` |
| Command valid | `202` |
| Rute valid | `201` |
| Telemetri/command/rute invalid | `400` |
| Tanpa `X-API-Key` | `401` |

Cek status tanpa API key:

```powershell
curl.exe -i http://localhost:5000/api/status
```

Cek status dengan API key:

```powershell
Invoke-RestMethod -Uri http://localhost:5000/api/status -Headers $headers | ConvertTo-Json -Depth 5
```

## Deploy Opsional dengan systemd

Contoh unit `/etc/systemd/system/backend-replika.service`:

```ini
[Unit]
Description=GeoSync Backend Replika
After=network.target

[Service]
User=admin
WorkingDirectory=/home/admin/KELOMPOK1-KEAMANANSIBER/backend-replika
ExecStart=/home/admin/KELOMPOK1-KEAMANANSIBER/backend-replika/venv/bin/python app.py
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

Aktifkan:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now backend-replika
sudo systemctl status backend-replika
```

## Troubleshooting

| Masalah | Solusi |
|---|---|
| `RuntimeError: API_KEY belum diset` | Buat `.env` dari `.env.example` dan isi `API_KEY`. |
| Dashboard menampilkan `Terputus` | Pastikan server berjalan di port 5000. |
| `401 unauthorized` | Header `X-API-Key` tidak ada atau nilainya salah. |
| Port 5000 dipakai proses lain | Hentikan proses tersebut atau ubah port di `app.py`. |
| `Activate.ps1 cannot be loaded` | Jalankan `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass`. |
| Data ingin direset | Hentikan server, hapus `database.db`, lalu jalankan lagi. |
