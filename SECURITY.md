# Kebijakan keamanan

## Kredensial

Bot menggunakan token Telegram dan dapat menggunakan API key TwitterAPI.io.
Simpan nilai asli di `.env` atau secret manager platform deployment. Jangan
menaruhnya di source code, README, issue, log publik, atau screenshot.

## Jika secret bocor

1. Rotasi token atau API key dari penyedia terkait.
2. Perbarui secret pada platform deployment.
3. Hapus nilai dari file aktif.
4. Bersihkan nilai dari riwayat Git; menghapus commit terbaru saja tidak cukup.
5. Periksa aktivitas bot dan API yang tidak dikenali.

## Data runtime

File berikut dapat mengungkap pola penggunaan dan tidak perlu dipublikasikan:

- `seen_items.json`;
- `sent_signatures.json`;
- `telegram_update_offset.json`.

Semua file tersebut sudah tercantum dalam `.gitignore`.

## Melaporkan masalah

Jangan membuat issue publik yang berisi token, chat ID privat, data grup, atau
langkah eksploitasi lengkap. Hubungi pemilik repository secara pribadi dengan
ringkasan dampak dan langkah reproduksi minimum yang sudah disensor.
