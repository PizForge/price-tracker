# Price Tracker

Price Tracker ialah projek Python untuk menjejak harga produk daripada URL
halaman produk. Ia membaca nama, harga dan mata wang daripada data berstruktur
JSON-LD, kemudian menggunakan meta tag sebagai pilihan sandaran. Harga semasa
dan sejarah perubahan disimpan dalam pangkalan data SQLite.

## Ciri-ciri

- Tambah produk dengan harga sasaran pilihan.
- Senaraikan produk yang sedang dijejak dan lihat sejarah harga.
- Semak harga terkini, simpan setiap semakan, dan maklumkan jika harga turun
  atau mencapai harga sasaran.
- Simpan nama, URL produk yang dibersihkan daripada parameter tracking, mata
  wang dan sejarah harga dalam SQLite.
- Jalankan semakan berkala melalui GitHub Actions atau mulakan semakan secara
  manual.

## Pemasangan

Perlukan Python 3.10 atau lebih baharu. Dari direktori projek:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e .
```

Pangkalan data SQLite dicipta secara automatik di
`data/price_tracker.db`. Untuk memilih lokasi lain, gunakan pilihan `--db-path`.

## Penggunaan CLI

Semua arahan dijalankan menggunakan `python -m pricetracker`.

Tambah produk dan harga sasaran pilihan:

```powershell
python -m pricetracker add "https://example.com/product" --target 250.00
```

Senaraikan produk:

```powershell
python -m pricetracker list
```

Semak dan simpan harga terkini untuk semua produk:

```powershell
python -m pricetracker check
```

Lihat sejarah harga menggunakan ID yang dipaparkan oleh arahan `list`:

```powershell
python -m pricetracker history 1
```

Buang produk dan sejarah harganya:

```powershell
python -m pricetracker remove 1
```

Contoh menggunakan pangkalan data alternatif:

```powershell
python -m pricetracker --db-path data/test.db list
```

## GitHub Actions

Workflow dalam `.github/workflows/check.yml` menjalankan `python -m
pricetracker check` setiap enam jam (`0 */6 * * *`) dan juga menyokong
`workflow_dispatch` untuk dijalankan secara manual dari tab **Actions** di
GitHub. Selepas semakan, workflow menambah `data/price_tracker.db` ke Git dan
commit serta push hanya jika fail itu berubah. Ia menggunakan
`permissions: contents: write`; pastikan tetapan Actions repository
membenarkan workflow token menulis kandungan.

## Had yang diketahui

- Sesetengah laman menyekat permintaan automatik atau memerlukan kuki,
  pengesahan, atau sesi pengguna. Dalam keadaan ini, semakan boleh gagal.
- Parser membaca HTML yang diterima daripada pelayan. Laman yang hanya
  memaparkan harga selepas JavaScript dijalankan mungkin tidak mendedahkan
  harga yang boleh dibaca oleh tracker.
- Harga hanya dapat dikenal pasti apabila laman menyediakan format JSON-LD
  atau meta tag produk yang disokong. Struktur laman yang berbeza mungkin
  memerlukan sokongan khusus.

## Ujian

Pasang kebergantungan ujian dan jalankan pytest:

```powershell
python -m pip install -e ".[test]"
python -m pytest
```

Dibina dengan bantuan AI
