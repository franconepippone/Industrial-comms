#include <Arduino.h>

#include <ESP8266WiFi.h>
extern "C" {
  #include <espnow.h>
}

// ============================================================
// CONFIGURATION
// ============================================================


// Receiver MAC address
// Replace with your receiver MAC
uint8_t receiverMAC[] = {0x24, 0x6F, 0x28, 0xAA, 0xBB, 0xCC};

// ============================================================
// DATA STRUCTURE
// ============================================================

struct Message {
  uint32_t counter;
  float temperature;
  char text[32];
};

Message outgoingMessage;
Message incomingMessage;

uint32_t sendCounter = 0;
unsigned long lastSend = 0;

// ============================================================
// CALLBACKS
// ============================================================

// Called after packet transmission
void onDataSent(uint8_t *mac_addr, uint8_t sendStatus) {
  Serial.println();
  Serial.println("===== SEND CALLBACK =====");

  char macStr[18];
  snprintf(macStr, sizeof(macStr),
           "%02X:%02X:%02X:%02X:%02X:%02X",
           mac_addr[0], mac_addr[1], mac_addr[2],
           mac_addr[3], mac_addr[4], mac_addr[5]);

  Serial.print("Target MAC: ");
  Serial.println(macStr);

  Serial.print("Send status: ");

  if (sendStatus == 0) {
    Serial.println("SUCCESS");
  } else {
    Serial.println("FAIL");
  }

  Serial.println("=========================");
}

// Called when data is received
void onDataReceived(uint8_t *mac_addr, uint8_t *incomingData, uint8_t len) {
  Serial.println();
  Serial.println("===== RECEIVE CALLBACK =====");

  char macStr[18];
  snprintf(macStr, sizeof(macStr),
           "%02X:%02X:%02X:%02X:%02X:%02X",
           mac_addr[0], mac_addr[1], mac_addr[2],
           mac_addr[3], mac_addr[4], mac_addr[5]);

  Serial.print("Sender MAC: ");
  Serial.println(macStr);

  Serial.print("Payload size: ");
  Serial.println(len);

  memcpy(&incomingMessage, incomingData, sizeof(incomingMessage));

  Serial.print("Counter: ");
  Serial.println(incomingMessage.counter);

  Serial.print("Temperature: ");
  Serial.println(incomingMessage.temperature);

  Serial.print("Text: ");
  Serial.println(incomingMessage.text);

  Serial.println("============================");
}

// ============================================================
// UTILITY
// ============================================================

void printLocalMAC() {
  Serial.print("Local MAC: ");
  Serial.println(WiFi.macAddress());
}

void initESPNow() {
  if (esp_now_init() != 0) {
    Serial.println("ESP-NOW init failed");
    ESP.restart();
  }

  Serial.println("ESP-NOW initialized");
}

void registerCallbacks() {
  esp_now_register_send_cb(onDataSent);
  esp_now_register_recv_cb(onDataReceived);

  Serial.println("Callbacks registered");
}

void configurePeer() {
#if DEVICE_ROLE == ROLE_SENDER

  if (esp_now_add_peer(receiverMAC, ESP_NOW_ROLE_COMBO, 1, NULL, 0) != 0) {
    Serial.println("Failed to add peer");
    return;
  }

  Serial.println("Peer added successfully");

#endif
}

// ============================================================
// SETUP
// ============================================================

void setup() {
  Serial.begin(115200);
  Serial.println();
  Serial.println();

  WiFi.mode(WIFI_STA);
  WiFi.disconnect();

  Serial.println("ESP8266 ESP-NOW Example");

  Serial.println("ROLE: SENDER");

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

  if (millis() - lastSend > 3000) {
    lastSend = millis();

    outgoingMessage.counter = sendCounter++;
    outgoingMessage.temperature = random(200, 350) / 10.0;

    snprintf(outgoingMessage.text,
             sizeof(outgoingMessage.text),
             "Hello #%lu",
             outgoingMessage.counter);

    Serial.println();
    Serial.println("Sending packet...");

    uint8_t result = esp_now_send(
      receiverMAC,
      (uint8_t *) &outgoingMessage,
      sizeof(outgoingMessage)
    );

    if (result == 0) {
      Serial.println("Send request queued");
    } else {
      Serial.print("Send error: ");
      Serial.println(result);
    }
  }

}
