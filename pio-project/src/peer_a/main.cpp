#include <Arduino.h>
#include <ESP8266WiFi.h>
#include "robust_msg.h"

#include "commands.h"

uint8_t receiverMAC[6] = {0xE0, 0x98, 0x06, 0x86, 0x1C, 0xF4}; // TODO replace with actual peer MAC


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


  Serial.println("ESP8266 ROBUST_MSG Example");
  Serial.println("ROLE: RECEIVER");

  log_ui("IDENT", WiFi.macAddress(), "Peer-A (receiver)");

  RobustMsg::printLocalMAC();
  RobustMsg::initialize(1, receiverMAC);
  RobustMsg::setProtocolParams({
    10, // retry max amount
    100, // retry base delay ms
    1000 // retry timeout ms
  });

}

// ============================================================
// LOOP
// ============================================================


void loop() {
  delay(100);
  RobustMsg::processPendingOperations();
  UserCommand cm = processSerialInput();

  if (cm == IDENT_RQST) {
    log_ui("IDENT", WiFi.macAddress(), "Peer-A (receiver)");
  } 
}
