# Hardening Checklist — Baseline & Remediasi Target-Node (`192.168.10.20`)

**Proyek:** GeoSync IoT Backend Replika — PBL Keamanan Siber (TEK1314)  
**Target-Node:** Ubuntu Server (`bagas@kelompok1` / `192.168.10.20`)  
**Standar Acuan:** Standar Minimum Hardening Minggu ke-9 & Remediasi IoT Minggu ke-13 (Kategori A, B, dan C)

---

## Ringkasan Status Hardening

| Kategori | Fokus Kontrol | Jumlah Kontrol | Status Akhir |
|---|---|---|---|
| **Kategori A** | Host & Identity Hardening | 4 Kontrol (A1–A4) | **100% Terimplementasi & Terverifikasi** |
| **Kategori B** | Network & Service Hardening | 5 Kontrol (B1–B5) | **100% Terimplementasi & Terverifikasi** |
| **Kategori C** | Data & Application Hardening | 5 Kontrol (C1–C5) | **100% Terimplementasi & Terverifikasi** |

---

## Kategori A — Host & Identity Hardening

Detail pengujian awal tersedia pada [`hardening_kategori_A.md`](hardening_kategori_A.md).

| ID | Kontrol Keamanan | Konfigurasi / Perintah Utama | Kondisi Sebelum (*Before*) | Kondisi Sesudah (*After*) | Bukti Verifikasi | Status |
|---|---|---|---|---|---|---|
| **A1** | Penonaktifan Login Root via SSH | `PermitRootLogin no` pada `/etc/ssh/sshd_config` & restart `ssh` | Root berpotensi diakses via SSH jika password diketahui | Login SSH untuk `root` ditolak secara permanen | [`evidence/11_hardening2_ssh_permitrootlogin_and_fail2ban_config.jpg`](evidence/11_hardening2_ssh_permitrootlogin_and_fail2ban_config.jpg) (`permitrootlogin no`) | [x] Selesai |
| **A2** | Pemisahan Akun & Least Privilege Direktori | Pembuatan akun non-privilege `public`; direktori `/opt/shared-data` diset `chown root:root` dan `chmod 755` | Belum ada pemisahan uji tulis direktori bersama | User `public` tidak memiliki akses tulis ke `/opt/shared-data` | `su - public` lalu `touch /opt/shared-data/uji.txt` -> `Permission denied` | [x] Selesai |
| **A3** | Kebijakan Kompleksitas Kata Sandi (PAM) | Instalasi `libpam-pwquality`, konfigurasi `/etc/security/pwquality.conf`: `minlen=10`, `dcredit=-1`, `ucredit=-1`, `lcredit=-1`, `ocredit=-1` | Password pendek/lemah tanpa huruf kapital atau simbol dapat digunakan | Password baru wajib >= 10 karakter dengan kombinasi huruf besar, kecil, angka, simbol, dan tidak boleh sama dengan password lama | `passwd bagas` menolak password lama & password tanpa huruf kapital (`BAD PASSWORD`) hingga retry habis | [x] Selesai |
| **A4** | Pembaruan Paket & Unattended Upgrades | Verifikasi `unattended-upgrades.service` aktif dan `apt list --upgradable` | Perlu pemeriksaan status patch keamanan OS | Layanan `unattended-upgrades` berjalan aktif (`PID 718`), seluruh paket *up-to-date* (`Listing... Done`) | `systemctl status unattended-upgrades` & `apt list --upgradable` | [x] Selesai |

---

## Kategori B — Network & Service Hardening

Detail pengujian awal tersedia pada [`hardening_kategori_B.md`](hardening_kategori_B.md).

| ID | Kontrol Keamanan | Konfigurasi / Perintah Utama | Kondisi Sebelum (*Before*) | Kondisi Sesudah (*After*) | Bukti Verifikasi | Status |
|---|---|---|---|---|---|---|
| **B1** | Host Firewall Default Deny (UFW) | `ufw default deny incoming`, `ufw default allow outgoing`, `ufw allow 22/tcp`, `ufw allow 80/tcp`, `ufw enable` | Port internal (termasuk port development Flask `5000/tcp`) berisiko terbuka langsung ke jaringan | Hanya port `22/tcp` (SSH) dan `80/tcp` (Nginx HTTP) yang diizinkan masuk; `998` port lainnya `filtered` | [`evidence/10_hardening1_ufw_default_deny_and_nginx.jpg`](evidence/10_hardening1_ufw_default_deny_and_nginx.jpg) & [`evidence/05_after_recon_nmap_only_22_80.jpg`](evidence/05_after_recon_nmap_only_22_80.jpg) | [x] Selesai |
| **B2** | Penyembunyian Versi Web Server & Reverse Proxy | `server_tokens off;` pada `/etc/nginx/sites-available/geosync` dan `proxy_pass http://127.0.0.1:5000;` | Banner HTTP menampilkan versi detail Nginx/Werkzeug sehingga memudahkan pencarian CVE | Header respons HTTP hanya menampilkan `Server: nginx` tanpa nomor versi | [`evidence/14_hardening_final_verification_summary.jpg`](evidence/14_hardening_final_verification_summary.jpg) & [`evidence/06_after_recon_curl_header_nginx_no_version.jpg`](evidence/06_after_recon_curl_header_nginx_no_version.jpg) | [x] Selesai |
| **B3** | Proteksi Brute-Force SSH (Fail2ban) | Konfigurasi `/etc/fail2ban/jail.local` pada `[sshd]`: `enabled=true`, `maxretry=3`, `findtime=300`, `bantime=600` | Attacker dapat menjalankan dictionary attack Hydra hingga menemukan `password: 123` | Jail `sshd` aktif memantau `/var/log/auth.log`, otomatis mem-ban IP `192.168.10.10`, dan serangan ulang Hydra gagal (`0 valid password found`) | [`evidence/11_hardening2_ssh_permitrootlogin_and_fail2ban_config.jpg`](evidence/11_hardening2_ssh_permitrootlogin_and_fail2ban_config.jpg), [`evidence/12_hardening2_fail2ban_banned_ip_192_168_10_10.jpg`](evidence/12_hardening2_fail2ban_banned_ip_192_168_10_10.jpg), & [`evidence/08_after_ssh_hydra_zero_password_found.jpg`](evidence/08_after_ssh_hydra_zero_password_found.jpg) | [x] Selesai |
| **B4** | Penonaktifan Layanan Non-Esensial | `systemctl disable --now` pada `fwupd`, `ModemManager`, `multipathd`, `udisks2`, `upower` | 21 unit layanan aktif, termasuk 5 daemon hardware/desktop yang tidak dibutuhkan server | Jumlah layanan berjalan turun menjadi 16 unit layanan inti | `systemctl list-units --type=service --state=running` (16 loaded units) | [x] Selesai |
| **B5** | Rate Limiting Endpoint Login Web | Konfigurasi Nginx `limit_req_zone $binary_remote_addr zone=login_limit:10m rate=5r/m;` dan `limit_req zone=login_limit burst=3 nodelay;` pada `location /login` | Endpoint `POST /login` dapat menerima ribuan percobaan password beruntun | Request brute-force ke `/login` langsung diputus oleh Nginx dengan HTTP `503 Service Temporarily Unavailable` setelah melewati batas burst | [`evidence/13_hardening3_nginx_ratelimit_login_config.jpg`](evidence/13_hardening3_nginx_ratelimit_login_config.jpg) & [`evidence/09_after_web_login_ratelimit_401_503.jpg`](evidence/09_after_web_login_ratelimit_401_503.jpg) | [x] Selesai |

---

## Kategori C — Data & Application Hardening

Implementasi kode terdapat pada [`../../backend-replika/app.py`](../../backend-replika/app.py).

| ID | Kontrol Keamanan | Konfigurasi / Implementasi Kode | Kondisi Sebelum (*Before*) | Kondisi Sesudah (*After*) | Bukti Verifikasi | Status |
|---|---|---|---|---|---|---|
| **C1** | Eliminasi Hardcoded Credentials & Proteksi File Rahasia | `load_dotenv()`, pembacaan `API_KEY`, `SECRET_KEY`, `FIREBASE_DB_URL`, `FIREBASE_CRED_PATH` via `os.getenv()`, file `.env` & `serviceAccountKey.json` diset `chmod 600` serta masuk `.gitignore` | Kredensial berisiko terekspos di source code atau ter-commit ke repositori publik | Tidak ada secret hardcoded di `app.py`; file kredensial hanya dapat dibaca oleh owner (`-rw-------`) | `grep` secret pada `app.py` bersih; `ls -l .env serviceAccountKey.json` | [x] Selesai |
| **C2** | Autentikasi API Timing-Safe (`X-API-Key`) | Fungsi `authorized()` memvalidasi header `X-API-Key` menggunakan `secrets.compare_digest(provided, API_KEY)` | Endpoint telemetri/command rawan diakses tanpa otorisasi atau terkena timing attack | Request tanpa/salah `X-API-Key` ditolak dengan HTTP `401 Unauthorized` | `curl -i -X POST http://192.168.10.20/api/telemetry` tanpa key -> `401` | [x] Selesai |
| **C3** | Validasi Input Ketat & Allowlist Perintah | Validasi rentang fisik `TELEMETRY_RULES` (suhu -20..150 C, RPM 0..3000, GPS valid, fuel 0..100%), allowlist `ALLOWED_COMMANDS`, dan `MAX_CONTENT_LENGTH = 64 KB` | Data sensor palsu/anomali dapat merusak logika thermal management atau menyuntikkan perintah liar | Payload di luar batas fisik atau perintah di luar allowlist ditolak dengan HTTP `400 Bad Request` | `curl` dengan `engine_temp_c: 999` menghasilkan HTTP `400` (`nilai engine_temp_c tidak valid`) | [x] Selesai |
| **C4** | Application Security & Anomaly Logging | Pencatatan terstruktur ke `stdout`/systemd journal dengan tag `[SUSPICIOUS]`, `[AUTH-FAIL]`, `[AUTH-OK]`, dan `[THERMAL]` | Percobaan akses ilegal ke API tidak tercatat secara spesifik di level aplikasi | Setiap kegagalan autentikasi dan anomali payload tercatat lengkap dengan IP sumber dan alasan penolakan | `sudo journalctl -u backend` menampilkan log `[SUSPICIOUS]` dan `[AUTH-FAIL]` dari `192.168.10.10` | [x] Selesai |
| **C5** | Role-Based Access Control (RBAC) Berbasis Firebase | Pemisahan hak akses session `role=admin` vs `role=user` pada endpoint `/dashboard/data`, `/api/command`, dan `/api/users` | Semua pengguna yang login berpotensi mengakses kontrol aktuator traktor atau melihat daftar akun | Role `user` hanya memiliki akses *read-only monitoring*; hanya `admin` yang dapat mengirim perintah kendali traktor dan melihat manajemen pengguna | Pengujian login session `kelompok1` (`user`) vs `admin` (`admin`) pada dashboard & API | [x] Selesai |
