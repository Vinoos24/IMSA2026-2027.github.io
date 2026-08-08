# IMSA Professional Web App — Public Dashboard + Presentation + Android QR + Admin

Arsitektur versi ini sengaja disederhanakan agar profesional dan tidak berantakan.

## Struktur penggunaan

### 1. Dashboard Publik — `/`

Pengunjung hanya melihat:

- Profil IMSA.
- Pengurus.
- Empat divisi dan anggota.
- Foto kegiatan.
- Tombol **Mode Presentasi**.
- Tombol **Android / QR**.

Tidak ada tombol upload/edit yang bercampur dengan halaman publik.

### 2. Mode Presentasi — `/presentation`

- Background crimson/red profesional.
- Fullscreen.
- Keyboard panah, Page Up/Down, Space, Home, End, dan F.
- Data selalu membaca database yang sama dengan Dashboard.

### 3. Android / QR

Dashboard menghasilkan QR menuju:

```text
PUBLIC_BASE_URL/?device=android
```

Layout yang dibuka di Android adalah dashboard yang sama dan responsif.

### 4. Admin — `/admin`

Admin mempunyai halaman terpisah untuk:

- Upload dan ganti foto latar gedung MI.
- Edit hero dashboard.
- Edit nomor/tanggal SK.
- Edit seluruh pengurus.
- Edit koordinator setiap divisi.
- Edit gambaran umum, tugas, output, dan prinsip divisi.
- Tambah/edit/hapus anggota.
- Tambah/edit/hapus kegiatan.
- Upload maksimal 8 foto kegiatan.
- Hapus foto kegiatan satu per satu.

Perubahan otomatis digunakan Dashboard dan Presentasi karena semuanya membaca SQLite yang sama.

## Password admin

Default development password:

```text
imsa2026
```

**Sebelum dipublikasikan wajib diganti.**

Salin `.env.example` menjadi `.env`, lalu isi:

```env
SECRET_KEY=random-yang-panjang
ADMIN_PASSWORD=password-kuat-anda
PUBLIC_BASE_URL=https://domain-anda.com
DATA_DIR=./data
PORT=5000
```

## Menjalankan di VS Code / Windows

### Opsi 1

Klik:

```text
start_windows.bat
```

### Opsi 2

Terminal VS Code:

```bash
python -m pip install -r requirements.txt
python app.py
```

Buka:

```text
http://localhost:5000
```

Admin:

```text
http://localhost:5000/admin
```

## Penting: QR beda jaringan

QR **tidak mungkin** diakses dari jaringan berbeda jika web hanya berjalan pada `localhost` atau alamat Wi-Fi lokal seperti `192.168.x.x`.

Agar Android di jaringan berbeda tetap bisa membuka aplikasi, aplikasi harus dipublikasikan ke server internet, contohnya:

```text
https://imsa.domainanda.com
```

Lalu set:

```env
PUBLIC_BASE_URL=https://imsa.domainanda.com
```

QR otomatis akan mengarah ke URL tersebut.

## Deploy publik

Proyek sudah dilengkapi:

- `Dockerfile`
- `Procfile`
- `gunicorn`
- environment variable `PUBLIC_BASE_URL`
- environment variable `DATA_DIR`

Dapat dipasang pada VPS, Railway, Render dengan persistent disk, Fly.io, atau layanan container lain.

### Penyimpanan permanen

Database dan upload berada di:

```text
data/imsa.db
data/uploads/
```

Jika menggunakan hosting/container, pasang **persistent volume** ke folder `data` agar foto dan perubahan Admin tidak hilang saat server restart/redeploy.

## Struktur file

```text
IMSA_Professional_WebApp_Admin_Public/
├── app.py
├── seed.json
├── requirements.txt
├── .env.example
├── Dockerfile
├── Procfile
├── start_windows.bat
├── start_windows.ps1
├── templates/
│   ├── base.html
│   ├── dashboard.html
│   ├── presentation.html
│   ├── admin_login.html
│   └── admin_dashboard.html
├── static/
│   ├── css/styles.css
│   ├── js/app.js
│   ├── js/presentation.js
│   ├── img/logo-imsa.png
│   ├── img/icon-192.png
│   ├── img/icon-512.png
│   └── manifest.webmanifest
└── data/
    └── uploads/
```

## Revisi struktur organisasi

Koordinator Kaderisasi pada seed versi ini adalah:

**Syavinatul Isya**

Elvareta Yoseph dicantumkan sebagai anggota Kaderisasi.


## V2 — Penyempurnaan Dashboard dan Presentasi

Versi ini memperbaiki bahasa pada halaman publik agar tidak terdengar seperti instruksi teknis/admin.
Judul dan deskripsi publik sekarang berfokus pada profil, kepemimpinan, kolaborasi divisi, dan dokumentasi organisasi.

Mode presentasi juga diperbarui menjadi lebih informatif dengan:
- slide pembuka profesional,
- ringkasan organisasi dan indikator utama,
- slide dasar pengesahan,
- susunan pengurus inti,
- satu slide terstruktur untuk setiap divisi,
- penjelasan tugas, output, prinsip kerja, koordinator, dan anggota,
- galeri dokumentasi,
- slide penutup,
- navigasi keyboard, mouse wheel, swipe mobile, dan fullscreen.

Warna crimson merah yang sudah digunakan tetap dipertahankan.
