#include <Arduino.h>

#include <ESP8266WiFi.h>
extern "C" {
  #include <espnow.h>
}


#define SERIAL_DEBUG

void debugOnReceived(uint8_t *mac_addr, uint8_t *incomingData, uint8_t len) {
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

  //memcpy(&incomingMessage, incomingData, sizeof(incomingMessage));

  Serial.println("============================");
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



// this is private, can be left outside
struct SendResult {
    bool finished;
    uint8_t macAddr[6];
    uint8_t sendStatus;
};

// prependend to each message, used for duplicate detection and possibly other features in the future
struct __attribute__((packed)) Header {
    uint32_t nonce;
    uint8_t packetId;
};


typedef void (*robust_msg_recv_callback)(u8 *mac_addr, u8 packet_id, u8 *data, u8 len);

class RobustMsg {
public:
    // Inner struct definition for QoS settings for user

    struct QoS {
        uint8 RETRY_MAX_AMOUNT;
        uint32 RETRY_BASE_DELAY_MS; // TODO make this full integer arithmetic
        //float RETRY_GROWTH;
        uint32 RETRY_TIMEOUT;
    };

private:
    inline static uint8_t peerMAC[6] = {0};
    inline static bool isInit = false;
    inline static QoS qos = {
        .RETRY_MAX_AMOUNT = 10,
        .RETRY_BASE_DELAY_MS = 100,
        .RETRY_TIMEOUT = 1000
    };
    inline static SendResult sendResult = {
        .finished = false,
        .macAddr = {0},
        .sendStatus = 0
    };
    inline static robust_msg_recv_callback userRecvCallback = nullptr;
    static uint32_t latestPacketNonce; // for duplicate detection

    // espnow callbacks
    
    static void onDataSent(uint8_t *mac_addr, uint8_t sendStatus) {
        #ifdef SERIAL_DEBUG
        debugOnSent(mac_addr, sendStatus); 
        #endif
        
        // store result so that it can be retrieved by the main loop
        memcpy(sendResult.macAddr, mac_addr, sizeof(sendResult.macAddr));
        sendResult.sendStatus = sendStatus;
        sendResult.finished = true;
    }

    static void onDataReceived(uint8_t *mac_addr, uint8_t *incomingData, uint8_t len) {
        #ifdef SERIAL_DEBUG
        debugOnReceived(mac_addr, incomingData, len);
        #endif

        // avoid crash if packet is malformed
        if (len < sizeof(Header)) {
            Serial.println("Invalid packet: too short");
            return;
        }

        Header& hdr = *reinterpret_cast<Header*>(incomingData);

        // assert is not duplicate
        if (hdr.nonce == latestPacketNonce) {
            Serial.println("Duplicate packet received, ignoring...");
            return;
        }
        latestPacketNonce = hdr.nonce;

        // if user callback is set, call it with the payload (data after header)
        if (userRecvCallback != nullptr) {
            userRecvCallback(mac_addr, hdr.packetId, incomingData + sizeof(Header), len - sizeof(Header));
        }

    }
    
    // UTILITY METHODS

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
        esp_now_register_recv_cb(onDataReceived);
    }

    inline static bool assertInitialized() {
        if (isInit) return true;
        Serial.println("RobustMsg not initialized");
        return false;
    }

    inline static auto sendMessage(u8* da, u8* data, unsigned int len) {
        sendResult.finished = false; // always reset this for ARQ
        
        u8 outboundData[len + sizeof(Header)]; // TODO is this dynamic allocation? might overflow stack

        // prepend header to data
        Header* hdr = reinterpret_cast<Header*>(outboundData);
        *hdr = Header{
            .nonce = (uint32)random(0, UINT32_MAX),
            .packetId = 0
        };

        // copy payload after header
        memcpy(outboundData + sizeof(Header), data, len);
        return esp_now_send(da, outboundData, sizeof(outboundData));
    }
    
public:

    // UTILITY

    static void printLocalMAC() {
        Serial.print("Local MAC: ");
        Serial.println(WiFi.macAddress());
    }

    /* Sets the given mac address as the current peer. */
    static int configurePeer(uint8* macAddr) {
        if (!assertInitialized()) return -1;

        // TODO possibly validate peerMac here
        memcpy(peerMAC, macAddr, sizeof(peerMAC));
        esp_now_del_peer(peerMAC); // in case peer was already added, remove it first to avoid duplicates
        return esp_now_add_peer(peerMAC, ESP_NOW_ROLE_COMBO, 0, NULL, 0);
    }

    /* Initialize wifi and espnow.*/
    static int initialize(uint8 wifiChannel, uint8* peerMac) {
        // if already initialized, return error code
        if (isInit) return -1;

        // TODO add per call error handling and return appropriate error codes
        
        initWifi(wifiChannel);
        initESPnow();
        bindCallbacks();
        
        isInit = true;

        configurePeer(peerMac);
        Serial.println("RobustMsg initialized successfully");
        return 0;
    }

    static void setQoS(QoS qos) {
        RobustMsg::qos = qos;
    }

    // SEND ARQ

    /* Sends data to the configured peer implementing ARQ according to 
    the current QoS settings. */
    static int send(u8* data, unsigned int len) {
        if (!assertInitialized()) return -1; // not initialized
        
        sendMessage(peerMAC, data, len);
        
        // ARQ loop
        const auto startTime = millis();
        uint8 attempt = 0;
        while (attempt < qos.RETRY_MAX_AMOUNT) {

            // if send callaback ran
            if (sendResult.finished) {
                if (sendResult.sendStatus == 0) return 0; // on success
                
                // on failure, wait and retry
                Serial.println("Send failed, retrying...");
                Serial.print("Retry attempt #");
                Serial.println(attempt + 1);
                
                attempt++;
                delay(qos.RETRY_BASE_DELAY_MS);
                sendMessage(peerMAC, data, len);
            }

            uint32 elapsed = millis() - startTime; // assuming difference fits inside uint32
            if (elapsed > qos.RETRY_TIMEOUT) {
                Serial.println("ARQ timeout reached, aborting send");
                return -2; // timed out
            }
            // this delay is absolutely necessary to let the backround esp-now callback run. Removing it cause callback to fail
            delay(5); // TODO adjust this (can probably be lower)
        }
        return -3; // max retry attempts reached
    }

    // RECV

};