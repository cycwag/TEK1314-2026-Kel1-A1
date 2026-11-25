# Dokumentasi Konfigurasi & Hardening Server (Target-Node)

**Proyek:** PBL Keamanan Siber (TEK1314)  
**Host/User:** `bagas@kelompok1`  

---

## 1. Pemeriksaan Pembaruan Sistem & Unattended Upgrades

Tahap awal dilakukan untuk memastikan layanan pembaruan otomatis berjalan dengan baik dan memeriksa apakah masih terdapat paket sistem yang perlu diperbarui.

### a. Status Layanan `unattended-upgrades`
* **Unit Layanan:** `unattended-upgrades.service`
* **Main PID:** `718 (unattended-upgr)` yang dieksekusi menggunakan Python 3 (`/usr/bin/python3 /usr/share/unattended-upgrades/unattended-upgrade-shutdown --wait-for-signal`).
* **Penggunaan Sumber Daya:** Memori sebesar `12.3M` dan waktu CPU `190ms`.
* **Log Sistem:** Tercatat `Started Unattended Upgrades Shutdown.` pada `Oct 22 14:18:49`.

### b. Pemeriksaan Paket yang Dapat Diperbarui
Pengguna menjalankan perintah berikut untuk memeriksa daftar paket yang memiliki pembaruan:
```bash
apt list --upgradable
```
* **Hasil:** Terminal menampilkan output `Listing... Done` tanpa diikuti daftar nama paket. Hal ini mengonfirmasi bahwa seluruh paket pada sistem sudah berada pada versi terbaru (*up-to-date*).

---

## 2. Konfigurasi Firewall (UFW) dan Pembukaan Port SSH

Tahap ini bertujuan untuk mengamankan lalu lintas jaringan pada server menggunakan **UFW (Uncomplicated Firewall)** dengan menerapkan kebijakan pembatasan trafik masuk dan hanya mengizinkan port yang dibutuhkan (SSH).

### a. Verifikasi Paket UFW dan Aturan ICMP
1. Paket `ufw` telah terpasang pada versi terbaru (`0.36.1-4ubuntu0.1`).
2. Pemeriksaan aturan *input* protokol ICMP dilakukan dengan perintah:
   ```bash
   sudo cat /etc/ufw/before.rules | grep -A 5 "ok icmp codes"
   ```
   Output menunjukkan bahwa empat tipe paket ICMP diizinkan (`ACCEPT`) pada rantai `ufw-before-input`, yaitu:
   * `destination-unreachable`
   * `time-exceeded`
   * `parameter-problem`
   * `echo-request`

### b. Pengaturan Kebijakan Default (*Default Policy*)
Menutup seluruh akses masuk secara bawaan dan mengizinkan akses keluar:
```bash
sudo ufw default deny incoming
sudo ufw default allow outgoing
```
* Kebijakan trafik masuk (*incoming*) berhasil diubah menjadi `deny`.
* Kebijakan trafik keluar (*outgoing*) berhasil diubah menjadi `allow`.

### c. Pembukaan Port SSH (22/TCP)
Sempat terjadi kesalahan pengetikan perintah `sudo allow 22/tcp` (`command not found`), kemudian diperbaiki dengan menambahkan argumen `ufw`:
```bash
sudo ufw allow 22/tcp
```
* **Hasil:** Aturan berhasil diperbarui (`Rules updated`) untuk trafik IPv4 maupun IPv6 (`v6`).

### d. Aktivasi dan Verifikasi Status Firewall
Mengaktifkan UFW dan memeriksa detail konfigurasinya:
```bash
sudo ufw enable
sudo ufw status verbose
```
* **Status Firewall:** `active` (aktif dan otomatis berjalan saat *system startup*).
* **Logging:** `on (low)`
* **Kebijakan Default:** `deny (incoming)`, `allow (outgoing)`, `disabled (routed)`.
* **Daftar Aturan Aktif:**

| To | Action | From |
| :--- | :--- | :--- |
| `22/tcp` | `ALLOW IN` | `Anywhere` |
| `22/tcp (v6)` | `ALLOW IN` | `Anywhere (v6)` |

---

## 3. Penonaktifan Layanan Non-Esensial (*Service Hardening*)

Tahap ini bertujuan untuk mengurangi permukaan serangan (*attack surface*) dan menghemat sumber daya server dengan mematikan layanan latar belakang (*daemon*) yang tidak diperlukan pada lingkungan server.

### a. Kondisi Awal (*Before*)
Pemeriksaan layanan yang sedang berjalan dilakukan dengan perintah:
```bash
systemctl list-units --type=service --state=running
```
* **Total Layanan Aktif:** **21 unit layanan** (`21 loaded units listed.`).
* **Temuan:** Masih terdapat 5 layanan terkait perangkat keras/desktop yang tidak diperlukan oleh server, yaitu `fwupd.service`, `ModemManager.service`, `multipathd.service`, `udisks2.service`, dan `upower.service`.

### b. Proses Penonaktifan Layanan
Kelima layanan tersebut dihentikan saat itu juga (`--now`) dan dinonaktifkan agar tidak berjalan saat *booting* (`disable`) menggunakan perintah:
```bash
sudo systemctl disable --now fwupd.service
sudo systemctl disable --now ModemManager.service
sudo systemctl disable --now multipathd.service
sudo systemctl disable --now udisks2.service
sudo systemctl disable --now upower.service
```
* **Catatan Eksekusi:** Pada saat mematikan `multipathd.service`, sistem menghapus *symlink* terkait namun memberikan peringatan bahwa layanan tersebut masih dapat dipicu oleh *socket*-nya (`Warning: Stopping multipathd.service, but it can still be activated by: multipathd.socket`).

### c. Kondisi Akhir (*After*)
Pemeriksaan ulang dilakukan kembali dengan perintah:
```bash
systemctl list-units --type=service --state=running
```
* **Total Layanan Aktif:** Berkurang menjadi **16 unit layanan** (`16 loaded units listed.`).
* **Hasil:** Kelima layanan non-esensial telah berhenti dan tidak lagi muncul dalam daftar proses aktif. Layanan yang tersisa hanyalah layanan inti sistem dan jaringan (seperti `ssh.service`, `cron.service`, `rsyslog.service`, `systemd-networkd.service`, dan `unattended-upgrades.service`).

### d. Tabel Perbandingan (*Before vs After*)

| Parameter / Nama Layanan | Deskripsi Layanan | Kondisi *Before* | Kondisi *After* |
| :--- | :--- | :--- | :--- |
| **Total Layanan Berjalan** | Jumlah unit berstatus *running* | **21 unit** | **16 unit** |
| `fwupd.service` | *Firmware update daemon* | `active (running)` | Berhenti & Dinonaktifkan |
| `ModemManager.service` | *Modem Manager* | `active (running)` | Berhenti & Dinonaktifkan |
| `multipathd.service` | *Device-Mapper Multipath Controller* | `active (running)` | Berhenti & Dinonaktifkan |
| `udisks2.service` | *Disk Manager* | `active (running)` | Berhenti & Dinonaktifkan |
| `upower.service` | *Daemon for power management* | `active (running)` | Berhenti & Dinonaktifkan |