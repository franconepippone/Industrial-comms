#include <Arduino.h>

#include <ESP8266WiFi.h>
extern "C" {
  #include <espnow.h>
}
extern "C" {
    #include "osapi.h"
}


// Use this function to log to the ui (python backed readable)

#define BEGIN_SEQ_INDICATOR "&&&"
#define SEPARATOR "::"

// One or more arguments
#include <type_traits>

template<typename T, typename... Rest>
void log_ui_print(const T& value, const Rest&... rest) {
    if constexpr (std::is_enum_v<T>) {
        Serial.print(static_cast<std::underlying_type_t<T>>(value));
    } else {
        Serial.print(value);
    }

    if constexpr (sizeof...(Rest) > 0) {
        Serial.print(SEPARATOR);
        log_ui_print(rest...);
    }
}

// Public API
template<typename... Args>
void log_ui(const Args&... args) {
    Serial.print(BEGIN_SEQ_INDICATOR);
    log_ui_print(args...);
    Serial.println();
}

#define PACKID_HOP_RQST 255
#define PACKID_HOP_ACK 254

enum class ErrorCode : uint8 {
    OK = 0,
    TIMEOUT,
    NOT_INITIALIZED,
    MAX_RETRIES_EXCEEDED,
    INTERNAL_ERROR,
    CHANNEL_HOP_INVALID_ACK
};

// internal usage only
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

// user recv callback type definition
typedef void (*robust_msg_recv_callback)(u8 *mac_addr, u8 packet_id, u8 *data, u8 len);


class RobustMsg {
public:
    // Inner struct definition for ProtocolParams settings. Makes it accesible through RobustMsg namespace

    struct ProtocolParams {
        uint8 RETRY_MAX_AMOUNT;
        uint32 RETRY_BASE_DELAY_MS; // TODO make this full integer arithmetic
        //float RETRY_GROWTH; exponential backoff?
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
    
    inline static ProtocolParams params = {
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

    static inline void bindRecvCallback(robust_msg_recv_callback callback);
    static void printLocalMAC();
    /* Sets the given mac address as the current peer. */
    static ErrorCode configurePeer(uint8* macAddr);
    /* Initialize wifi and espnow.*/
    static ErrorCode initialize(uint8 wifiChannel, uint8* peerMac);
    static void setProtocolParams(ProtocolParams params);

    /* Sends data to the configured peer implementing ARQ according to 
    the current ProtocolParams settings. */
    static ErrorCode send(u8* data, unsigned int len, u8 packId = 0);
    
    /* Processes pending operations queued by callbacks.
    Call this in your main loop to safely handle deferred operations. */
    static void processPendingOperations();

    /* Attempts syncronized hopping to a new Wifi channel. */
    static ErrorCode hopChannel(uint8 newChannel);

    static inline bool setWifiChannel(uint8 newChannel);

};