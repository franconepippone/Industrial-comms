
### 1. ARQ Send Flow

```mermaid
flowchart TD

    A[send data] --> B[Generate random nonce]
    B --> C[sendMessage]
    C --> D[esp_now_send]

    D --> E{Send callback fired?}

    E -- No --> F[Wait 5 ms]
    F --> G{Timeout exceeded?}
    G -- No --> E
    G -- Yes --> H[Return TIMEOUT]

    E -- Yes --> I{sendStatus == 0 ?}

    I -- Yes --> J[Return OK]

    I -- No --> K[Increment retry counter]
    K --> L{Retries exhausted?}

    L -- Yes --> M[Return MAX_RETRIES_EXCEEDED]

    L -- No --> N[Delay RETRY_BASE_DELAY_MS]
    N --> C
```

---

### 2. Receive Packet Flow

```mermaid
flowchart TD

    A[ESP-NOW packet arrives]
    --> B[onDataReceived]

    B --> C{Length >= Header size?}

    C -- No --> D[Discard packet]
    C -- Yes --> E[Parse Header]

    E --> F{Duplicate nonce?}

    F -- Yes --> G[Ignore packet]
    F -- No --> H[Update latestPacketNonce]

    H --> I[Extract payload]

    I --> J[processInternalPackets]

    J --> K{Consumed internally?}

    K -- Yes --> L[Return]

    K -- No --> M{User callback set?}

    M -- No --> N[Return]

    M -- Yes --> O[Call userRecvCallback]
```

---

### 3. Channel Hop Initiator

Called by `hopChannel(newChannel)`.

```mermaid
sequenceDiagram

    participant A as Board A
    participant B as Board B

    A->>B: HOP_RQST(packetId=255,newChannel)

    B->>B: Queue channel change
    B->>A: HOP_ACK(packetId=254,newChannel)

    A->>A: Wait for ACK

    alt Correct ACK 
        A->>A: wifi_set_channel(newChannel)
        A-->>A: Return OK
    else Wrong ACK
        A-->>A: CHANNEL_HOP_INVALID_ACK
    else Timeout
        A-->>A: TIMEOUT
    end
```

---

### 4. Receiver Side Channel Hop Processing

This happens after receiving a hop request.

```mermaid
flowchart TD

    A[Receive packetId 255]
    --> B[Read requested channel]

    B --> C[Set pendingChannel]
    C --> D[pendingChannelChange = true]

    D --> E[Return from callback]

    E --> F[Main loop calls processPendingOperations]

    F --> G{pendingChannelChange?}

    G -- No --> H[Exit]

    G -- Yes --> I[Send HOP_ACK]

    I --> J{ACK sent successfully?}

    J -- No --> K[Report error]

    J -- Yes --> L[Delay 100 ms]

    L --> M[wifi_set_channel pendingChannel]

    M --> N[Delay 1000 ms]

    N --> O[Done]
```