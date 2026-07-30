# Bot News Telegram

Bot kurasi berita multi-topik untuk Telegram. Aplikasi ini mengambil berita dari RSS dan X, menilai relevansi serta tingkat viralnya, menyaring berita yang mirip, lalu mengirim hasil terbaik ke Topic Telegram yang sesuai.

Bot berjalan tanpa AI generatif. Judul dan ringkasan tetap berasal dari sumber asli sehingga hasil kurasi dapat dibaca, diverifikasi, dan ditulis ulang secara manual sebelum dipublikasikan ke platform lain.

## Fitur utama

- Kurasi berita untuk AI, crypto, viral Indonesia, entertainment Indonesia, viral global, dan politik Indonesia.
- Sumber RSS berbeda untuk setiap topik.
- Dukungan sumber X melalui TwitterAPI.io.
- Skor viral berdasarkan kata kunci, engagement, dan kemunculan lintas sumber.
- Filter relevansi dan batas umur berita.
- Pencegahan duplikasi berdasarkan token judul dan entitas penting.
- Pengiriman ke Topic Telegram melalui `message_thread_id`.
- Perintah `/tr` untuk menerjemahkan pesan yang dibalas ke bahasa Indonesia.
- Mode pengujian satu kali sebelum bot dijalankan terus-menerus.

## Cara kerja

```text
RSS + TwitterAPI.io
        ↓
  Filter waktu dan topik
        ↓
    Penilaian viral
        ↓
  Pemeriksaan duplikasi
        ↓
 Topic Telegram terkait
```

Setiap berita mendapatkan skor dari sinyal berikut:

1. engagement dari X atau skor dasar untuk RSS;
2. kata kunci update besar, kontroversi, dan sinyal khusus topik;
3. kemunculan berita serupa di beberapa sumber;
4. filter tambahan untuk memastikan konten sesuai dengan kategori.

Berita yang sudah dikirim disimpan secara lokal agar tidak terkirim kembali pada siklus berikutnya.

## Persyaratan

- Python 3.11 atau lebih baru
- Bot Telegram dari `@BotFather`
- Grup Telegram dengan fitur Topics
- API key TwitterAPI.io jika sumber X ingin digunakan

## Instalasi

Clone repository dan masuk ke folder proyek:

```powershell
git clone https://github.com/ardisulaiman/Bot-News-Telegram.git
cd Bot-News-Telegram
```

Buat virtual environment dan instal dependensi:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Salin konfigurasi contoh:

```powershell
Copy-Item .env.example .env
```

## Konfigurasi

Isi file `.env`:

```dotenv
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=

TOPIC_AI_THREAD_ID=
TOPIC_CRYPTO_THREAD_ID=
TOPIC_VIRAL_THREAD_ID=
TOPIC_ENTERTAINMENT_THREAD_ID=
TOPIC_VIRAL_GLOBAL_THREAD_ID=
TOPIC_POLITICS_THREAD_ID=

TWITTERAPI_KEY=
CHECK_INTERVAL_SECONDS=1800
MAX_AGE_HOURS=5
MAX_ITEMS_PER_TOPIC=6
POLITICS_MAX_ITEMS=15
DEDUPE_HOURS=72
TRANSLATE_SOURCE_LANG=en
TEST_MODE=0
```

### Mendapatkan Telegram Chat ID

1. Tambahkan bot ke grup Telegram.
2. Jadikan bot admin agar dapat mengirim pesan ke Topic.
3. Kirim satu pesan ke grup.
4. Buka `https://api.telegram.org/bot<TOKEN>/getUpdates`.
5. Ambil nilai `message.chat.id` dan masukkan sebagai `TELEGRAM_CHAT_ID`.

### Mendapatkan Topic Thread ID

1. Aktifkan Topics pada grup Telegram.
2. Buat Topic untuk kategori yang ingin digunakan.
3. Kirim pesan ke Topic tersebut.
4. Buka endpoint `getUpdates`.
5. Ambil nilai `message_thread_id` dan masukkan ke variabel topik terkait.

Topik dengan thread ID kosong akan dilewati, jadi tidak semua kategori wajib diaktifkan.

## Menjalankan bot

Uji satu siklus terlebih dahulu:

```powershell
$env:TEST_MODE="1"
python repurpose-bot.py
```

Jika hasilnya sudah sesuai, jalankan normal:

```powershell
python repurpose-bot.py
```

Bot akan memeriksa sumber, mengirim berita yang lolos kurasi, menunggu sesuai `CHECK_INTERVAL_SECONDS`, lalu mengulangi proses.

## Perintah Telegram

Balas pesan berbahasa Inggris di grup, lalu kirim:

```text
/tr
```

Bot akan menerjemahkan teks atau caption ke bahasa Indonesia melalui layanan MyMemory. URL dalam pesan tetap dipertahankan.

## File runtime

File berikut dibuat otomatis dan tidak perlu di-commit:

- `seen_items.json`: ID berita yang sudah diproses;
- `sent_signatures.json`: sidik jari judul untuk mencegah duplikasi;
- `telegram_update_offset.json`: posisi terakhir listener perintah Telegram.

## Deployment

Repository menyertakan `railpack.toml` untuk deployment yang sudah ada. Di platform hosting, isi variabel environment yang sama dengan `.env` dan jalankan `python repurpose-bot.py` sebagai proses utama. Jangan mengunggah file `.env`.

## Troubleshooting

### Bot tidak mengirim berita

Periksa token, chat ID, thread ID, umur maksimum berita, dan skor minimum setiap profil. Lihat log terminal untuk mengetahui topik yang dilewati.

### Berita yang sama muncul kembali

Pastikan file runtime dapat ditulis dan tidak selalu terhapus ketika service restart. Pada hosting ephemeral, gunakan storage persisten jika ingin status deduplikasi bertahan.

### Sumber X kosong

Pastikan `TWITTERAPI_KEY` valid. Tanpa key tersebut, sumber RSS tetap berjalan normal.

### Perintah /tr tidak merespons

Pastikan hanya satu instance bot yang memakai `getUpdates` dan bot memiliki izin membaca pesan grup.

## Keamanan

Jangan commit token Telegram, API key, file `.env`, atau data runtime. Jika secret pernah masuk ke GitHub, segera rotasi secret tersebut dan bersihkan dari riwayat Git.

## Catatan

Feed RSS, struktur data X, dan API eksternal dapat berubah. Periksa log secara berkala dan sesuaikan sumber jika ada feed yang berhenti merespons.
