BEGIN TRANSACTION;
CREATE TABLE IF NOT EXISTS readings (
    device_id TEXT NOT NULL,
    ts TEXT NOT NULL,
    temp_c REAL NOT NULL,
    humidity REAL NOT NULL,
    rssi INTEGER
);

CREATE INDEX IF NOT EXISTS idx_readings_device_ts ON readings(device_id, ts);
COMMIT;
