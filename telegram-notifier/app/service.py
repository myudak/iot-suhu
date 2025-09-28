import asyncio
import json
import logging
import threading
import time
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Deque, Dict, Optional

import paho.mqtt.client as mqtt
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

from .config import Settings

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


@dataclass
class Insight:
    device_id: str
    level: str
    summary: str
    recommendation: Optional[str]
    last_temp_c: float
    window_avg_c: float
    ts: datetime


class TelegramNotifier:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.loop: Optional[asyncio.AbstractEventLoop] = None
        self._client = mqtt.Client()
        if settings.mqtt_user:
            self._client.username_pw_set(settings.mqtt_user, settings.mqtt_pass)
        self._client.on_connect = self._on_connect
        self._client.on_message = self._on_message
        self._client.on_disconnect = self._on_disconnect
        self._client.reconnect_delay_set(settings.mqtt_reconnect_initial, settings.mqtt_reconnect_max)

        self._history: Deque[Insight] = deque(maxlen=settings.status_history_size)
        self._last_sent: Dict[str, datetime] = {}
        self._lock = threading.Lock()

        self._telegram_app: Optional[Application] = None
        self.enabled = bool(settings.telegram_bot_token and settings.telegram_chat_id)

    async def start(self) -> None:
        self.loop = asyncio.get_running_loop()
        if self.enabled:
            await self._start_bot()
        await asyncio.to_thread(self._connect_mqtt)

    async def stop(self) -> None:
        try:
            self._client.loop_stop()
            self._client.disconnect()
        except Exception:  # pragma: no cover - shutdown path
            pass
        if self.enabled and self._telegram_app is not None:
            if self._telegram_app.updater is not None:
                await self._telegram_app.updater.stop()
            await self._telegram_app.stop()
            await self._telegram_app.shutdown()

    async def _start_bot(self) -> None:
        app = Application.builder().token(self.settings.telegram_bot_token).build()
        app.add_handler(CommandHandler("start", self._command_start))
        app.add_handler(CommandHandler("status", self._command_status))
        await app.initialize()
        await app.start()
        if app.updater is not None:
            await app.updater.start_polling()
        self._telegram_app = app
        logger.info("telegram_bot_started")

    def _connect_mqtt(self) -> None:
        delay = self.settings.mqtt_reconnect_initial
        while True:
            try:
                logger.info(
                    "telegram_notifier_connect_mqtt",
                    extra={"host": self.settings.mqtt_host, "port": self.settings.mqtt_port},
                )
                self._client.connect(self.settings.mqtt_host, self.settings.mqtt_port, self.settings.mqtt_keepalive)
                self._client.loop_start()
                break
            except Exception as exc:  # pragma: no cover - network failure path
                logger.warning("telegram_notifier_mqtt_failed", extra={"error": str(exc), "next_retry": delay})
                time.sleep(delay)
                delay = min(delay * 2, self.settings.mqtt_reconnect_max)

    def _on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            logger.info("telegram_notifier_connected", extra={"topic": self.settings.mqtt_topic})
            client.subscribe(self.settings.mqtt_topic, qos=1)
        else:  # pragma: no cover - connection error path
            logger.error("telegram_notifier_connect_error", extra={"rc": rc})

    def _on_disconnect(self, client, userdata, rc):  # pragma: no cover - network path
        logger.warning("telegram_notifier_disconnected", extra={"rc": rc})

    def _on_message(self, client, userdata, message):
        try:
            payload = json.loads(message.payload.decode("utf-8"))
            insight = Insight(
                device_id=str(payload.get("device_id", "")).strip(),
                level=str(payload.get("level", "")).upper(),
                summary=str(payload.get("summary", "")).strip(),
                recommendation=(payload.get("recommendation") or None),
                last_temp_c=float(payload.get("last_temp_c", 0.0)),
                window_avg_c=float(payload.get("window_avg_c", 0.0)),
                ts=self._parse_ts(payload.get("ts")),
            )
        except Exception as exc:
            logger.warning("insight_parse_failed", extra={"error": str(exc)})
            return

        if not insight.device_id:
            return

        with self._lock:
            self._history.appendleft(insight)

        if insight.level not in {"WARN", "ALERT"}:
            return

        if not self.enabled:
            logger.info("insight_received", extra={"device": insight.device_id, "level": insight.level})
            return

        if not self._can_notify(insight):
            return

        text = self._format_message(insight)
        if self.loop and self._telegram_app is not None:
            asyncio.run_coroutine_threadsafe(self._send(text), self.loop)

    def _can_notify(self, insight: Insight) -> bool:
        cooldown = timedelta(seconds=self.settings.notifier_cooldown)
        last = self._last_sent.get(insight.device_id)
        if last and insight.ts - last < cooldown:
            return False
        self._last_sent[insight.device_id] = insight.ts
        return True

    async def _send(self, text: str) -> None:
        assert self._telegram_app is not None
        try:
            await self._telegram_app.bot.send_message(chat_id=self.settings.telegram_chat_id, text=text)
        except Exception as exc:  # pragma: no cover - network failure path
            logger.error("telegram_send_failed", extra={"error": str(exc)})

    def _format_message(self, insight: Insight) -> str:
        recommendation = insight.recommendation or "Pantau kondisi perangkat."
        return (
            "🔔 Siap Suhu — {level}\n"
            "Device: {device}\n"
            "Suhu: {temp:.1f}°C (rata2 {avg:.1f}°C)\n"
            "{summary}\n"
            "Saran: {recommendation}"
        ).format(
            level=insight.level,
            device=insight.device_id,
            temp=insight.last_temp_c,
            avg=insight.window_avg_c,
            summary=insight.summary,
            recommendation=recommendation,
        )

    def _parse_ts(self, value) -> datetime:
        if isinstance(value, str) and value.endswith("Z"):
            value = value[:-1] + "+00:00"
        if isinstance(value, str):
            try:
                return datetime.fromisoformat(value).astimezone(timezone.utc)
            except ValueError:
                pass
        return datetime.now(tz=timezone.utc)

    async def _command_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if update.message is None:
            return
        await update.message.reply_text(
            "Halo! Notifikasi Siap Suhu aktif. Gunakan /status untuk ringkasan terakhir.")

    async def _command_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if update.message is None:
            return
        if not self._history:
            await update.message.reply_text("Belum ada insight yang diterima.")
            return
        lines = ["Ringkasan insight terbaru:"]
        for item in list(self._history)[:5]:
            lines.append(
                f"{item.ts.isoformat().replace('+00:00', 'Z')} • {item.device_id} • {item.level} • {item.last_temp_c:.1f}°C"
            )
        await update.message.reply_text("\n".join(lines))


__all__ = ["TelegramNotifier"]
