# Deteksi Warna dari Webcam

Program Python untuk membaca warna secara real-time dari webcam dan melacak objek berdasarkan warnanya. Menggunakan OpenCV dan NumPy dengan ruang warna HSV.

## Anggota Kelompok

| No | Nama | NIM |
|----|------|-----|
| 1 | Fira Ramadhani | 2408107010019 |
| 2 | Naila Hafizha | 2408107010026 |
| 3 | Annisa Haura Dhiya | 2408107010030 |

## Fitur

- Menampilkan nilai **RGB**, kode **HEX**, nilai **HSV**, dan **nama warna** secara real-time.
- **Mode ROI tetap**: warna dibaca dari kotak di tengah frame.
- **Mode pelacakan objek**: kunci warna sebuah benda, lalu kotak hijau mengikuti benda tersebut lengkap dengan jejak pergerakan dan jendela mask.
- **Kalibrasi white balance (putih)** supaya warna lebih akurat di bawah cahaya yang berbeda-beda.
- **Penanganan hue merah** yang melingkar (sekitar 0 dan 179).
- **Smoothing** nilai warna antar frame agar angka tidak berkedip.
- **Simpan screenshot** lengkap dengan kotak objek dan panel info berukuran kecil.

## Kebutuhan

- Python 3
- Webcam yang terpasang dan dapat diakses
- Pustaka: `opencv-python` dan `numpy`

## Cara Menjalankan

1. Pastikan Python sudah terpasang. Cek dengan:

   ```
   python --version
   ```

2. Pasang pustaka yang dibutuhkan:

   ```
   pip install opencv-python numpy
   ```

3. Jalankan program dari folder tempat `rgb.py` berada:

   ```
   python rgb.py
   ```

4. Jendela **Deteksi Warna v3** akan terbuka dan menampilkan hasil webcam. Gunakan tombol pada tabel di bawah untuk mengendalikan program.

5. Tekan `q` untuk keluar.

> Jika muncul pesan "Webcam tidak bisa dibuka", pastikan webcam tidak sedang dipakai aplikasi lain dan izin kamera sudah diberikan ke terminal atau editor yang dipakai. Jika memakai kamera eksternal, ubah angka `0` pada `cv2.VideoCapture(0)` menjadi `1`.

## Kontrol

| Input | Fungsi |
|-------|--------|
| Klik mouse | Kunci warna objek di titik yang diklik, lalu mulai melacak |
| `t` | Kunci warna dari kotak di tengah frame, lalu mulai melacak |
| `x` | Berhenti melacak, kembali ke ROI tetap di tengah |
| `c` | Kalibrasi putih (arahkan kertas putih ke kotak tengah) |
| `r` | Reset kalibrasi |
| `s` | Simpan screenshot ke `hasil_deteksi.png` |
| `q` | Keluar |

## Cara Pakai Singkat

**Membaca warna di tengah (ROI tetap)**
1. Jalankan program.
2. Arahkan benda ke kotak putih di tengah layar.
3. Baca nilai warna pada panel di pojok kiri atas.

**Melacak objek**
1. Arahkan kamera ke benda berwarna.
2. Klik benda tersebut di layar, atau letakkan di kotak tengah lalu tekan `t`.
3. Kotak hijau akan mengikuti objek, disertai titik pusat dan jejak pergerakan. Jendela **Mask pelacakan** menampilkan piksel yang cocok dengan warna target (putih).
4. Tekan `x` untuk berhenti melacak.

**Kalibrasi putih (disarankan jika cahaya kekuningan atau kebiruan)**
1. Letakkan kertas putih di kotak tengah.
2. Tekan `c`.
3. Tekan `r` jika ingin membatalkan kalibrasi.

## Keluaran

Tekan `s` untuk menyimpan `hasil_deteksi.png` di folder yang sama dengan program. Gambar berisi frame, kotak penanda (dan jejak jika sedang melacak), serta panel info berisi swatch warna, RGB, HEX, HSV, nama warna, dan mode.

## Parameter yang Bisa Diubah

Parameter ada di bagian atas `rgb.py`:

| Parameter | Nilai Awal | Fungsi |
|-----------|-----------|--------|
| `ROI_SIZE` | 40 | Setengah sisi kotak ROI di tengah (piksel) |
| `SMOOTHING` | 0.8 | Penghalusan nilai warna (0 = tanpa smoothing) |
| `LOCK_CAMERA` | False | Coba matikan auto white balance dan auto exposure kamera |
| `H_TOL` | 12 | Toleransi hue |
| `S_TOL` | 70 | Toleransi saturasi |
| `V_TOL` | 70 | Toleransi kecerahan |
| `MIN_AREA` | 500 | Luas minimum kontur agar dianggap objek |
| `TRAIL_LEN` | 32 | Panjang jejak pergerakan |
| `CLICK_PATCH` | 5 | Setengah sisi area warna yang diambil saat klik |
| `SAVE_PANEL_SCALE` | 0.55 | Ukuran panel info pada screenshot |

## Keterbatasan

- Peka terhadap perubahan pencahayaan; kalibrasi putih perlu diulang jika cahaya berubah.
- Hanya melacak satu objek (kontur terbesar) dan satu warna.
- Yang dilacak adalah warna, bukan bentuk atau jenis benda.
- Nama warna ditentukan dengan ambang batas manual, sehingga warna di dekat batas dua kategori bisa diberi nama yang berbeda dari penilaian visual.

## Struktur Berkas

```
.
├── rgb.py              # program utama
├── hasil_deteksi.png   # dibuat saat menekan tombol s
└── README.md
```
