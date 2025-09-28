import json
import logging
import threading
import time
from collections import defaultdict, deque
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Deque, Dict, Optional, Tuple

import paho.mqtt.client as mqtt

from .config import Settings
from .llm import InsightContext, InsightSummarizer
from .models import InsightMessage, TelemetryMessage

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


@dataclass
class Reading:
    ts: datetime
    temp_c: float
    humidity: float
    rssi: Optional[int]


def determine_level(
    current: Reading,
    previous: Optional[Reading],
    warn_threshold: float,
    alert_threshold: float,
    alert_delta: float,
) -> Tuple[str, str]:
    """Return level and rule-based reason."""
    temp = current.temp_c

    if temp >= alert_threshold:
        return "ALERT", f"Suhu {temp:.1f}°C melebihi ambang ALERT {alert_threshold:.1f}°C."

    if previous is not None:
        delta_temp = temp - previous.temp_c
        delta_seconds = (current.ts - previous.ts).total_seconds()
        if delta_temp >= alert_delta and delta_seconds <= 120:
            return (
                "ALERT",
                f"Suhu naik {delta_temp:.1f}°C dalam {int(delta_seconds)} detik, melampaui batas kenaikan {alert_delta:.1f}°C.",
            )

    if temp >= warn_threshold:
        return "WARN", f"Suhu {temp:.1f}°C melebihi ambang WARN {warn_threshold:.1f}°C."

    return "OK", "Suhu dalam rentang aman."


class InsightEngine:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._client = mqtt.Client(client_id=settings.mqtt_client_id, clean_session=True)
        if settings.mqtt_user:
            self._client.username_pw_set(settings.mqtt_user, settings.mqtt_pass)
        self._client.on_connect = self._on_connect
        self._client.on_message = self._on_message
        self._client.on_disconnect = self._on_disconnect
        self._client.reconnect_delay_set(min_delay=self.settings.mqtt_reconnect_initial, max_delay=self.settings.mqtt_reconnect_max)
        self._client.enable_logger()
        self._buffers: Dict[str, Deque[Reading]] = defaultdict(deque)
        self._lock = threading.Lock()
        self._summarizer = InsightSummarizer(settings.gemini_api_key, settings.gemini_model)
        self._last_alert: Dict[str, datetime] = {}

    def start(self) -> None:
        delay = self.settings.mqtt_reconnect_initial
        while True:
            try:
                logger.info(
                    "connect_mqtt",
                    extra={"host": self.settings.mqtt_host, "port": self.settings.mqtt_port},
                )
                self._client.connect(self.settings.mqtt_host, self.settings.mqtt_port, self.settings.mqtt_keepalive)
                self._client.loop_start()
                break
            except Exception as exc:  # pragma: no cover - network failure path
                logger.warning("mqtt_connect_failed", extra={"error": str(exc), "next_retry": delay})
                time.sleep(delay)
                delay = min(delay * 2, self.settings.mqtt_reconnect_max)

    def stop(self) -> None:
        try:
            self._client.loop_stop()
            self._client.disconnect()
        except Exception:  # pragma: no cover - shutdown path
            pass

    def _on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            logger.info("mqtt_connected", extra={"topic": self.settings.telemetry_topic})
            client.subscribe(self.settings.telemetry_topic, qos=1)
        else:  # pragma: no cover - connection error path
            logger.error("mqtt_connect_error", extra={"rc": rc})

    def _on_disconnect(self, client, userdata, rc):  # pragma: no cover - network path
        logger.warning("mqtt_disconnected", extra={"rc": rc})

    def _on_message(self, client, userdata, message):
        try:
            payload = message.payload.decode("utf-8")
            data = json.loads(payload)
            telemetry = TelemetryMessage.parse_obj(data)
        except Exception as exc:
            logger.warning("telemetry_parse_failed", extra={"error": str(exc)})
            return

        reading = Reading(
            ts=telemetry.ts,
            temp_c=telemetry.temp_c,
            humidity=telemetry.humidity,
            rssi=telemetry.rssi,
        )

        with self._lock:
            window = self._buffers[telemetry.device_id]
            self._prune_old(window, reading.ts)
            previous = window[-1] if window else None
            window.append(reading)

        level, reason = determine_level(
            current=reading,
            previous=previous,
            warn_threshold=self.settings.warn_threshold,
            alert_threshold=self.settings.alert_threshold,
            alert_delta=self.settings.alert_delta,
        )

        window_avg = self._compute_average(window)
        if not self._should_emit(level, telemetry.device_id, reading.ts):
            return

        llm_result = self._summarizer.summarize(
            InsightContext(
                device_id=telemetry.device_id,
                level=level,
                temp_c=reading.temp_c,
                window_avg_c=window_avg,
                reason=reason,
                humidity=reading.humidity,
            )
        )

        insight = InsightMessage(
            device_id=telemetry.device_id,
            ts=datetime.now(tz=timezone.utc),
            level=level,
            summary=llm_result["summary"],
            reason=reason,
            last_temp_c=reading.temp_c,
            window_avg_c=window_avg,
            recommendation=llm_result.get("recommendation"),
        )

        self._publish_insight(telemetry.device_id, insight)

    def _prune_old(self, window: Deque[Reading], current_ts: datetime) -> None:
        """Keep data within configured window."""
        limit = current_ts - timedelta(minutes=self.settings.window_minutes)
        while window and window[0].ts < limit:
            window.popleft()

    def _compute_average(self, window: Deque[Reading]) -> float:
        if not window:
            return 0.0
        return sum(r.temp_c for r in window) / len(window)

    def _should_emit(self, level: str, device_id: str, ts: datetime) -> bool:
        if level != "ALERT":
            if level == "WARN":
                return True
            self._last_alert.pop(device_id, None)
            return True

        cooldown = timedelta(seconds=self.settings.insight_alert_cooldown)
        last = self._last_alert.get(device_id)
        if last and ts - last < cooldown:
            return False
        self._last_alert[device_id] = ts
        return True

    def _publish_insight(self, device_id: str, insight: InsightMessage) -> None:
        payload = insight.json()
        topic = f"{self.settings.insight_topic_prefix}/{device_id}"
        result = self._client.publish(topic, payload=payload, qos=self.settings.publish_qos, retain=self.settings.publish_retain)
        if result.rc != mqtt.MQTT_ERR_SUCCESS:
            logger.error("insight_publish_failed", extra={"rc": result.rc})
        else:
            logger.info(
                "insight_published",
                extra={
                    "topic": topic,
                    "level": insight.level,
                    "temp_c": insight.last_temp_c,
                    "avg": insight.window_avg_c,
                },
            )


__all__ = ["InsightEngine", "determine_level", "Reading"]
