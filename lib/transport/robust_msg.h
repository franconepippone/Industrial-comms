#include <Arduino.h>

#include <ESP8266WiFi.h>
extern "C" {
  #include <espnow.h>
}
extern "C" {
    #include "osapi.h"
}

#define SERIAL_DEBUG

enum class ErrorCode : uint8 {
    OK = 0,
    TIMEOUT,
    NOT_INITIALIZED,
    MAX_RETRIES_EXCEEDED,
    INTERNAL_ERROR,
    CHANNEL_HOP_INVALID_ACK
};

struct SendResult {
    bool finished;
    uint8 macAddr[6];
    uint8 sendStatus;
};

// prependend to each message, used for duplicate detection and possibly other features in the future
struct __attribute__((packed)) Header {
    uint32 nonce;
    uint8 packetId;
};

typedef void (*robust_msg_recv_callback)(u8 *mac_addr, u8 packet_id, u8 *data, u8 len);


class RobustMsg {
public:
    // Inner struct definition for QoS settings for user usage

    struct QoS {
        uint8 RETRY_MAX_AMOUNT;
        uint32 RETRY_BASE_DELAY_MS; // TODO make this full integer arithmetic
        //float RETRY_GROWTH;
        uint32 SEND_TIMEOUT_MS;
        uint32 CHANNEL_HOP_TIMEOUT_MS;
    };

private:
    inline static uint8 peerMAC[6] = {0};
    inline static bool isInit = false;
    inline static robust_msg_recv_callback userRecvCallback = nullptr;
    inline static uint32 latestPacketNonce = 0; // for duplicate detection
    inline static uint8 chHopAck = 0;
    
    // Deferred operation flags (set by callbacks, executed in main loop)
    inline static volatile bool pendingChannelChange = false;
    inline static volatile uint8 pendingChannel = 0;
    
    inline static QoS qos = {
        .RETRY_MAX_AMOUNT = 10,
        .RETRY_BASE_DELAY_MS = 100,
        .SEND_TIMEOUT_MS = 1000,
        .CHANNEL_HOP_TIMEOUT_MS = 2000
    };
    inline static SendResult sendResult = {
        .finished = false,
        .macAddr = {0},
        .sendStatus = 0
    };

    // espnow callbacks
    static void onDataSent(uint8 *mac_addr, uint8 sendStatus);
    static void onDataReceived(uint8 *mac_addr, uint8 *incomingData, uint8 len);

    // handles packets for internal communication (e.g. channel hopping commands)
    static bool processInternalPackets(const Header& hdr, uint8 *mac_addr, uint8 *incomingData, uint8 len);
    
    // utility
    static void initWifi(uint8 channel);
    static auto initESPnow();
    static void bindCallbacks();
    inline static bool assertInitialized();

    // Wrapper around esp_now_send. Prepends header to message and resets ARQ internal state flags.
    inline static auto sendMessage(u8* da, u8* data, unsigned int len, uint32 nonce, u8 packId);
    
public:

    // UTILITY

    static inline void bindRecvCallback(robust_msg_recv_callback callback);
    static void printLocalMAC();
    /* Sets the given mac address as the current peer. */
    static ErrorCode configurePeer(uint8* macAddr);
    /* Initialize wifi and espnow.*/
    static ErrorCode initialize(uint8 wifiChannel, uint8* peerMac);
    static void setQoS(QoS qos);

    /* Sends data to the configured peer implementing ARQ according to 
    the current QoS settings. */
    static ErrorCode send(u8* data, unsigned int len, u8 packId = 0);
    
    /* Processes pending operations queued by callbacks.
    Call this in your main loop to safely handle deferred operations. */
    static void processPendingOperations();

    // wifi channel hopping
    static ErrorCode hopChannel(uint8 newChannel);

};