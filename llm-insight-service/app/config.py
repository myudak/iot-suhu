from pydantic import BaseSettings, Field


class Settings(BaseSettings):
    mqtt_host: str = Field("mosquitto", alias="MQTT_HOST")
    mqtt_port: int = Field(1883, alias="MQTT_PORT")
    mqtt_user: str = Field("", alias="MQTT_USER")
    mqtt_pass: str = Field("", alias="MQTT_PASS")
    mqtt_keepalive: int = Field(60, alias="MQTT_KEEPALIVE")
    mqtt_client_id: str = Field("siap-suhu-llm", alias="MQTT_CLIENT_ID")
    telemetry_topic: str = Field("siapsuhu/telemetry/#", alias="MQTT_TELEMETRY_TOPIC")
    insight_topic_prefix: str = Field("siapsuhu/insight", alias="MQTT_INSIGHT_TOPIC")
    mqtt_reconnect_initial: float = Field(1.0, alias="MQTT_RECONNECT_INITIAL")
    mqtt_reconnect_max: float = Field(30.0, alias="MQTT_RECONNECT_MAX")

    warn_threshold: float = Field(30.0, alias="INSIGHT_WARN_THRESHOLD")
    alert_threshold: float = Field(35.0, alias="INSIGHT_ALERT_THRESHOLD")
    alert_delta: float = Field(5.0, alias="INSIGHT_ALERT_DELTA")
    window_minutes: int = Field(15, alias="INSIGHT_WINDOW_MINUTES")

    gemini_api_key: str = Field("", alias="GEMINI_API_KEY")
    gemini_model: str = Field("gemini-1.5-flash", alias="GEMINI_MODEL")

    db_path: str = Field("/data/siapsuhu.db", alias="DB_PATH")
    publish_qos: int = Field(1, alias="MQTT_PUBLISH_QOS")
    publish_retain: bool = Field(False, alias="MQTT_PUBLISH_RETAIN")

    insight_alert_cooldown: int = Field(120, alias="INSIGHT_ALERT_COOLDOWN_SECONDS")

    class Config:
        env_file = ".env"
        case_sensitive = False
