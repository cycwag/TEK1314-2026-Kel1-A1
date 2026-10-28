# Hardening A — Kebijakan Kata Sandi & Kontrol Akses Direktori

**Proyek:** PBL Keamanan Siber (TEK1314)  
**Host/User:** `bagas@kelompok1` & `public@kelompok1`

---

## 1. Pengujian Kebijakan Keamanan Kata Sandi (*Password Policy*)

Tahap ini bertujuan untuk memverifikasi bahwa aturan kompleksitas dan riwayat kata sandi (seperti melalui modul PAM `pam_pwquality`) telah berjalan dengan baik guna mencegah penggunaan kata sandi yang lemah atau berulang.

### a. Eksekusi Perintah
Pada lingkungan `(venv)` di direktori `~/TEK1314-2026-Kel1-A1/backend-replika`, pengguna menjalankan perintah untuk mengganti kata sandi akun `bagas`:
```bash
passwd bagas
```

### b. Hasil Pengujian & Analisis
Setelah memverifikasi kata sandi saat ini (`Current password`), dilakukan tiga kali percobaan memasukkan kata sandi baru yang tidak memenuhi kriteria keamanan:

1. **Percobaan Pertama (Kata Sandi Sama):**
   * **Respon Sistem:** `BAD PASSWORD: The password is the same as the old one`
   * **Penjelasan:** Sistem menolak perubahan karena kata sandi baru yang dimasukkan identik dengan kata sandi lama yang sedang digunakan.

2. **Percobaan Kedua & Ketiga (Tanpa Huruf Kapital):**
   * **Respon Sistem:** `BAD PASSWORD: The password contains less than 1 uppercase letters`
   * **Penjelasan:** Sistem menolak kata sandi baru sebanyak dua kali berturut-turut karena tidak memenuhi syarat minimal memiliki **1 huruf kapital (*uppercase*)**.

3. **Penghentian Otomatis oleh Sistem:**
   * **Respon Sistem:** 
     ```text
     passwd: Have exhausted maximum number of retries for service
     passwd: password unchanged
     ```
   * **Penjelasan:** Karena telah gagal melewati validasi sebanyak batas maksimal percobaan (3 kali), layanan `passwd` menghentikan proses secara otomatis dan mempertahankan kata sandi lama. Hal ini membuktikan bahwa kebijakan *password hardening* telah aktif dan efektif.

---

## 2. Pengujian Pembatasan Hak Akses Direktori (*Access Control*)

Tahap ini dilakukan untuk menguji penerapan hak akses (*file/directory permissions*) pada direktori `/opt/shared-data` agar pengguna yang tidak memiliki otorisasi tidak dapat membuat atau memodifikasi file di dalamnya.

### a. Beralih ke Akun Non-Otorisasi (`public`)
Dari sesi pengguna `bagas`, dilakukan perpindahan sesi login ke akun `public`:
```bash
su - public
```

### b. Percobaan Penulisan File di Direktori Terproteksi
Setelah masuk sebagai `public@kelompok1`, dilakukan percobaan membuat file baru bernama `uji.txt` di dalam direktori `/opt/shared-data`:
```bash
touch /opt/shared-data/uji.txt
```

### c. Hasil Pengujian & Analisis
* **Respon Sistem:**
  ```text
  touch: cannot touch '/opt/shared-data/uji.txt': Permission denied
  ```
* **Penjelasan:** Sistem secara tegas menolak pembuatan file tersebut (`Permission denied`). Hal ini mengonfirmasi bahwa konfigurasi kepemilikan (*ownership*) dan izin akses (*permissions*) pada direktori `/opt/shared-data` telah berhasil membatasi pengguna luar (`public`) dari hak tulis (*write access*).

---

## 3. Ringkasan Hasil Pengujian (Hardening A)

| Parameter Pengujian | Skenario Uji | Respon Sistem | Status |
| :--- | :--- | :--- | :--- |
| **Riwayat Kata Sandi** | Memasukkan *password* baru yang sama dengan *password* lama | `The password is the same as the old one` | **Berhasil Diblokir** |
| **Kompleksitas Kata Sandi** | Memasukkan *password* tanpa huruf kapital (*uppercase*) | `The password contains less than 1 uppercase letters` | **Berhasil Diblokir** |
| **Batas Percobaan (`passwd`)** | Gagal validasi *password* baru 3 kali berturut-turut | `Have exhausted maximum number of retries` (`password unchanged`) | **Berhasil Diblokir** |
| **Hak Akses Direktori** | User `public` menjalankan `touch /opt/shared-data/uji.txt` | `Permission denied` | **Berhasil Diblokir** |