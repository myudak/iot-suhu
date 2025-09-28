# Repository Guidelines

## Project Structure & Module Organization
- `src/` & `include/`: PlatformIO firmware sources; `siap_suhu_firmware.cpp` hosts core logic, while `main.cpp` provides Arduino entry points. Secrets belong in `include/secrets.h` (ignored by git).
- `firmware/esp32/`: Wokwi bridge sketch reusing the same firmware API; `diagram.json` and `wokwi.toml` drive simulations.
- `llm-insight-service/` & `telegram-notifier/`: Python microservices (FastAPI) with Dockerfiles, requirements, and tests.
- `collector/node-red-data/`: Exported Node-RED flow JSON; `db/migrations/` holds SQLite schema.
- `scripts/`: Utilities such as `migrate.sh` and `publish_dummy.py` for demo data.

## Build, Test, and Development Commands
- `pio run` / `pio device monitor`: Build and flash/monitor firmware via PlatformIO.
- `make migrate`: Apply SQLite migrations locally using `sqlite3`.
- `make up` / `make down`: Start or stop the Mosquitto, Node-RED, Gemini insight, and Telegram services with Docker Compose.
- `docker compose logs -f`: Tail container logs when diagnosing MQTT or LLM behaviour.
- `cd llm-insight-service && python -m pytest`: Run unit tests for the rule engine.

## Coding Style & Naming Conventions
- Firmware follows Arduino C++ conventions: 2-space indentation, camelCase for functions (`siapSuhuSetup`), UPPER_SNAKE_CASE for macros and constants.
- Python services target 3.11, prefer Black-like formatting (4 spaces) and snake_case for functions/variables. Keep module-level constants UPPER_SNAKE_CASE.
- Node-RED function nodes should log in Bahasa Indonesia and validate payload fields explicitly.

## Testing Guidelines
- Firmware: smoke tests via Wokwi or `publish_dummy.py` against local broker; log output should show QoS1 publishes.
- Python: Pytest suite (`tests/test_rules.py`) must pass before shipping; add new tests beside the module under test.
- Manual integration: verify MQTT topics `siapsuhu/telemetry/#`, `siapsuhu/insight/#`, and Telegram notifications through Docker stack.

## Commit & Pull Request Guidelines
- Use imperative, concise commit subjects (e.g., `Add Gemini summariser fallback`). Group related changes per commit.
- Pull requests should describe impacted services, mention testing performed (e.g., `pytest`, `make up` smoke), and include screenshots of Node-RED dashboard when UI changes.
- Link relevant issues or TODOs; request review from IoT and backend reviewers when touching cross-service flows.

## Security & Configuration Tips
- Never commit `include/secrets.h` or real `.env` values; rely on `.env.example` for templates.
- Regenerate API keys (Gemini, Telegram) if exposed, and rotate MQTT credentials when enabling authentication.
- For production, disable anonymous Mosquitto access (`broker/mosquitto.conf`) and mount persistent `data/sqlite` volumes with restricted permissions.
