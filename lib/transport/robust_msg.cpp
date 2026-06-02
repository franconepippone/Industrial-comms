#include "robust_msg.h"


void debugOnReceived(uint8 *mac_addr, uint8 *incomingData, uint8 len) {
    Serial.println();
    Serial.println("===== RECEIVE CALLBACK =====");
  
    Header& hdr = *reinterpret_cast<Header*>(incomingData);
  
    char macStr[18];
    snprintf(macStr, sizeof(macStr),
             "%02X:%02X:%02X:%02X:%02X:%02X",
             mac_addr[0], mac_addr[1], mac_addr[2],
             mac_addr[3], mac_addr[4], mac_addr[5]);
  
    Serial.print("Sender MAC: ");
    Serial.println(macStr);
  
    Serial.print("Payload size: ");
    Serial.println(len);
  
    Serial.print("Nonce: ");
    Serial.println(hdr.nonce);
  
    Serial.print("Packet ID: ");
    Serial.println(hdr.packetId);
    
    Serial.println("============================");
}
  
void debugOnSent(uint8 *mac_addr, uint8 sendStatus) {
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



//#define SIMULATE_FAULT 



// ==============================
// RobustMsg class implementation
// ==============================
 
// esp-now callbacks

void RobustMsg::onDataSent(uint8 *mac_addr, uint8 sendStatus) {
    #ifdef SERIAL_DEBUG
    debugOnSent(mac_addr, sendStatus); 
    #endif
    
    // store result so that it can be retrieved by the main loop
    memcpy(sendResult.macAddr, mac_addr, sizeof(sendResult.macAddr));
    sendResult.sendStatus = sendStatus;

    #ifdef SIMULATE_FAULT
    // simulate 20% send failure by randomly setting sendStatus to non-zero
    if (os_random() % 5 == 0) {
        Serial.println("Simulating send failure in callback...");
        sendResult.sendStatus = 1; // non-zero indicates failure
    }
    #endif

    sendResult.finished = true;
}

void RobustMsg::onDataReceived(uint8 *mac_addr, uint8 *incomingData, uint8 len) {
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

    // if marked as consumed, user provided recv handler is not called
    bool consume = processInternalPackets(hdr, mac_addr, incomingData, len);
    if (consume) return;

    // if user callback is set, call it with the payload (data after header)
    if (userRecvCallback != nullptr) {
        userRecvCallback(mac_addr, hdr.packetId, incomingData + sizeof(Header), len - sizeof(Header));
    }

}

/* All internal diagnostics / commands are processed here. They are not seen by user if function returns true (mark packet as consumed). 
*/
bool RobustMsg::processInternalPackets(const Header& hdr, uint8 *mac_addr, uint8 *incomingData, uint8 len) {
    // reserved packetId 255 for internal channel hop commands
    if (hdr.packetId == 255 && len == sizeof(Header) + sizeof(uint8)) {
        uint8 newChannel = incomingData[sizeof(Header)];
        Serial.print("Received channel hop command, new channel: ");
        Serial.println(newChannel);
        chHopAck = newChannel; // set ack to be read by hopChannel method

        // Queue the channel change to be executed in main loop (safer than doing it here)
        pendingChannel = newChannel;
        pendingChannelChange = true;
        return true;
    }

    return false; 
}


// UTILITY METHODS

void RobustMsg::initWifi(uint8 channel) {
    WiFi.mode(WIFI_STA);
    WiFi.disconnect();
    wifi_set_channel(channel);
    // TODO handle and return errors
}

auto RobustMsg::initESPnow() {
    int outcome = esp_now_init();
    if (outcome != 0) {
        Serial.println("ESP-NOW init failed");
        return outcome;
    }

    esp_now_set_self_role(ESP_NOW_ROLE_COMBO);

    Serial.println("ESP-NOW initialized");
    return 0; 
}

void RobustMsg::bindCallbacks() {
    esp_now_register_send_cb(RobustMsg::onDataSent);
    esp_now_register_recv_cb(RobustMsg::onDataReceived);
}

inline bool RobustMsg::assertInitialized() {
    if (isInit) return true;
    Serial.println("RobustMsg not initialized");
    return false;
}

inline void RobustMsg::bindRecvCallback(robust_msg_recv_callback callback) {
    userRecvCallback = callback;
}


/* Wrapper around esp_now_send. Prepends header to message and resets ARQ internal state flags.
*/
inline auto RobustMsg::sendMessage(u8* da, u8* data, unsigned int len, uint32 nonce, u8 packId) {
    sendResult.finished = false; // always reset this for ARQ
    
    u8 outboundData[len + sizeof(Header)]; // TODO is this dynamic allocation?

    // prepend header to data
    Header& hdr = *reinterpret_cast<Header*>(outboundData);
    hdr.nonce = nonce;
    hdr.packetId = packId;

    // copy payload after header
    memcpy(outboundData + sizeof(Header), data, len);

    #ifdef SIMULATE_FAULT
    if (os_random() % 5 == 0) { // simulate 20% packet loss
        Serial.println("Simulating send failure...");
        return -1; // non-zero return value indicates failure in esp_now_send
    }
    #endif

    return esp_now_send(da, outboundData, sizeof(outboundData));
}

// UTILITY

void RobustMsg::printLocalMAC() {
    Serial.print("Local MAC: ");
    Serial.println(WiFi.macAddress());
}

/* Sets the given mac address as the current peer. */
ErrorCode RobustMsg::configurePeer(uint8* macAddr) {
    if (!assertInitialized()) return ErrorCode::NOT_INITIALIZED;

    // TODO possibly validate peerMac here
    memcpy(peerMAC, macAddr, sizeof(peerMAC));
    esp_now_del_peer(peerMAC); // in case peer was already added, remove it first to avoid duplicates
    return esp_now_add_peer(peerMAC, ESP_NOW_ROLE_COMBO, 0, NULL, 0) ? ErrorCode::OK : ErrorCode::INTERNAL_ERROR; // TODO return more specific error code
}

/* Initialize wifi and espnow.*/
ErrorCode RobustMsg::initialize(uint8 wifiChannel, uint8* peerMac) {
    // if already initialized, return error code
    if (isInit) return ErrorCode::NOT_INITIALIZED;

    // TODO add per call error handling and return appropriate error codes
    
    initWifi(wifiChannel);
    initESPnow();
    bindCallbacks();
    
    isInit = true;

    ErrorCode result = configurePeer(peerMac);
    if (result != ErrorCode::OK) {
        return result;
    }
    Serial.println("RobustMsg initialized successfully");
    return ErrorCode::OK;
}

void RobustMsg::setQoS(RobustMsg::QoS qos) {
    RobustMsg::qos = qos;
}

// SEND ARQ

/* Sends data to the configured peer implementing ARQ according to 
the current QoS settings. */
ErrorCode RobustMsg::send(u8* data, unsigned int len, u8 packId) {
    if (!assertInitialized()) return ErrorCode::NOT_INITIALIZED;
    
    uint32 nonce = os_random(); // generate random nonce for this message
    Serial.print("Generated nonce: ");
    Serial.println(nonce);

    sendMessage(peerMAC, data, len, nonce, packId);
    
    // ARQ loop
    const auto startTime = millis();
    uint8 attempt = 0;
    while (attempt < qos.RETRY_MAX_AMOUNT) {

        // if send callaback ran
        if (sendResult.finished) {
            if (sendResult.sendStatus == 0) return ErrorCode::OK; // on success
            
            // on failure, wait and retry
            Serial.println("Send failed, retrying...");
            Serial.print("Retry attempt #");
            Serial.println(attempt + 1);
            
            attempt++;
            delay(qos.RETRY_BASE_DELAY_MS);
            sendMessage(peerMAC, data, len, nonce, packId);
        }

        uint32 elapsed = millis() - startTime; // assuming difference fits inside uint32
        if (elapsed > qos.SEND_TIMEOUT_MS) {
            Serial.println("ARQ timeout reached, aborting send");
            return ErrorCode::TIMEOUT; // timed out
        }
        // this delay is absolutely necessary to let the backround esp-now callback run. Removing it cause callback to fail
        delay(5); // TODO adjust this (can probably be lower)
    }
    return ErrorCode::MAX_RETRIES_EXCEEDED; // max retry attempts reached
}


ErrorCode RobustMsg::hopChannel(uint8 newChannel) {
        
    chHopAck = 0; // reset ack before sending command
   
    // send channel change command to peer, reserved packetId 255 for channel change commands
    ErrorCode result = send((u8*)&newChannel, sizeof(newChannel), 255); 
    if (result != ErrorCode::OK) {
        Serial.print("Failed to send channel hop command, error code: ");
        Serial.println((uint8)result);
        return result;
    }
    
    // in this loop we are expecting the peer to send back the desired new channel as an ack
    auto startTime = millis();
    while (millis() - startTime < qos.CHANNEL_HOP_TIMEOUT_MS) {
        delay(10);
        if (chHopAck == 0) continue;

        if (chHopAck != newChannel) return ErrorCode::CHANNEL_HOP_INVALID_ACK; // received ack but for wrong channel, possibly desynchronized state between peers

        Serial.println("Received channel hop ack from peer, switching channel");
        wifi_set_channel(newChannel);
        return ErrorCode::OK;
    }
    return ErrorCode::TIMEOUT;
}

/* Processes pending operations that were queued by callbacks.
Call this regularly in your main loop to safely execute deferred operations. */
void RobustMsg::processPendingOperations() {
    if (pendingChannelChange) {
        pendingChannelChange = false; // clear flag first
        Serial.print("Processing deferred channel change to: ");
        Serial.println(pendingChannel);

        // send ack back to peer
        ErrorCode result = send((u8*)&pendingChannel, sizeof(pendingChannel), 255);
        if (result != ErrorCode::OK) {
            Serial.print("Failed to send channel hop ack, error code: ");
            Serial.println((uint8)result);
        } else {
            Serial.println("Channel hop ack sent successfully");
            wifi_set_channel(pendingChannel);
            delay(1000);
        }

        int ch = WiFi.channel();
        Serial.print("Current channel: ");
        Serial.println(ch);
    }
}