# Direktori Bukti (Evidence) — Red Team

Folder ini berisi artefak dan tangkapan layar (*screenshot*) hasil eksekusi simulasi serangan dan pengujian ulang (*re-test*) pasca-hardening oleh **Red Team** dari `Attacker-Node` (`192.168.10.10`).

## Daftar Bukti & Referensi Dokumentasi

| Skenario | Deskripsi Bukti | Lokasi / Referensi |
|---|---|---|
| **Skenario 1 — Reconnaissance** | Output `sudo nmap -sS -sV -O 192.168.10.20` dan `sudo nmap -p- 192.168.10.20` (sebelum & sesudah hardening UFW/Nginx) | [`../attack_plan.md`](../attack_plan.md) & [`../../purple-team-log.md`](../../purple-team-log.md) |
| **Skenario 2 — SSH Brute-Force** | Eksekusi `hydra -l bagas -P pass.txt ssh://192.168.10.20 -t 4 -V` (sebelum hardening & sesudah diblokir Fail2ban) | [`../attack_plan.md`](../attack_plan.md) & [`../../purple-team-log.md`](../../purple-team-log.md) |
| **Skenario 3 — Web / API Attack** | Eksekusi `curl` tanpa API key (`401`), payload sensor ekstrem (`400`), telemetri valid (`201`), serta bash loop brute-force `/login` (`401` x4 -> `503` x4) | [`../attack_plan.md`](../attack_plan.md) & [`../../purple-team-log.md`](../../purple-team-log.md) |
