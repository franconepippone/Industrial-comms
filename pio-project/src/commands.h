#include <Arduino.h>

enum UserCommand {
  SEND,
  HOP,
  CURRENT_CHN,
  NO_OP,
  ACK_LOSS_P,
  SEND_LOSS_P,
  IDENT_RQST,
  PAUSE_AUTOHOP,
  RESUME_AUTOHOP
};

UserCommand processSerialInput() {
  if (Serial.available()) {
    uint8 c = Serial.read();
    switch (c) {
      case 's':
        return SEND;

      case 'h':
        return HOP;

      case 'c':
        return CURRENT_CHN;
      
      case 'a':
        return ACK_LOSS_P;
      
      case 'l':
        return SEND_LOSS_P;
      
      case 'i':
        return IDENT_RQST;
      
      case 'p':
        return PAUSE_AUTOHOP;
      
      case 'r':
        return RESUME_AUTOHOP;

    }
  }
  return NO_OP;
}
