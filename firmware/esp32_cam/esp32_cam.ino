/*
 * ESP32-CAM — SoftAP provisioning from dashboard, then capture + POST /predict.
 *
 * Setup mode (no saved WiFi):
 *   SoftAP SSID "EWaste-Setup" @ 192.168.4.1
 *   POST /config  JSON: {ssid, password, api_base_url, interval_ms}
 *
 * After credentials are saved to NVS, joins home WiFi and uploads every interval_ms.
 *
 * Libraries: ArduinoJson
 * Board: AI Thinker ESP32-CAM
 */

#include "esp_camera.h"
#include <WiFi.h>
#include <WebServer.h>
#include <HTTPClient.h>
#include <Preferences.h>
#include <ArduinoJson.h>
#include "soc/soc.h"
#include "soc/rtc_cntl_reg.h"

Preferences prefs;
WebServer setupServer(80);

String wifiSsid = "Debonik";
String wifiPassword = "debonik@2005";
String apiBaseUrl = "http://192.168.0.205:8080";
unsigned long intervalMs = 1000;

const int JPEG_QUALITY = 12;
const framesize_t FRAME_SIZE = FRAMESIZE_VGA;
const int WIFI_RETRY_DELAY_MS = 3000;
const int UPLOAD_RETRIES = 3;
const int HTTP_TIMEOUT_MS = 20000;
const char* SOFTAP_SSID = "EWaste-Setup";
const char* SOFTAP_PASS = "ewaste123";  // open-ish lab password for SoftAP itself

#define PWDN_GPIO_NUM     32
#define RESET_GPIO_NUM    -1
#define XCLK_GPIO_NUM      0
#define SIOD_GPIO_NUM     26
#define SIOC_GPIO_NUM     27
#define Y9_GPIO_NUM       35
#define Y8_GPIO_NUM       34
#define Y7_GPIO_NUM       39
#define Y6_GPIO_NUM       36
#define Y5_GPIO_NUM       21
#define Y4_GPIO_NUM       19
#define Y3_GPIO_NUM       18
#define Y2_GPIO_NUM        5
#define VSYNC_GPIO_NUM    25
#define HREF_GPIO_NUM     23
#define PCLK_GPIO_NUM     22

unsigned long lastCaptureMs = 0;
bool setupMode = false;

String predictUrl() {
  String base = apiBaseUrl;
  while (base.endsWith("/")) {
    base.remove(base.length() - 1);
  }
  if (base.endsWith("/predict")) {
    return base;
  }
  return base + "/predict";
}

void loadPrefs() {
  prefs.begin("ewaste", true);
  wifiSsid = prefs.getString("ssid", "");
  wifiPassword = prefs.getString("pass", "");
  apiBaseUrl = prefs.getString("api", apiBaseUrl);
  intervalMs = prefs.getULong("interval", 5000);
  if (intervalMs < 1000) {
    intervalMs = 5000;
  }
  prefs.end();
}

void savePrefs(const String& ssid, const String& pass, const String& api, unsigned long interval) {
  prefs.begin("ewaste", false);
  prefs.putString("ssid", ssid);
  prefs.putString("pass", pass);
  prefs.putString("api", api);
  prefs.putULong("interval", interval);
  prefs.end();
  wifiSsid = ssid;
  wifiPassword = pass;
  apiBaseUrl = api;
  intervalMs = interval;
}

bool initCamera() {
  camera_config_t config;
  config.ledc_channel = LEDC_CHANNEL_0;
  config.ledc_timer = LEDC_TIMER_0;
  config.pin_d0 = Y2_GPIO_NUM;
  config.pin_d1 = Y3_GPIO_NUM;
  config.pin_d2 = Y4_GPIO_NUM;
  config.pin_d3 = Y5_GPIO_NUM;
  config.pin_d4 = Y6_GPIO_NUM;
  config.pin_d5 = Y7_GPIO_NUM;
  config.pin_d6 = Y8_GPIO_NUM;
  config.pin_d7 = Y9_GPIO_NUM;
  config.pin_xclk = XCLK_GPIO_NUM;
  config.pin_pclk = PCLK_GPIO_NUM;
  config.pin_vsync = VSYNC_GPIO_NUM;
  config.pin_href = HREF_GPIO_NUM;
  config.pin_sccb_sda = SIOD_GPIO_NUM;
  config.pin_sccb_scl = SIOC_GPIO_NUM;
  config.pin_pwdn = PWDN_GPIO_NUM;
  config.pin_reset = RESET_GPIO_NUM;
  config.xclk_freq_hz = 10000000; // Lowered to 10MHz to prevent FB-OVF
  config.pixel_format = PIXFORMAT_JPEG;
  config.frame_size = FRAME_SIZE;
  config.jpeg_quality = JPEG_QUALITY;
  
  if (psramFound()) {
    config.fb_count = 2;
    config.grab_mode = CAMERA_GRAB_LATEST;
  } else {
    config.fb_count = 1;
    config.grab_mode = CAMERA_GRAB_WHEN_EMPTY;
  }

  esp_err_t err = esp_camera_init(&config);
  if (err != ESP_OK) {
    Serial.printf("Camera init failed: 0x%x\n", err);
    return false;
  }
  return true;
}

void sendCorsHeaders() {
  setupServer.sendHeader("Access-Control-Allow-Origin", "*");
  setupServer.sendHeader("Access-Control-Allow-Methods", "GET, POST, OPTIONS");
  setupServer.sendHeader("Access-Control-Allow-Headers", "Content-Type");
}

void handleRoot() {
  sendCorsHeaders();
  setupServer.send(
      200,
      "text/plain",
      "EWaste-Setup SoftAP ready.\n"
      "Use the dashboard Device Setup modal, connect PC to this WiFi,\n"
      "then Push to ESP32 (POST /config).\n");
}

void handleOptions() {
  sendCorsHeaders();
  setupServer.send(204);
}

void handleConfigPost() {
  sendCorsHeaders();
  if (!setupServer.hasArg("plain")) {
    setupServer.send(400, "application/json", "{\"ok\":false,\"error\":\"empty body\"}");
    return;
  }

  StaticJsonDocument<768> doc;
  DeserializationError err = deserializeJson(doc, setupServer.arg("plain"));
  if (err) {
    setupServer.send(400, "application/json", "{\"ok\":false,\"error\":\"invalid json\"}");
    return;
  }

  const char* ssid = doc["ssid"] | doc["wifi_ssid"] | "";
  const char* pass = doc["password"] | doc["wifi_password"] | "";
  const char* api = doc["api_base_url"] | doc["api"] | "";
  unsigned long interval = doc["interval_ms"] | doc["capture_interval_ms"] | 5000;

  if (strlen(ssid) == 0 || strlen(api) == 0) {
    setupServer.send(400, "application/json", "{\"ok\":false,\"error\":\"ssid and api_base_url required\"}");
    return;
  }

  savePrefs(String(ssid), String(pass), String(api), interval);
  setupServer.send(200, "application/json", "{\"ok\":true,\"message\":\"saved — rebooting\"}");
  delay(500);
  ESP.restart();
}

void handleStatus() {
  sendCorsHeaders();
  StaticJsonDocument<256> doc;
  doc["setup_mode"] = setupMode;
  doc["ssid_saved"] = wifiSsid.length() > 0;
  doc["api_base_url"] = apiBaseUrl;
  doc["interval_ms"] = intervalMs;
  String out;
  serializeJson(doc, out);
  setupServer.send(200, "application/json", out);
}

void startSoftAP() {
  setupMode = true;
  WiFi.mode(WIFI_AP);
  WiFi.softAP(SOFTAP_SSID, SOFTAP_PASS);
  IPAddress ip = WiFi.softAPIP();
  Serial.printf("Setup SoftAP '%s' (pass %s) IP=%s\n", SOFTAP_SSID, SOFTAP_PASS, ip.toString().c_str());
  Serial.println("Connect PC to EWaste-Setup, open dashboard Device Setup, Push to ESP32");

  setupServer.on("/", HTTP_GET, handleRoot);
  setupServer.on("/status", HTTP_GET, handleStatus);
  setupServer.on("/config", HTTP_POST, handleConfigPost);
  setupServer.on("/config", HTTP_OPTIONS, handleOptions);
  setupServer.on("/status", HTTP_OPTIONS, handleOptions);
  setupServer.begin();
}

bool connectWiFiStation() {
  if (wifiSsid.length() == 0) {
    return false;
  }
  Serial.printf("Connecting to WiFi SSID=%s\n", wifiSsid.c_str());
  WiFi.mode(WIFI_STA);
  WiFi.begin(wifiSsid.c_str(), wifiPassword.c_str());
  unsigned long start = millis();
  while (WiFi.status() != WL_CONNECTED) {
    delay(400);
    Serial.print(".");
    if (millis() - start > 45000) {
      Serial.println("\nWiFi timeout");
      return false;
    }
  }
  Serial.println();
  Serial.print("WiFi OK, IP=");
  Serial.println(WiFi.localIP());
  Serial.print("Predict URL=");
  Serial.println(predictUrl());
  setupMode = false;
  return true;
}

bool uploadFrame(camera_fb_t* fb) {
  String boundary = "----EwasteBoundary7MA4YWxkTrZu0gW";
  String head = "--" + boundary + "\r\n"
                "Content-Disposition: form-data; name=\"file\"; filename=\"frame.jpg\"\r\n"
                "Content-Type: image/jpeg\r\n\r\n";
  String tail = "\r\n--" + boundary + "--\r\n";

  size_t totalLen = head.length() + fb->len + tail.length();
  uint8_t* body = (uint8_t*)malloc(totalLen);
  if (!body) {
    Serial.println("Out of memory building multipart body");
    return false;
  }
  memcpy(body, head.c_str(), head.length());
  memcpy(body + head.length(), fb->buf, fb->len);
  memcpy(body + head.length() + fb->len, tail.c_str(), tail.length());

  String url = predictUrl();
  bool ok = false;
  for (int attempt = 1; attempt <= UPLOAD_RETRIES; attempt++) {
    HTTPClient http;
    http.setTimeout(HTTP_TIMEOUT_MS);
    if (!http.begin(url)) {
      Serial.println("HTTP begin failed");
      delay(500);
      continue;
    }
    http.addHeader("Content-Type", "multipart/form-data; boundary=" + boundary);
    int code = http.POST(body, totalLen);
    String response = http.getString();
    http.end();

    Serial.printf("Upload attempt %d → HTTP %d\n", attempt, code);
    Serial.println(response);

    if (code >= 200 && code < 300) {
      StaticJsonDocument<512> doc;
      DeserializationError err = deserializeJson(doc, response);
      if (!err) {
        bool ewaste = doc["ewaste"] | false;
        const char* category = doc["category"] | "unknown";
        float confidence = doc["confidence"] | 0.0f;
        Serial.printf("RESULT ewaste=%s category=%s confidence=%.3f\n",
                      ewaste ? "true" : "false", category, confidence);
      }
      ok = true;
      break;
    }
    delay(750);
  }

  free(body);
  return ok;
}

void setup() {
  Serial.begin(115200);
  delay(800);
  Serial.println("ESP32-CAM e-waste client starting");
  WRITE_PERI_REG(RTC_CNTL_BROWN_OUT_REG, 0); // Disable brownout detector to prevent reboots on minor voltage dips

  // loadPrefs();

  if (!initCamera()) {
    Serial.println("Halting — camera init failed");
    while (true) {
      delay(1000);
    }
  }

  if (wifiSsid.length() == 0 || !connectWiFiStation()) {
    Serial.println("No WiFi credentials or connect failed — entering SoftAP setup");
    startSoftAP();
  }

  lastCaptureMs = millis() - intervalMs;
}

void loop() {
  if (setupMode) {
    setupServer.handleClient();
    delay(2);
    return;
  }

  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("WiFi lost — reconnecting");
    if (!connectWiFiStation()) {
      startSoftAP();
      return;
    }
  }

  unsigned long now = millis();
  if (now - lastCaptureMs < intervalMs) {
    delay(40);
    return;
  }
  lastCaptureMs = now;

  camera_fb_t* fb = esp_camera_fb_get();
  if (!fb) {
    Serial.println("Camera capture failed");
    return;
  }

  Serial.printf("Captured %u bytes (Free Heap: %u) → %s\n", fb->len, ESP.getFreeHeap(), predictUrl().c_str());
  bool success = uploadFrame(fb);
  esp_camera_fb_return(fb);

  if (!success) {
    Serial.println("Upload failed after retries");
  }
}
