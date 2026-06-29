#include "robust_msg.h"


String mac_to_string(const uint8_t mac[6]) {
    char buf[18]; // "AA:BB:CC:DD:EE:FF" + null
    snprintf(buf, sizeof(buf),
             "%02X:%02X:%02X:%02X:%02X:%02X",
             mac[0], mac[1], mac[2], mac[3], mac[4], mac[5]);
    return String(buf);
}

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


#define SERIAL_DEBUG
#define SIMULATE_FAULT

#ifdef SIMULATE_FAULT
unsigned int _fault_prob_send = 20; // 20% by default
unsigned int _fault_prob_ack = 20; // 20% by default
#endif

void set_sim_loss_ack_p(int p) {
    #ifdef SIMULATE_FAULT
    _fault_prob_ack = p;
    #endif
}

void set_sim_loss_send_p(int p) {
    #ifdef SIMULATE_FAULT
    _fault_prob_send = p;
    #endif
}



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
    // simulate ACK loss by randomly setting sendStatus to non-zero
    if ((os_random() % 100 < _fault_prob_ack) && sendStatus == 0) {
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

    bool is_duplicate = hdr.nonce == latestPacketNonce;

    // print python readable condensed log
    log_ui("RECV", millis(), mac_to_string(mac_addr), len, hdr.nonce, hdr.packetId, is_duplicate);

    // assert is not duplicate
    if (is_duplicate) {
        Serial.println("Duplicate packet received, ignoring...");
        return;
    }
    latestPacketNonce = hdr.nonce;

    uint8* payloadData = incomingData + sizeof(Header);
    const uint8 payloadLen = len - sizeof(Header);

    // if interanlly marked as consumed, user provided recv handler is not called
    bool consume = processInternalPackets(hdr, mac_addr, payloadData, payloadLen);
    if (consume) return;

    // if user callback is set, call it with the payload (data after header)
    if (userRecvCallback != nullptr) {
        userRecvCallback(mac_addr, hdr.packetId, payloadData, payloadLen);
    }

}

/* All internal diagnostics / commands are processed here. They are not seen by user if function returns true (mark packet as consumed). 
*/
bool RobustMsg::processInternalPackets(const Header& hdr, uint8 *mac_addr, uint8 *incomingData, uint8 len) {
    
    #define EXPECTED_HOP_PACKET_LEN sizeof(uint8)
    
    // reserved packetId 255 for hop RQST command
    Serial.println(len);
    if (hdr.packetId == 255 && len == EXPECTED_HOP_PACKET_LEN) {
        uint8 newChannel = incomingData[0];
        Serial.print("Hopping wifi to new channel: ");
        Serial.println(newChannel);

        // Queue the channel change to be executed in main loop (safer than doing it here)
        pendingChannel = newChannel;
        pendingChannelChange = true;
        return true;
    }
    // reserved packetID 254 for hop ACK
    if (hdr.packetId == 254 && len == EXPECTED_HOP_PACKET_LEN) {
        uint8 newChannel = incomingData[0];
        Serial.print("Got hop ACK for channel: ");
        Serial.println(newChannel);
        chHopAck = newChannel; // set ack to be read by hopChannel method
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
    bindCallbacks();

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

    // simulate PACKET loss (dont send anything)
    #ifdef SIMULATE_FAULT
        if (os_random() % 100 < _fault_prob_send) {
            Serial.println("Simulating send packet loss...");
            onDataSent(da, 1); // we directly call the send callback with negative status, we dont actually send anything
            return 0;            
        } else {
            return esp_now_send(da, outboundData, sizeof(outboundData));
        }
    #else
        return esp_now_send(da, outboundData, sizeof(outboundData));
    #endif
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
    esp_now_del_peer(peerMAC); // remove current peer, if valid
    memcpy(peerMAC, macAddr, sizeof(peerMAC));
    return (esp_now_add_peer(peerMAC, ESP_NOW_ROLE_COMBO, 0, NULL, 0) == 0) ? ErrorCode::OK : ErrorCode::INTERNAL_ERROR; // TODO return more specific error code
}

/* Initialize wifi and espnow.*/
ErrorCode RobustMsg::initialize(uint8 wifiChannel, uint8* peerMac) {
    // if already initialized, error
    if (isInit) return ErrorCode::NOT_INITIALIZED;

    // TODO add per call error handling and return appropriate error codes
    
    initWifi(wifiChannel);
    initESPnow();
    
    isInit = true;

    ErrorCode result = configurePeer(peerMac);
    if (result != ErrorCode::OK) {
        isInit = false;
        return result;
    }
    Serial.println("RobustMsg initialized successfully");
    return ErrorCode::OK;
}

void RobustMsg::setProtocolParams(RobustMsg::ProtocolParams params) {
    RobustMsg::params = params;
}

// SEND ARQ

/* Sends data to the configured peer implementing ARQ according to 
the current ProtocolParams settings. */
ErrorCode RobustMsg::send(u8* data, unsigned int len, u8 packId) {
    if (!assertInitialized()) return ErrorCode::NOT_INITIALIZED;
    
    uint32 nonce = os_random(); // generate random nonce for this message
    Serial.print("Generated nonce: ");
    Serial.println(nonce);

    sendMessage(peerMAC, data, len, nonce, packId);
    
    // ARQ loop
    const auto startTime = millis();
    uint8 attempt = 0;
    while (attempt < params.RETRY_MAX_AMOUNT) {

        // if send callaback ran
        if (sendResult.finished) {
            log_ui("SEND", millis(), mac_to_string(peerMAC), sendResult.sendStatus, len, nonce, packId, attempt, "running");

            if (sendResult.sendStatus == 0) return ErrorCode::OK; // on success
            
            // on failure, wait and retry
            Serial.println("Send failed, retrying...");
            Serial.print("Retry attempt #");
            Serial.println(attempt + 1);
            
            attempt++;
            delay(params.RETRY_BASE_DELAY_MS);
            sendMessage(peerMAC, data, len, nonce, packId);
        }

        uint32 elapsed = millis() - startTime; // assuming difference fits inside uint32
        if (elapsed > params.SEND_TIMEOUT_MS) {
            log_ui("SEND", millis(), mac_to_string(peerMAC), 1, len, nonce, packId, attempt, "timeout");
            Serial.println("ARQ timeout reached, aborting send");
            return ErrorCode::TIMEOUT; // timed out
        }
        // this delay is absolutely necessary to let the backround esp-now callback run. Removing it cause callback to fail
        delay(5); // TODO adjust this (can probably be lower)
    }
    log_ui("SEND", millis(), mac_to_string(peerMAC), sendResult.sendStatus, len, nonce, packId, attempt, "maxretries");
    return ErrorCode::MAX_RETRIES_EXCEEDED; // max retry attempts reached
}


ErrorCode RobustMsg::hopChannel(uint8 newChannel) {
        
    chHopAck = 0; // reset ack before sending command

    log_ui("HOP", "INIT", newChannel);
    
    // send channel change command to peer, reserved packetId 255 for channel change commands
    ErrorCode result = send((u8*)&newChannel, sizeof(newChannel), PACKID_HOP_RQST); 
    if (result != ErrorCode::OK) {
        log_ui("HOP", "INITERR", result);
        Serial.print("Failed to send channel hop command, error code: ");
        Serial.println((uint8)result);
        return result;
    }
    
    // in this loop we are expecting the peer to send back the desired new channel as an ack
    auto startTime = millis();
    while (millis() - startTime < params.CHANNEL_HOP_TIMEOUT_MS) {
        delay(10);
        // chHopAck is set from the receive callback
        if (chHopAck == 0) continue;

        if (chHopAck != newChannel) return ErrorCode::CHANNEL_HOP_INVALID_ACK; // received ack but for wrong channel, possibly desynchronized state between peers

        Serial.println("Received channel hop ack from peer, switching channel");
        log_ui("HOP", "GOTACK", newChannel);
        wifi_set_channel(newChannel);
        delay(1000); // wait a bit for channel switch to stabilize
        log_ui("HOP", "CHANNEL", WiFi.channel());
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

        log_ui("HOP", "GOTRQST", pendingChannel);

        // send ack back to peer
        ErrorCode result = send((u8*)&pendingChannel, sizeof(pendingChannel), PACKID_HOP_ACK);
        if (result != ErrorCode::OK) {
            Serial.print("Failed to send channel hop ack, error code: ");
            log_ui("HOP", "ACKRFAIL", pendingChannel);
            Serial.println((uint8)result);
        } else {
            Serial.println("Channel hop ack sent successfully");
            delay(100); 
            wifi_set_channel(pendingChannel);
            delay(1000);
        }

        int ch = WiFi.channel();
        Serial.print("Current channel: ");
        Serial.println(ch);
        log_ui("HOP", "CHANNEL", ch);
    }
}

/* Tunes this board's wifi radio to new channel. Unlike 'hopChannel', this does not perform a syncronized Hop. */
inline bool RobustMsg::setWifiChannel(uint8 newChannel) {
    return wifi_set_channel(newChannel);
}