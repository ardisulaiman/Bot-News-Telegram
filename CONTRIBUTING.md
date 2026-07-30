# Panduan kontribusi

Terima kasih sudah membantu mengembangkan Bot News Telegram.

## Menyiapkan lingkungan

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

Isi konfigurasi pengujian sendiri dan jangan pernah membagikan token atau API
key.

## Prinsip perubahan

- Pertahankan sumber asli pada judul, preview, dan link berita.
- Pastikan filter baru tidak mencampurkan berita antar-topik.
- Hindari perubahan ambang skor tanpa menjelaskan alasannya.
- Jangan menghapus mekanisme deduplikasi tanpa pengganti yang setara.
- Perbarui README jika konfigurasi atau cara penggunaan berubah.
- Jangan commit `.env` atau file status runtime.

## Pemeriksaan sebelum commit

Periksa sintaks:

```powershell
python -m py_compile repurpose-bot.py
```

Jalankan satu siklus pengujian:

```powershell
$env:TEST_MODE="1"
python repurpose-bot.py
```

Tinjau log untuk memastikan topik yang aktif, jumlah kandidat, hasil filter,
duplikasi, dan status pengiriman sesuai harapan.

## Pesan commit

Gunakan pesan singkat dan jelas, misalnya:

- `docs: improve setup guide`
- `fix: prevent duplicate politics stories`
- `feat: add new RSS source`
