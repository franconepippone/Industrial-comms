#include <Arduino.h>

#include <ESP8266WiFi.h>
extern "C" {
  #include <espnow.h>
}
extern "C" {
    #include "osapi.h"
}

#define SERIAL_DEBUG


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
    inline static robust_msg_recv_callback userRecvCallback = nullptr;
    inline static uint32_t latestPacketNonce = 0; // for duplicate detection
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

    // espnow callbacks
    
    static void onDataSent(uint8_t *mac_addr, uint8_t sendStatus);
    static void onDataReceived(uint8_t *mac_addr, uint8_t *incomingData, uint8_t len);
    
    // utility
    static void initWifi(uint8 channel);
    static auto initESPnow();
    static void bindCallbacks();
    inline static bool assertInitialized();

    // Wrapper around esp_now_send. Prepends header to message and resets ARQ internal state flags.
    inline static auto sendMessage(u8* da, u8* data, unsigned int len);
    
public:

    // UTILITY

    static inline void bindRecvCallback(robust_msg_recv_callback callback);
    static void printLocalMAC();
    /* Sets the given mac address as the current peer. */
    static int configurePeer(uint8* macAddr);
    /* Initialize wifi and espnow.*/
    static int initialize(uint8 wifiChannel, uint8* peerMac);
    static void setQoS(QoS qos);

    /* Sends data to the configured peer implementing ARQ according to 
    the current QoS settings. */
    static int send(u8* data, unsigned int len);

};