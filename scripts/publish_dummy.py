#!/usr/bin/env python3
"""Publisher sederhana untuk mengirim data telemetry dummy ke broker MQTT."""
import argparse
import json
import random
import time
from datetime import datetime, timezone

import paho.mqtt.client as mqtt


def build_payload(device_id: str) -> str:
    base_temp = random.uniform(24.0, 29.0)
    temp = base_temp + random.uniform(-1.5, 4.5)
    humidity = random.uniform(40.0, 70.0)
    payload = {
        "device_id": device_id,
        "ts": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "temp_c": round(temp, 2),
        "humidity": round(humidity, 2),
        "rssi": random.randint(-70, -40),
        "fw": "siap-suhu-sim"
    }
    return json.dumps(payload)


def main() -> None:
    parser = argparse.ArgumentParser(description="Publish data telemetry dummy Siap Suhu")
    parser.add_argument("--host", default="127.0.0.1", help="Alamat broker MQTT")
    parser.add_argument("--port", type=int, default=1883, help="Port broker MQTT")
    parser.add_argument("--device", default="SIM-001", help="Device ID yang digunakan")
    parser.add_argument("--interval", type=float, default=5.0, help="Interval publish (detik)")
    args = parser.parse_args()

    client = mqtt.Client()
    client.connect(args.host, args.port, keepalive=30)
    client.loop_start()
    topic = f"siapsuhu/telemetry/{args.device}"
    print(f"Mulai publish ke {topic} -> {args.host}:{args.port}")
    try:
        while True:
            payload = build_payload(args.device)
            client.publish(topic, payload=payload, qos=1, retain=False)
            print(payload)
            time.sleep(args.interval)
    except KeyboardInterrupt:
        print("Berhenti.")
    finally:
        client.loop_stop()
        client.disconnect()


if __name__ == "__main__":
    main()
