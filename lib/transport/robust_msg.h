#include <Arduino.h>

#include <ESP8266WiFi.h>
extern "C" {
  #include <espnow.h>
}



void debugOnSent(uint8_t *mac_addr, uint8_t sendStatus) {
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


struct RobustMsgQoS {
    uint8 RETRY_MAX_AMOUNT;
    uint32 RETRY_BASE_DELAY_MS; // TODO make this full integer arithmetic
    //float RETRY_GROWTH;
    uint32 RETRY_TIMEOUT;
};


struct SendResult {
    bool finished;
    uint8_t macAddr[6];
    uint8_t sendStatus;
};

class RobustMsg {
private:
    inline static uint8_t peerMAC[6] = {0};
    inline static bool isInit = false;
    inline static RobustMsgQoS qos = {
        10,
        10,
        //1.2,
        1000
    };

    inline static SendResult sendResult = {
        .finished = false,
        .macAddr = {0},
        .sendStatus = 0
    };

    // UTILITY METHODS

    static void onDataSent(uint8_t *mac_addr, uint8_t sendStatus) {
        debugOnSent(mac_addr, sendStatus);

        // store result so that it can be retrieved by the main loop
        memcpy(sendResult.macAddr, mac_addr, sizeof(sendResult.macAddr));
        sendResult.sendStatus = sendStatus;
        sendResult.finished = true;
    }
    
    static void initWifi(uint8 channel) {
        WiFi.mode(WIFI_STA);
        WiFi.disconnect();
        wifi_set_channel(channel);
        // TODO handle and return errors
    }
    
    static auto initESPnow() {
        int outcome = esp_now_init();
        if (outcome != 0) {
            Serial.println("ESP-NOW init failed");
            return outcome;
        }

        esp_now_set_self_role(ESP_NOW_ROLE_COMBO);
    
        Serial.println("ESP-NOW initialized");
        return 0; 
    }
    
    static void bindCallbacks() {
        esp_now_register_send_cb(onDataSent);
    }

    inline static bool assertInitialized() {
        if (isInit) {
            Serial.println("RobustMsg not initialized");
            return false;
        }
        return true;
    }

    inline static auto espNowSend(u8* da, u8* data, unsigned int len) {
        sendResult.finished = false; // always reset this for ARQ
        return esp_now_send(da, data, len);
    }
    
public:

    static void printLocalMAC() {
        Serial.print("Local MAC: ");
        Serial.println(WiFi.macAddress());
    }

    static int configurePeer(uint8* peerMac) {
        if (!assertInitialized()) return -1;

        // TODO possibly validate peerMac here
        memcpy(peerMAC, peerMac, sizeof(peerMAC));
        return esp_now_add_peer(peerMAC, ESP_NOW_ROLE_COMBO, 0, NULL, 0);
    }

    static int initialize(uint8 wifiChannel, uint8* peerMac) {
        // if already initialized, return error code
        if (assertInitialized()) return -1;

        // TODO add per call error handling and return appropriate error codes
        bindCallbacks();
        
        initWifi(wifiChannel);
        initESPnow();
        
        configurePeer(peerMac);

        isInit = true;
        return 0;
    }

    static void setQoS(RobustMsgQoS newQoS) {
        qos = newQoS;
    }

    static int send(u8* data, unsigned int len) {
        if (!assertInitialized()) return -1;
        
        espNowSend(peerMAC, data, len);
        
        // ARQ loop
        const auto startTime = millis();
        for (uint8 i = 0; i < qos.RETRY_MAX_AMOUNT; i++) {

            // if send callaback ran
            if (sendResult.finished) {
                if (sendResult.sendStatus == 0) return 0; // on success
                
                // on failure, wait and retry
                delay(qos.RETRY_BASE_DELAY_MS);
                espNowSend(peerMAC, data, len);
            }

            uint32 elapsed = millis() - startTime; // assuming difference fits inside uint32
            if (elapsed > qos.RETRY_TIMEOUT) {
                Serial.println("ARQ timeout reached, aborting send");
                return -1;
            }
        }
        return -2;
    }

};