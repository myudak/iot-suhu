from pydantic import BaseSettings, Field


class Settings(BaseSettings):
    mqtt_host: str = Field("mosquitto", alias="MQTT_HOST")
    mqtt_port: int = Field(1883, alias="MQTT_PORT")
    mqtt_user: str = Field("", alias="MQTT_USER")
    mqtt_pass: str = Field("", alias="MQTT_PASS")
    mqtt_keepalive: int = Field(60, alias="MQTT_KEEPALIVE")
    mqtt_topic: str = Field("siapsuhu/insight/#", alias="MQTT_INSIGHT_TOPIC")
    mqtt_reconnect_initial: float = Field(1.0, alias="MQTT_RECONNECT_INITIAL")
    mqtt_reconnect_max: float = Field(30.0, alias="MQTT_RECONNECT_MAX")

    telegram_bot_token: str = Field("", alias="TELEGRAM_BOT_TOKEN")
    telegram_chat_id: str = Field("", alias="TELEGRAM_CHAT_ID")
    notifier_cooldown: int = Field(120, alias="NOTIFIER_ALERT_COOLDOWN_SECONDS")

    status_history_size: int = Field(10, alias="NOTIFIER_STATUS_HISTORY_SIZE")

    class Config:
        env_file = ".env"
        case_sensitive = False
