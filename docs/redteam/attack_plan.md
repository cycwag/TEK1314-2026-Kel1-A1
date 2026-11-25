# Attack Plan — Rencana Simulasi Serangan Red Team

**Proyek:** GeoSync IoT Backend Replika — PBL Keamanan Siber (TEK1314)  
**Attacker-Node:** Kali Linux (`192.168.10.10`)  
**Target-Node:** Ubuntu Server — GeoSync Backend Replika (`192.168.10.20`)  
**Monitoring-Node:** Security Onion IDS (`192.168.10.30`)

> **Prinsip Etika & Ruang Lingkup:** Seluruh skenario serangan hanya dijalankan di dalam jaringan internal laboratorium (`intnet-pbl` / `192.168.10.0/24`) terhadap **Target-Node Replika**, bukan terhadap perangkat traktor otonom GeoSync asli milik Mitra.

---

## Ringkasan Skenario Serangan

| ID | Nama Skenario | MITRE ATT&CK | Tools Utama | Target Layanan / Port | Tujuan Pengujian |
|---|---|---|---|---|---|
| **Skenario 1** | Network & Service Reconnaissance | `T1046` (Network Service Discovery) | `nmap` | Seluruh port TCP (`1-65535`), khususnya `22/tcp`, `80/tcp`, `5000/tcp` | Memetakan port terbuka, mengidentifikasi versi layanan (OpenSSH, Nginx, Flask), dan melakukan OS fingerprinting |
| **Skenario 2** | SSH Credential Brute-Force | `T1110.001` (Brute Force: Password Guessing) | `hydra` | OpenSSH (`22/tcp`), akun `bagas` & `root` | Menguji ketahanan autentikasi SSH terhadap serangan kamus (*dictionary attack*) dan memicu mekanisme pemblokiran otomatis |
| **Skenario 3** | Web & IoT API Exploitation (Unauthorized Telemetry, Payload Anomaly, Web Login Brute-Force) | `T1190` (Exploit Public-Facing Application) & `T1110` (Brute Force) | `curl`, Bash Loop | Nginx/Flask HTTP (`80/tcp`): `POST /api/telemetry` & `POST /login` | Menguji penolakan request tanpa `X-API-Key`, ketahanan validasi input terhadap injeksi data sensor ekstrem, serta ketahanan endpoint `/login` terhadap brute-force |

---

## Detail Skenario 1 — Network & Service Reconnaissance

### 1. Objektif
Mengidentifikasi permukaan serangan (*attack surface*) pada Target-Node `192.168.10.20`, termasuk port layanan yang tidak semestinya terekspos dan informasi versi perangkat lunak pada banner layanan.

### 2. Langkah Eksekusi (Attacker-Node `192.168.10.10`)
```bash
export TARGET=192.168.10.20

# 1. TCP SYN Scan + Service/Version Detection + OS Fingerprinting
sudo nmap -sS -sV -O "$TARGET"

# 2. Full TCP Port Scan (seluruh 65535 port)
sudo nmap -p- "$TARGET"
```

### 3. Hasil yang Diharapkan (*Expected*) vs Aktual
* **Sebelum Hardening:** Port `22/tcp` (OpenSSH), `80/tcp` (Nginx), dan port internal bila belum ditutup terlihat `open` beserta nomor versi lengkap pada header HTTP.
* **Deteksi Blue Team:** Security Onion menangkap lonjakan paket SYN dan memunculkan alert Sguil `ET SCAN Nmap Scripting Engine` / `ET SCAN Suspicious inbound`.
* **Setelah Hardening (UFW + `server_tokens off`):** Hanya port `22/tcp` dan `80/tcp` yang `open` (port `5000/tcp` tertutup/filtered), serta header `curl -I http://192.168.10.20` hanya menampilkan `Server: nginx` tanpa versi.

---

## Detail Skenario 2 — SSH Credential Brute-Force

### 1. Objektif
Menguji apakah layanan akses jarak jauh SSH pada Target-Node dapat ditembus menggunakan daftar kata sandi umum (*wordlist*) dan apakah sistem mampu mendeteksi serta memutus koneksi penyerang secara otomatis.

### 2. Langkah Eksekusi (Attacker-Node `192.168.10.10`)
```bash
# 1. Membuat wordlist kata sandi umum
cat > pass.txt <<'EOF'
123456
password
admin
root
toor
letmein
qwerty
EOF

# 2. Menjalankan brute-force SSH dengan Hydra (4 thread paralel)
hydra -l bagas -P pass.txt ssh://192.168.10.20 -t 4 -V
```

### 3. Hasil yang Diharapkan (*Expected*) vs Aktual
* **Sebelum Hardening:** Hydra dapat mencoba seluruh isi `pass.txt` tanpa hambatan hingga menemukan password yang valid.
* **Deteksi Blue Team:**
  * Security Onion Sguil memunculkan Alert ID `5.1278` (`ET SCAN LibSSH Based Frequent SSH Connections Likely Brute Force`).
  * `/var/log/auth.log` pada Target-Node mencatat rentetan `Failed password for bagas from 192.168.10.10`.
* **Setelah Hardening (PAM `pwquality` + `PermitRootLogin no` + `Fail2ban`):** Setelah 3 kali kegagalan dalam 300 detik, Fail2ban memblokir IP `192.168.10.10` selama 600 detik (`Banned IP list: 192.168.10.10`), sehingga koneksi Hydra ke-4 langsung ditolak (`Connection reset by peer`).

---

## Detail Skenario 3 — Web & IoT API Exploitation

### 1. Objektif
Menguji tiga vektor serangan pada lapisan aplikasi GeoSync Control Center (`http://192.168.10.20`):
1. **3a — Unauthorized Telemetry Injection:** Mengirim data telemetri palsu ke `/api/telemetry` tanpa header `X-API-Key`.
2. **3b — Anomalous Sensor Payload Injection:** Mengirim data sensor di luar batas fisik traktor (`engine_temp_c: 999`, `rpm: 9000`, `fuel_pct: 200`) menggunakan API key untuk mengacaukan logika *thermal management*.
3. **3c — Web Login Brute-Force:** Melakukan percobaan login berulang secara cepat pada endpoint `POST /login` untuk akun `admin`.

### 2. Langkah Eksekusi (Attacker-Node `192.168.10.10`)
```bash
export TARGET=192.168.10.20
export API_KEY='<API_KEY_REDACTED>'

# 3a. Request telemetri tanpa API key
curl -i -X POST "http://$TARGET/api/telemetry" \
  -H "Content-Type: application/json" \
  -d '{"engine_temp_c":92.5,"rpm":1450,"latitude":-6.9147,"longitude":107.6098,"speed_kmh":4.2,"heading_deg":87,"fuel_pct":63.5}'

# 3b. Injeksi payload sensor ekstrem/anomali
curl -i -X POST "http://$TARGET/api/telemetry" \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"engine_temp_c":999,"rpm":9000,"latitude":999,"longitude":999,"speed_kmh":500,"heading_deg":999,"fuel_pct":200}'

# 3c. Brute-force endpoint autentikasi web /login
for pass in 123456 password admin root toor letmein qwerty; do
  echo -n "Coba password [$pass]: "
  curl -s -o /dev/null -w "HTTP %{http_code}\n" -X POST "http://$TARGET/login" \
    -H "Content-Type: application/json" \
    -d "{\"username\":\"admin\",\"password\":\"$pass\"}"
done
```

### 3. Hasil yang Diharapkan (*Expected*) vs Aktual
* **Sebelum Mitigasi Rate-Limit:**
  * Sub-skenario 3a ditolak dengan HTTP `401` (`{"error":"unauthorized"}`).
  * Sub-skenario 3b ditolak dengan HTTP `400` (`{"error":"nilai engine_temp_c tidak valid"}`).
  * Sub-skenario 3c berhasil mencoba seluruh kandidat password pada `/login` dengan respons `401` beruntun (atau `200` jika password tertebak) karena belum ada pembatasan laju request (*rate limiting*).
* **Deteksi Blue Team:**
  * Log systemd `journalctl -u backend` mencatat tag `[SUSPICIOUS] unauthorized`, `[SUSPICIOUS] nilai engine_temp_c tidak valid`, dan rentetan `[AUTH-FAIL] login gagal dari 192.168.10.10 untuk user='admin'`.
  * Security Onion Sguil mendeteksi aktivitas `ET POLICY curl User-Agent`.
* **Setelah Hardening (Nginx `limit_req_zone` `5r/m` `burst=3 nodelay`):**
  * Pengujian 8 request beruntun ke `POST /login` hanya meneruskan 4 request pertama ke Flask (`401`), sementara request ke-5 hingga ke-8 langsung diblokir oleh Nginx dengan HTTP `503 Service Temporarily Unavailable`.
  * Endpoint `/api/telemetry` untuk perangkat IoT sah tetap berjalan normal (`HTTP 201 Created`).
