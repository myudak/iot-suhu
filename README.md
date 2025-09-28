# Siap Suhu — IoT Monitoring & Notifikasi Pintar

Proyek ini membangun rantai IoT lengkap untuk memantau suhu menggunakan ESP32 + sensor DHT, mengirim telemetry ke MQTT, menganalisis wawasan secara otomatis dengan LLM, menampilkan dashboard Node-RED, serta meneruskan notifikasi kritis ke Telegram.

## Arsitektur Singkat
- **Perangkat**: ESP32 (board *esp32-devkit-c-v4*) + DHT22 pada pin D15. Firmware membaca suhu/kelembapan setiap 5 detik dan publish ke MQTT dengan QoS 1.
- **Broker**: Mosquitto dengan listener MQTT 1883 dan WebSocket 9001 (untuk dashboard/Web).
- **Collector & Dashboard**: Node-RED menerima telemetry, menyimpannya ke SQLite, menampilkan gauge + chart realtime, menyediakan endpoint historis `/api/history`, dan menampilkan insight LLM.
- **LLM Insight Service**: FastAPI + Google Gemini. Mengombinasikan aturan cepat (threshold/delta) dengan ringkasan LLM dan publish insight ke MQTT.
- **Telegram Notifier**: Subscribes insight dan mengirim pesan ke bot Telegram (WARN/ALERT) dengan cooldown.
- **Penyimpanan**: SQLite (`data/sqlite/siapsuhu.db`) dengan migrasi awal pada `db/migrations`.

```
ESP32 + DHT22 --> MQTT (Mosquitto) --> Node-RED --> SQLite + Dashboard
                                \-> LLM Insight Service --> MQTT insight --> Telegram Notifier
```

## Struktur Repository
```
.
├── broker/                # Konfigurasi Mosquitto
├── collector/             # Flow Node-RED siap impor
├── data/sqlite/           # Lokasi file SQLite (git-ignored)
├── db/migrations/         # Skrip SQL migrasi awal
├── firmware/esp32/        # Sketch jembatan untuk Wokwi (memanggil kode PlatformIO)
├── llm-insight-service/   # Layanan FastAPI + MQTT + Gemini
├── telegram-notifier/     # Layanan notifikasi Telegram
├── scripts/               # Utilitas migrasi & publisher dummy
├── diagram.json           # Rangkaian Wokwi ESP32 + DHT22
├── wokwi.toml             # Konfigurasi proyek Wokwi
├── docker-compose.yml     # Stack Mosquitto, Node-RED, LLM, Telegram
└── README.md              # Dokumen ini
```

## Prasyarat
- Docker & Docker Compose
- Python 3.11 (opsional, untuk menjalankan tes/skrip lokal)
- `sqlite3` CLI untuk menjalankan migrasi manual
- Akun Google AI Studio (Gemini) + API key (opsional, jika ingin insight LLM nyata)
- Bot Telegram (token & chat id) jika ingin notifikasi.

## Konfigurasi Lingkungan
Salin `.env.example` menjadi `.env`, lalu isi sesuai lingkungan Anda.

| Variabel | Keterangan |
|----------|------------|
| `MQTT_HOST`, `MQTT_PORT`, `MQTT_WS_PORT` | Endpoint broker Mosquitto (docker-compose default: `mqtt`, `1883`, `9001`). |
| `MQTT_USER`, `MQTT_PASS` | Opsional bila ingin autentikasi broker. |
| `GEMINI_API_KEY`, `GEMINI_MODEL` | Kredensial Google Gemini untuk insight LLM (contoh model `gemini-1.5-flash`). |
| `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` | Token bot & chat ID untuk pengiriman pesan. |
| `DB_PATH` | Lokasi file SQLite di dalam kontainer (default `/data/siapsuhu.db`). |
| `INSIGHT_WARN_THRESHOLD`, `INSIGHT_ALERT_THRESHOLD`, `INSIGHT_ALERT_DELTA` | Parameter aturan suhu. |
| `INSIGHT_WINDOW_MINUTES` | Rentang (menit) untuk rata-rata bergerak & analisa delta. |
| `INSIGHT_ALERT_COOLDOWN_SECONDS` | Jeda minimal antar ALERT per device pada layanan insight. |
| `NOTIFIER_ALERT_COOLDOWN_SECONDS` | Jeda minimal untuk notifikasi Telegram. |

> **Firmware**: salin `include/secrets.h.example` menjadi `include/secrets.h` dan isi `WIFI_SSID`, `WIFI_PASS`, `MQTT_HOST`, `MQTT_PORT`, dsb sebelum kompilasi.

## Menjalankan Proyek End-to-End
1. **Jalankan migrasi DB (sekali di awal):**
   ```bash
   ./scripts/migrate.sh
   ```
   atau gunakan `make migrate`.

2. **Start seluruh layanan docker:**
   ```bash
   make up
   ```

3. **Node-RED Dashboard:**
   - Buka `http://localhost:1880`.
   - Import flow (`collector/node-red-data/flows.json`) via menu *Import > Clipboard*, lalu *Deploy*.
   - Dashboard tersedia di tab **Siap Suhu**.

4. **Firmware / Simulator Wokwi:**
   - Buka [wokwi.com](https://wokwi.com) dan impor `diagram.json` + `firmware/esp32/siap_suhu.ino` (wokwi.toml mempermudah).
   - Atur `include/secrets.h` jika menggunakan hardware nyata.
   - Firmware otomatis publish telemetry ke `siapsuhu/telemetry/<chipId>` setiap 5 detik.

5. **Insight & Notifikasi:**
   - Pastikan `GEMINI_API_KEY` valid; jika kosong, layanan insight tetap memakai ringkasan fallback lokal.
   - Telegram notifier memerlukan bot sudah menambahkan chat (kirim `/start` pada bot Anda terlebih dulu).
   - Gunakan script dummy untuk uji cepat tanpa perangkat:
     ```bash
     ./scripts/publish_dummy.py --device SIM-TEST --host 127.0.0.1 --port 1883
     ```

6. **Log & Shutdown:**
   ```bash
   make logs   # melihat log seluruh layanan
   make down   # menghentikan stack
   ```

## Skema Topik MQTT
| Topik | Produsen | Penjelasan |
|-------|----------|------------|
| `siapsuhu/telemetry/<deviceId>` | ESP32 Firmware | Telemetry suhu & kelembapan (QoS 1, retain false).
| `siapsuhu/status/<deviceId>` | ESP32 Firmware | Status online/offline (last will `"offline"`).
| `siapsuhu/insight/<deviceId>` | LLM Insight Service | Insight gabungan rule + LLM.

### Contoh Payload
**Telemetry**
```json
{
  "device_id": "24A5BCFF1122",
  "ts": "2024-07-05T08:30:12Z",
  "temp_c": 31.4,
  "humidity": 58.2,
  "rssi": -62,
  "fw": "siap-suhu-1.0.0"
}
```

**Insight**
```json
{
  "device_id": "24A5BCFF1122",
  "ts": "2024-07-05T08:30:15Z",
  "level": "WARN",
  "summary": "Suhu perangkat 31,4°C sedikit di atas batas aman, kelembapan tetap stabil.",
  "reason": "Suhu 31,4°C melebihi ambang WARN 30,0°C.",
  "last_temp_c": 31.4,
  "window_avg_c": 30.7,
  "recommendation": "Pantau kondisi dan aktifkan pendingin jika tren naik."
}
```

## Firmware ESP32
- File utama PlatformIO: `src/siap_suhu_firmware.cpp` (dipanggil oleh `src/main.cpp`).
- Sketch `firmware/esp32/siap_suhu.ino` bertindak sebagai jembatan untuk simulasi Wokwi dengan logika yang sama.
- Sensor DHT22 di pin D15 (`DHT_TYPE` dapat diubah ke `DHT11`).
- Menggunakan pustaka `ArduinoMqttClient` agar dapat publish QoS 1.
- Terdapat reconnect WiFi + MQTT, sinkronisasi NTP, serta last will `siapsuhu/status/<deviceId>`.
- Versi firmware di payload: `fw = "siap-suhu-1.0.0"`.

## Layanan Backend
### Node-RED Collector (`collector/flows.json`)
- Parsing telemetry → validasi → simpan ke SQLite (`readings`).
- Dashboard: gauge suhu dinamis, chart suhu & kelembapan 1 jam terakhir, tabel ringkas histori, daftar insight, toast notifikasi.
- Endpoint REST: `GET /api/history?device_id=...&from=...&to=...&limit=...`.

### LLM Insight Service (`llm-insight-service`)
- FastAPI + Paho MQTT.
- Aturan cepat: WARN (>= warn threshold), ALERT (>= alert threshold atau delta >= 5°C dalam ≤2 menit).
- Simpan window data 15 menit untuk rata-rata bergerak.
- Memanggil Gemini (fallback otomatis jika API key kosong) agar insight tetap tersedia.
- Unit test tersedia di `llm-insight-service/tests/test_rules.py`.
- Endpoint kesehatan: `GET /healthz`.

### Telegram Notifier (`telegram-notifier`)
- Mendengar `siapsuhu/insight/#`, memfilter level WARN/ALERT.
- Format pesan sesuai spesifikasi dengan emoji 🔔.
- Command: `/start` (aktivasi) dan `/status` (menampilkan 5 insight terakhir).
- Cooldown default 120 detik per device.
- Endpoint kesehatan: `GET /healthz`.

## Pengujian
- Jalankan unit test layanan insight:
  ```bash
  cd llm-insight-service
  pip install -r requirements-dev.txt
  python -m pytest
  ```

- Uji end-to-end dengan script dummy publisher + awasi dashboard / Telegram.

## Penyesuaian & Tips
- **Threshold**: ubah di `.env` lalu restart layanan (`docker compose restart llm-insight-service telegram-notifier`).
- **Autentikasi MQTT**: set `MQTT_USER/MQTT_PASS` pada `.env` & `include/secrets.h`.
- **SQLite**: file `data/sqlite/siapsuhu.db` di-*gitignore*, dapat di-backup langsung.
- **Gemini biaya**: tanpa API key, layanan insight masih berjalan dengan pesan fallback.
- **Telegram**: pastikan bot sudah diundang ke chat/grup tujuan dan `chat_id` diisi benar (gunakan @userinfobot untuk mendapatkan ID).

## Referensi Wokwi
- `diagram.json` menghubungkan ESP32 + DHT22.
- `wokwi.toml` mempermudah pemilihan firmware `.ino` saat simulasi.
- Untuk simulasi cloud MQTT, gunakan Wokwi Cloud (isi variabel melalui `include/secrets.h`).

Selamat mencoba “Siap Suhu”! Jangan ragu menyesuaikan arsitektur atau menambah integrasi sesuai kebutuhan demo atau deployment nyata.
