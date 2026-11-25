# Direktori Bukti (Evidence) — Blue Team

Folder ini berisi artefak dan tangkapan layar (*screenshot*) hasil deteksi, konfigurasi hardening, serta verifikasi pasca-mitigasi oleh **Blue Team** pada `Target-Node` (`192.168.10.20`) dan `Monitoring-Node` (`192.168.10.30`).

## Daftar Bukti & Referensi Dokumentasi

| Kategori / Skenario | Deskripsi Bukti | Lokasi / Referensi |
|---|---|---|
| **Instalasi & Sensor Monitoring** | VM Security Onion & Workstation Lab aktif pada VirtualBox | [`../../DOKUMENTASI_INSTALASI_UTAMA/`](../../DOKUMENTASI_INSTALASI_UTAMA/) |
| **Hardening Kategori A** | Uji `passwd bagas` (PAM `pwquality`) & pembatasan hak akses direktori `/opt/shared-data` (`user public`) | [`../hardening_kategori_A.md`](../hardening_kategori_A.md) |
| **Hardening Kategori B** | Konfigurasi `ufw status verbose`, `unattended-upgrades`, dan penonaktifan 5 layanan non-esensial | [`../hardening_kategori_B.md`](../hardening_kategori_B.md) |
| **Hardening Kategori C** | Pemisahan secret `.env`, validasi input `TELEMETRY_RULES`, logging `[SUSPICIOUS]`, dan RBAC Dashboard (`user` vs `admin`) | [`../hardening_checklist.md`](../hardening_checklist.md) |
| **Deteksi & Verifikasi Skenario 1 (Recon)** | Alert Sguil `ET SCAN Nmap`, output `ufw status verbose`, dan `curl -I http://192.168.10.20` (`Server: nginx` tanpa versi) | [`../../purple-team-log.md`](../../purple-team-log.md) |
| **Deteksi & Verifikasi Skenario 2 (SSH Brute-Force)** | Alert Sguil ID `5.1278` (`ET SCAN LibSSH Based Frequent SSH Connections Likely Brute Force`), `/var/log/auth.log`, dan `fail2ban-client status sshd` (`Banned IP: 192.168.10.10`) | [`../../purple-team-log.md`](../../purple-team-log.md) |
| **Deteksi & Verifikasi Skenario 3 (Web/API Attack)** | Log `journalctl -u backend` (`[SUSPICIOUS]`, `[AUTH-FAIL]`), `/var/log/nginx/access.log`, Alert Sguil `ET POLICY curl User-Agent`, dan hasil rate-limit Nginx (`401` x4 -> `503` x4) | [`../../purple-team-log.md`](../../purple-team-log.md) |
