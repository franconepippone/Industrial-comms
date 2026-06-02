#include <Arduino.h>
#include <ESP8266WiFi.h>
#include "robust_msg.h"



uint8_t receiverMAC[6] = {0xE0, 0x98, 0x06, 0x85, 0xAC, 0x69};


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
// SETUP
// ============================================================

void setup() {
  Serial.begin(115200);
  Serial.println();
  Serial.println();

  Serial.println("ESP8266 ESP-NOW Example");

  Serial.println("ROLE: SENDER");

  RobustMsg::printLocalMAC();
  RobustMsg::initialize(1, receiverMAC);
  RobustMsg::setProtocolParams({
    .RETRY_MAX_AMOUNT = 10,
    .RETRY_BASE_DELAY_MS = 100,
    .SEND_TIMEOUT_MS = 1000,
    .CHANNEL_HOP_TIMEOUT_MS = 2000
  });

}

// ============================================================
// LOOP
// ============================================================


void loop() {
  RobustMsg::processPendingOperations();

  if (millis() - lastSend > 3000) {
    lastSend = millis();

    outgoingMessage.counter = sendCounter++;
    outgoingMessage.temperature = random(200, 350) / 10.0;

    snprintf(outgoingMessage.text,
      sizeof(outgoingMessage.text),
      "Hello #%u",
      outgoingMessage.counter);

    Serial.println();
    Serial.println("Sending packet...");

    ErrorCode result = RobustMsg::send((uint8_t*) &outgoingMessage, sizeof(outgoingMessage), 5);

    if (outgoingMessage.counter % 5 == 0) {
      Serial.println("Hopping channel...");
      auto result = RobustMsg::hopChannel(random(1, 14));
      if (result == ErrorCode::OK) {
        Serial.println("Channel hop ok, waiting for 5 seconds before sending next message...");
        delay(5000);
        int ch = WiFi.channel();
        Serial.print("Current channel: ");
        Serial.println(ch);

      } else {
        Serial.print("Channel hop error: ");
        Serial.println((uint8_t)result);
      }
      
    }

    //int result = esp_now_send(receiverMAC, (uint8_t*) &outgoingMessage, sizeof(outgoingMessage));

    if (result == ErrorCode::OK) {
      Serial.println("Send ok");
    } else {
      Serial.print("Send error: ");
      Serial.println((uint8_t)result);
    }
  }

}
