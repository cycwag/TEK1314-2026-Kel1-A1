# Direktori Bukti (Evidence) — Blue Team

Folder ini berisi artefak dan tangkapan layar (*screenshot*) hasil deteksi sensor **Security Onion IDS (`192.168.10.30`)**, log forensik pada **Target-Node (`192.168.10.20`)**, proses eksekusi **Hardening (Tahap 4)**, serta bukti **Verifikasi Pasca-Hardening (Tahap 5)**.

---

## A. Bukti Deteksi Awal (Tahap 2 Purple Team Loop — Sebelum Hardening)

### 1. Deteksi Skenario 1 — Network & Service Reconnaissance (`01_sguil_recon_nmap_alert.jpg`)
* **Sensor:** `seconion` (`192.168.10.30`)
* **Source IP:** `192.168.10.10` -> **Destination IP:** `192.168.10.20`
* **Alert ID & Event Message:**
  * `5.1254` — `ET SCAN Nmap Scripting Engine User-Agent Detected` (DPort `80`)
  * `5.1255` — `ET SCAN Possible Nmap User-Agent Observed` (DPort `80`)
  * `5.1266` — `ET SCAN Suspicious inbound to mySQL port 4333` (DPort `4333`)

![Sguil Alert Reconnaissance Nmap](01_sguil_recon_nmap_alert.jpg)

### 2. Deteksi Skenario 2 — Alert Sguil SSH Brute-Force (`02_sguil_ssh_bruteforce_alert_5_1278.jpg`)
* **Alert ID:** `5.1278` (beserta rangkaian scan `5.1228` s.d. `5.1242`)
* **Source IP:** `192.168.10.10` (`SPort: 35544`) -> **Destination IP:** `192.168.10.20` (`DPort: 22`)
* **Event Message:** `ET SCAN LibSSH Based Frequent SSH Connections Likely Brute Force`

![Sguil Alert 5.1278 SSH Brute Force](02_sguil_ssh_bruteforce_alert_5_1278.jpg)

### 3. Deteksi Skenario 2 — Log Forensik `/var/log/auth.log` (`03_target_auth_log_ssh_bruteforce.jpg`)
Perintah: `sudo tail -n 20 /var/log/auth.log`
* Mencatat rentetan `Failed password for bagas from 192.168.10.10` pada berbagai port sumber (`35530`, `35544`, `35522`, `35534`), diikuti oleh `Accepted password for bagas from 192.168.10.10 port 35534 ssh2` saat password lemah (`123`) berhasil ditebak sebelum hardening diterapkan.

![Target auth.log SSH Brute Force](03_target_auth_log_ssh_bruteforce.jpg)

### 4. Deteksi Skenario 3 — Log Aplikasi Flask Brute-Force `/login` (`04_target_flask_log_web_bruteforce.jpg`)
* Mencatat rentetan percobaan brute-force login ke endpoint `POST /login`:
  * 6x `[AUTH-FAIL] login gagal dari 127.0.0.1 untuk user='admin'` (`"POST /login HTTP/1.0" 401 -`)
  * Diikuti oleh `[AUTH-OK] login berhasil dari 127.0.0.1 -> user=admin (role=admin)` (`"POST /login HTTP/1.0" 200 -`) sebelum diterapkannya pembatasan laju request (*rate-limiting*) di Nginx.

![Target Flask Log Web Login Brute Force](04_target_flask_log_web_bruteforce.jpg)

---

## B. Bukti Proses Hardening (Tahap 4 Purple Team Loop — Implementasi Mitigasi)

### 5. Hardening Skenario 1 — Konfigurasi UFW Default Deny & Penutupan Port 5000 (`10_hardening1_ufw_default_deny_and_nginx.jpg`)
Perintah pada `bagas@kelompok1`:
```bash
sudo ufw delete allow 5000/tcp 2>/dev/null
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw enable
sudo ufw status verbose
sudo nano /etc/nginx/sites-available/geosync
```
* Menghapus izin port `5000/tcp`, mengaktifkan firewall `Default: deny (incoming)`, hanya mengizinkan `22/tcp` dan `80/tcp`, serta mengonfigurasi reverse proxy Nginx.

![Hardening 1 UFW Default Deny and Nginx](10_hardening1_ufw_default_deny_and_nginx.jpg)

### 6. Hardening Skenario 2 — Penonaktifan Root SSH (`PermitRootLogin no`) & Konfigurasi Jail Fail2ban (`11_hardening2_ssh_permitrootlogin_and_fail2ban_config.jpg`)
Perintah pada `bagas@kelompok1`:
```bash
sudo sed -i 's/^#\?PermitRootLogin.*/PermitRootLogin no/' /etc/ssh/sshd_config
sudo sshd -T | grep -i permitrootlogin
sudo systemctl restart ssh
cat /etc/fail2ban/jail.local
sudo systemctl restart fail2ban
sudo systemctl enable fail2ban
```
* Menampilkan output `permitrootlogin no` serta isi `/etc/fail2ban/jail.local` (`enabled = true`, `port = 22`, `maxretry = 3`, `findtime = 300`, `bantime = 600`).

![Hardening 2 SSH PermitRootLogin No and Fail2ban Config](11_hardening2_ssh_permitrootlogin_and_fail2ban_config.jpg)

### 7. Hardening Skenario 3 — Konfigurasi Rate-Limiting Nginx pada `/login` (`13_hardening3_nginx_ratelimit_login_config.jpg`)
Perintah pada `bagas@kelompok1`:
```bash
cat /etc/nginx/sites-available/geosync
sudo nginx -t && sudo systemctl reload nginx
```
* Menampilkan konfigurasi `limit_req_zone $binary_remote_addr zone=login_limit:10m rate=5r/m;`, `server_tokens off;`, dan `limit_req zone=login_limit burst=3 nodelay;` pada blok `location /login`, diikuti hasil uji sintaks `nginx: configuration file /etc/nginx/nginx.conf test is successful`.

![Hardening 3 Nginx Rate Limit Config](13_hardening3_nginx_ratelimit_login_config.jpg)

---

## C. Bukti Verifikasi Pasca-Hardening (Tahap 5 Purple Team Loop — Sesudah Hardening)

### 8. Verifikasi Skenario 1 — Nmap Scan Ulang Pasca-UFW (`05_after_recon_nmap_only_22_80.jpg`)
Perintah: `sudo nmap -n -sS -sV 192.168.10.20`
* Setelah firewall UFW (`default deny incoming`) diaktifkan, hasil scan Nmap menunjukkan **`998 filtered tcp ports (no-response)`** dan hanya menyisakan port **`22/tcp` (open ssh)** serta **`80/tcp` (open http nginx)**. Port internal `5000/tcp` sudah tidak lagi terlihat.

![After Hardening Nmap Scan Only Port 22 and 80](05_after_recon_nmap_only_22_80.jpg)

### 9. Verifikasi Skenario 1 — Penyembunyian Versi Nginx (`06_after_recon_curl_header_nginx_no_version.jpg`)
Perintah: `curl -I http://192.168.10.20`
* Setelah direktif `server_tokens off;` diaktifkan pada Nginx, header HTTP hanya menampilkan **`Server: nginx`** tanpa membocorkan nomor versi Nginx maupun sistem operasi.

![After Hardening Curl Header Server Nginx Without Version](06_after_recon_curl_header_nginx_no_version.jpg)

### 10. Verifikasi Skenario 2 — Status Awal & Pemblokiran Otomatis IP Penyerang di Fail2ban (`07_after_ssh_fail2ban_sshd_active.jpg` & `12_hardening2_fail2ban_banned_ip_192_168_10_10.jpg`)
Perintah:
```bash
sudo fail2ban-client status sshd
sudo grep "Ban" /var/log/fail2ban.log | tail -n 10
```
* Menampilkan perbandingan status jail `sshd` sebelum serangan ulang (`Currently banned: 0`) dan sesudah serangan ulang Hydra (`Currently banned: 1`, **`Banned IP list: 192.168.10.10`**) beserta bukti log `[sshd] Ban 192.168.10.10` pada `/var/log/fail2ban.log`.

![After Hardening Fail2ban Status sshd Active](07_after_ssh_fail2ban_sshd_active.jpg)
![After Hardening Fail2ban Banned IP 192.168.10.10](12_hardening2_fail2ban_banned_ip_192_168_10_10.jpg)

### 11. Verifikasi Skenario 2 — Uji Ulang Serangan Hydra Gagal Menemukan Password (`08_after_ssh_hydra_zero_password_found.jpg`)
Perintah: `hydra -l bagas -P pass.txt ssh://192.168.10.20 -t 4 -V`
* Setelah penerapan Fail2ban dan kebijakan password, serangan ulang Hydra menggunakan wordlist yang sama gagal menembus akun `bagas` (**`1 of 1 target completed, 0 valid password found`**).

![After Hardening Hydra Zero Valid Password Found](08_after_ssh_hydra_zero_password_found.jpg)

### 12. Verifikasi Skenario 3 — Uji Rate-Limiting Nginx pada Endpoint `/login` (`09_after_web_login_ratelimit_401_503.jpg`)
Perintah:
```bash
for i in {1..8}; do curl -s -o /dev/null -w "%{http_code}\n" -X POST http://192.168.10.20/login -H "Content-Type: application/json" -d '{"username":"admin","password":"tes"}'; done
```
* Setelah penerapan `limit_req_zone` (`rate=5r/m`, `burst=3 nodelay`) pada `location /login`, 4 percobaan pertama dijawab dengan **`401`**, dan 4 percobaan berikutnya langsung ditolak oleh Nginx dengan **`503`** (`Service Temporarily Unavailable`).

![After Hardening Web Login Rate Limit 401 and 503](09_after_web_login_ratelimit_401_503.jpg)

### 13. Verifikasi Akhir Gabungan Seluruh Kontrol Hardening (`14_hardening_final_verification_summary.jpg`)
* Menampilkan verifikasi gabungan pada `bagas@kelompok1`: konfigurasi `/etc/nginx/sites-available/geosync`, hasil `sudo sshd -T | grep -i permitrootlogin` -> `permitrootlogin no`, `sudo ufw status verbose` (`Default: deny (incoming)`), dan `grep -n "server_tokens" /etc/nginx/sites-available/geosync` -> `5: server_tokens off;`.

![Final Hardening Verification Summary](14_hardening_final_verification_summary.jpg)
