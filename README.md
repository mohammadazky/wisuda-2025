
# Wisuda Uploader (Web Aplikasi)

Tema hitam-emas elegan 🎓. Upload file otomatis ke Google Drive folder **WISUDAMHMQ2025** (ID: `1kEO0rYA1aVSPyhUr1bMkXpGB3P5e8JzX`).
Login via Google OAuth hanya untuk email yang diizinkan di `allowed_users.json`.

## 1) Persiapan
- Python 3.10+ terpasang
- File `credentials.json` dari Google Cloud Console (sudah Anda miliki)
- Pastikan folder Google Drive sudah dishare **Editor** ke semua user yang boleh upload

## 2) Cara Menjalankan (Lokal)
```bash
pip install -r requirements.txt
python app.py
```
Buka: http://localhost:5000

### Login
Klik **Login dengan Google** → pilih akun user yang diizinkan (contoh: `usersatuwisuda2025@gmail.com`).

## 3) Konfigurasi
- **Folder ID**: ubah di `config.json` → `"folder_id"`
- **Logo**: ganti file `static/images/logo.png` (cukup replace)
- **Teks/Branding**: ubah `config.json` bagian `branding`
- **Daftar pengguna**: edit `allowed_users.json` → tambahkan email lain

## 4) Catatan Penting
- File akan diupload ke folder admin **dengan akun user yang login**, maka **user harus punya akses Editor** ke folder Drive tersebut.
- Jika upload gagal karena izin, cek:
  1. Folder Drive sudah dishare ke user sebagai **Editor**
  2. Email user tercantum di `allowed_users.json`
  3. Proses login berhasil (lihat notifikasi di halaman)

## 5) Ganti Tema
- Ubah warna di `static/css/style.css`
- Ganti logo dengan file PNG transparan ukuran ~512x512 untuk hasil maksimal

Sukses wisuda! 🎓
