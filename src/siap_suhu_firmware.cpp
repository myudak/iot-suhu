#include <Arduino.h>
#include <ArduinoMqttClient.h>
#include <DHT.h>
#include <WiFi.h>
#include <cstring>
#include <time.h>

#include "siap_suhu_firmware.h"

#ifdef __has_include
#if __has_include("secrets.h")
#include "secrets.h"
#endif
#endif

#ifndef WIFI_SSID
#define WIFI_SSID "Wokwi-GUEST"
#endif

#ifndef WIFI_PASS
#define WIFI_PASS ""
#endif

#ifndef MQTT_HOST
#define MQTT_HOST "mqtt"
#endif

#ifndef MQTT_PORT
#define MQTT_PORT 1883
#endif

#ifndef MQTT_USER
#define MQTT_USER ""
#endif

#ifndef MQTT_PASS
#define MQTT_PASS ""
#endif

#ifndef DHT_PIN
#define DHT_PIN 15
#endif

#ifndef DHT_TYPE
#define DHT_TYPE DHT22
#endif

#ifndef TELEMETRY_INTERVAL_MS
#define TELEMETRY_INTERVAL_MS 5000UL
#endif

#define FW_VERSION "siap-suhu-1.0.0"

static WiFiClient wifiClient;
static MqttClient mqttClient(wifiClient);
static DHT dht(DHT_PIN, DHT_TYPE);

static String deviceId;
static String telemetryTopic;
static String statusTopic;

static unsigned long lastTelemetryAt = 0;
static unsigned long lastWiFiAttempt = 0;
static unsigned long lastTimeSync = 0;

static void ensureWiFi();
static void ensureMqtt();
static void publishTelemetry();
static String getIsoTimestamp();
static String getDeviceId();
static void syncTimeIfNeeded();
static void setupMqttWill();

void siapSuhuSetup() {
  Serial.begin(115200);
  delay(500);
  deviceId = getDeviceId();
  telemetryTopic = "siapsuhu/telemetry/" + deviceId;
  statusTopic = "siapsuhu/status/" + deviceId;

  WiFi.mode(WIFI_STA);
  WiFi.setAutoReconnect(true);
  WiFi.setSleep(false);

  dht.begin();

  ensureWiFi();
  syncTimeIfNeeded();
  ensureMqtt();
}

void siapSuhuLoop() {
  ensureWiFi();
  ensureMqtt();
  mqttClient.poll();
  syncTimeIfNeeded();

  unsigned long now = millis();
  if (now - lastTelemetryAt >= TELEMETRY_INTERVAL_MS) {
    publishTelemetry();
    lastTelemetryAt = now;
  }
}

static void ensureWiFi() {
  if (WiFi.status() == WL_CONNECTED) {
    return;
  }

  unsigned long now = millis();
  if (now - lastWiFiAttempt < 2000UL) {
    return;
  }
  lastWiFiAttempt = now;

  Serial.printf("[WiFi] Menghubungkan ke SSID %s\n", WIFI_SSID);
  WiFi.begin(WIFI_SSID, WIFI_PASS);

  uint8_t attempts = 0;
  while (WiFi.status() != WL_CONNECTED && attempts < 20) {
    delay(500);
    Serial.print('.');
    attempts++;
  }
  Serial.println();

  if (WiFi.status() == WL_CONNECTED) {
    Serial.printf("[WiFi] Terhubung, IP: %s RSSI: %d\n", WiFi.localIP().toString().c_str(), WiFi.RSSI());
    lastTimeSync = 0;  // paksa sync ulang setelah reconnect
  } else {
    Serial.println("[WiFi] Gagal terhubung, akan retry...");
  }
}

static void setupMqttWill() {
  const char *offlinePayload = "offline";
  mqttClient.beginWill(statusTopic.c_str(), strlen(offlinePayload), false, 1);
  mqttClient.print(offlinePayload);
  mqttClient.endWill();
}

static void ensureMqtt() {
  if (mqttClient.connected() || WiFi.status() != WL_CONNECTED) {
    return;
  }

  Serial.println("[MQTT] Menghubungkan ke broker...");

  mqttClient.stop();
  mqttClient.setId(("siapsuhu-" + deviceId).c_str());

  if (strlen(MQTT_USER) > 0) {
    mqttClient.setUsernamePassword(MQTT_USER, MQTT_PASS);
  } else {
    mqttClient.setUsernamePassword("", "");
  }
  mqttClient.setCleanSession(true);

  setupMqttWill();

  if (!mqttClient.connect(MQTT_HOST, MQTT_PORT)) {
    Serial.printf("[MQTT] Gagal connect, kode %d\n", mqttClient.connectError());
    delay(2000);
    return;
  }

  Serial.println("[MQTT] Terhubung");

  mqttClient.beginMessage(statusTopic.c_str(), false, 1);
  mqttClient.print("online");
  mqttClient.endMessage();
}

static void publishTelemetry() {
  if (!mqttClient.connected()) {
    return;
  }

  float humidity = dht.readHumidity();
  float temperature = dht.readTemperature();

  if (isnan(humidity) || isnan(temperature)) {
    Serial.println("[Sensor] Pembacaan DHT tidak valid, dilewati");
    return;
  }

  int rssi = WiFi.RSSI();
  String timestamp = getIsoTimestamp();

  char payload[256];
  snprintf(payload, sizeof(payload),
           "{\"device_id\":\"%s\",\"ts\":\"%s\",\"temp_c\":%.2f,\"humidity\":%.2f,\"rssi\":%d,\"fw\":\"%s\"}",
           deviceId.c_str(), timestamp.c_str(), temperature, humidity, rssi, FW_VERSION);

  Serial.printf("[MQTT] Publish %s: %s\n", telemetryTopic.c_str(), payload);
  mqttClient.beginMessage(telemetryTopic.c_str(), false, 1);
  mqttClient.print(payload);
  mqttClient.endMessage();
}

static String getIsoTimestamp() {
  struct tm timeinfo;
  if (getLocalTime(&timeinfo, 1000)) {
    char buffer[25];
    strftime(buffer, sizeof(buffer), "%Y-%m-%dT%H:%M:%SZ", &timeinfo);
    return String(buffer);
  }

  unsigned long ms = millis();
  char buffer[30];
  snprintf(buffer, sizeof(buffer), "1970-01-01T00:00:%02luZ", (ms / 1000UL) % 60UL);
  return String(buffer);
}

static void syncTimeIfNeeded() {
  if (WiFi.status() != WL_CONNECTED) {
    return;
  }

  unsigned long now = millis();
  if (lastTimeSync != 0 && (now - lastTimeSync) < 3600000UL) {
    return;
  }

  configTime(0, 0, "pool.ntp.org", "time.google.com", "id.pool.ntp.org");
  struct tm timeinfo;
  if (getLocalTime(&timeinfo, 5000)) {
    Serial.println("[NTP] Sinkronisasi waktu berhasil");
    lastTimeSync = now;
  } else {
    Serial.println("[NTP] Gagal sinkron waktu");
  }
}

static String getDeviceId() {
  uint64_t chipid = ESP.getEfuseMac();
  char buffer[17];
  snprintf(buffer, sizeof(buffer), "%012llX", (unsigned long long)chipid);
  return String(buffer);
}
