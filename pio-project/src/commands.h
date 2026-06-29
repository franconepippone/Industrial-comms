#include <Arduino.h>

enum UserCommand {
  SEND,
  HOP,
  CURRENT_CHN,
  NO_OP,
  FAULT_P_UPDATE,
  IDENT_RQST
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
      
      case 'f':
        return FAULT_P_UPDATE;
      
      case 'i':
        return IDENT_RQST;

    }
  }
  return NO_OP;
}
