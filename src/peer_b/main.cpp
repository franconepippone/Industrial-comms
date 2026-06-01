#include <Arduino.h>
#include <ESP8266WiFi.h>
#include "robust_msg.h"



uint8_t receiverMAC[6] = {0xE0, 0x98, 0x06, 0x85, 0xAC, 0x69}; // TODO replace with actual peer MAC


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
  RobustMsg::setQoS({
    10, // retry max amount
    10, // retry base delay ms
    1000 // retry timeout ms
  });

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
      "Hello #%u",
      outgoingMessage.counter);

    Serial.println();
    Serial.println("Sending packet...");

    int result = RobustMsg::send((uint8_t*) &outgoingMessage, sizeof(outgoingMessage));

    if (result == 0) {
      Serial.println("Send request queued");
    } else {
      Serial.print("Send error: ");
      Serial.println(result);
    }
  }

}
