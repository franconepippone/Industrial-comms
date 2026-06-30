#include <Arduino.h>
#include <ESP8266WiFi.h>
#include "robust_msg.h"

#include "commands.h"

uint8_t receiverMAC[6] = {0xE0, 0x98, 0x06, 0x86, 0x1C, 0xF4}; // TODO replace with actual peer MAC


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
  delay(100);
  RobustMsg::processPendingOperations();
  UserCommand cm = processSerialInput();

  if (cm == IDENT_RQST) {
    log_ui("IDENT", WiFi.macAddress(), "Peer-A (receiver)");
  }

  if (cm == SEND) {

    Serial.println();
    Serial.println("Sending packet...");
    
    // simulate random size
    uint8_t packid = random(1, 100);
    char msg[20] = {0};
    unsigned int size = random(sizeof(msg)-5, sizeof(msg)+10);

    ErrorCode result = RobustMsg::send((uint8_t*) &msg, size, packid);


    if (result == ErrorCode::OK) {
      Serial.println("Send ok");
    } else {
      Serial.print("Send error: ");
      Serial.println((uint8_t)result);
    }

  }


  // perform a hop to random channel
  if (cm == HOP) {
    Serial.println("Hopping channel...");
    auto result = RobustMsg::hopChannel(random(1, 14));
    if (result == ErrorCode::OK) {
      int ch = WiFi.channel();
      Serial.print("Current channel: ");
      Serial.println(ch);

    } else {
      Serial.print("Channel hop error: ");
      Serial.println((uint8_t)result);
    }
  }

  if (cm == CURRENT_CHN) {
    int ch = WiFi.channel();
    Serial.print("Current channel: ");
    Serial.println(ch);
  }
  
  if (cm == ACK_LOSS_P) {
    long p = Serial.parseInt();
    set_sim_loss_ack_p(p);
    Serial.print("Changed ack loss p to ");
    Serial.println(p);
  }

  if (cm == SEND_LOSS_P) {
    long p = Serial.parseInt();
    set_sim_loss_send_p(p);
    Serial.print("Changed send loss p to ");
    Serial.println(p);
  }
}
