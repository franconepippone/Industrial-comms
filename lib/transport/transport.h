#include <Arduino.h>

#include <ESP8266WiFi.h>
extern "C" {
  #include <espnow.h>
}

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

class Endpoint {
private:    
    uint8 peermac[6] = {0};
    
public:
    Endpoint() {};

    String getLocalMac() {
        return WiFi.macAddress();
    }

    void setPeerMac(uint8* mac) {
        memcpy(peermac, mac, 6);
    }

    int begin() {
        // init wifi
        WiFi.mode(WIFI_STA);
        WiFi.disconnect();

        // init esp now
        int result = esp_now_init();
        return result;
    }

};


/* Takes a 18-char output array and a raw mac address array, and prints
human readable MAC addres into output array.
*/
void formatMac(char *strOutput, const uint8_t *mac_addr) {
    snprintf(strOutput, 18,
             "%02X:%02X:%02X:%02X:%02X:%02X",
             mac_addr[0], mac_addr[1], mac_addr[2],
             mac_addr[3], mac_addr[4], mac_addr[5]);
}

void initializeWifi() {
    WiFi.mode(WIFI_STA);
    WiFi.disconnect();
}

void initESPNow() {
    if (esp_now_init() != 0) {
      Serial.println("ESP-NOW init failed");
      ESP.restart();
    }
  
    Serial.println("ESP-NOW initialized");
}

void initialize() {
    initializeWifi();
    initESPNow();
}

// ============================================================
// CONFIGURATION
// ============================================================


// Receiver MAC address
// Replace with your receiver MAC
uint8_t receiverMAC[] = {0xE0, 0x98, 0x06, 0x86, 0x1C, 0xF4};



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
