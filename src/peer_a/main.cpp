#include <Arduino.h>
#include <ESP8266WiFi.h>
#include "transport.h"



// ============================================================
// SETUP
// ============================================================

void setup() {
  Serial.begin(115200);
  Serial.println();
  Serial.println();

  WiFi.mode(WIFI_STA);
  WiFi.disconnect();
  wifi_set_channel(1);

  Serial.println("ESP8266 ESP-NOW Example");

  Serial.println("ROLE: RECEIVER");

  printLocalMAC();

  initESPNow();

  // Device role
  esp_now_set_self_role(ESP_NOW_ROLE_COMBO);

  registerCallbacks();

  configurePeer();
}

// ============================================================
// LOOP
// ============================================================

void loop() {

}
