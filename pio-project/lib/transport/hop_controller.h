#pragma once
#include <Arduino.h>
#include "robust_msg.h"

struct Channel {
    float R = .5;
    unsigned long timeout = 0;
};

typedef uint8 espWifiChannel;

class HopController {
    Channel chs[14];
    uint8 current_ch;

    // used for calculating TXS, TXF
    uint64_t last_tx_succ = 0;
    uint64_t last_tx_fail = 0;
    unsigned long last_time = 0;
    unsigned long next_hop_min_time = 0;

public:
    struct {
        unsigned long hop_cooldown_ms; // minimum time between hops
        unsigned long channel_cooldown_ms; // cooldown for a channel that was left 
        uint8 ch_proximity_range; // max distance of channels considered *near* current channel
        float ch_proximity_penalty; // multiplier for reputation of channels *near* current channels
        float d_treeshold;
        float k_d; // deg-est filter constant
        float k_s; // reputation succ gain
        float k_f; // reputation fail gain
    } params;

private:
    //
    float D = 0.0; // degradation estimate for the current channel

    void updateVariables(float dt_ms) {
        auto TXS = RobustMsg::TX_succ_cnt - last_tx_succ; 
        auto TXF = RobustMsg::TX_fail_cnt - last_tx_fail;
        auto TXtot = TXS + TXF;
        
        Serial.println(TXS);
        // dont update if no other packets are received
        if (TXtot == 0) return;

        // update local counters
        last_tx_succ = RobustMsg::TX_succ_cnt;
        last_tx_fail = RobustMsg::TX_fail_cnt;

        // update degradation estimate
        float d_inst = (float)TXF / (float)(TXtot);
        D += params.k_d * (d_inst - D);
        
        float R = chs[current_ch].R; 
        // compute new r caused by both updates in parallel
        float r_succ = 1.0 - (1.0 - R)*pow((1.0-params.k_s), TXS);
        float r_fail = R * pow((1.0-params.k_f), TXF);
        // add the effect of deltas
        R += (r_succ - R) + (r_fail - R);   

        // clamping
        chs[current_ch].R = constrain(R, 0.0, 1.0);
        D = constrain(D, 0.0, 1.0);
    }

    /* returns the channel that has the best overall reputation at this moment,
    also considering distance penalty and cooldown timeout*/
    espWifiChannel get_best_channel() {
        uint8 best_ch = 0;
        float best_rep = -INFINITY;

        auto now = millis();

        for (uint8 i = 0; i < 14; i++) {
            if (i == current_ch) continue; // if it's the current channel, ignore
            if (now < chs[i].timeout) continue; // ignore channels in cooldown

            float rep = chs[i].R;
            
            // apply penalty to nearby channels
            if (abs(current_ch - i) <= params.ch_proximity_range) rep *= params.ch_proximity_penalty;

            if (rep > best_rep) {
                best_rep = rep;
                best_ch = i;
            } 
        }

        return to_esp_channel(best_ch);
    }

    // channels are numbered 1-14 in espressif framework, but 0-13 in this class
    inline uint8 from_esp_channel(espWifiChannel ch_wifi) {return ch_wifi - 1;}
    inline espWifiChannel to_esp_channel(uint8 ch_idx) {return ch_idx + 1;}
    inline void update_current_channel() {current_ch = from_esp_channel(WiFi.channel());}

public:
    HopController() {
        update_current_channel();
        params = {
            .hop_cooldown_ms = 5000,
            .channel_cooldown_ms = 10000,
            .ch_proximity_range = 2,
            .ch_proximity_penalty = 0.5,
            .d_treeshold = .7,
            .k_d = 0,
            .k_s = 0,
            .k_f = 0
        };
    }

    void logAllReps() {
        for (int i = 0; i < 14; i++) 
            log_ui("HOPCTRL", millis(), to_esp_channel(i), D, chs[i].R);
    }

    void setReputations(const float (&reps)[14]) {
        for (int i = 0; i < 14; i++) {
            chs[i].R = reps[i];
        }
    }

        
    /* If manual change of channel is needed, call this (do
    not call RobustMsg::hopChannel directly)*/
    ErrorCode forceHop(espWifiChannel ch) {
        uint8 old_channel = current_ch;
        auto code = RobustMsg::hopChannel(ch);
        update_current_channel();

        if (code == ErrorCode::OK) {
            D = 0;
            chs[old_channel].timeout = millis() + params.channel_cooldown_ms;
        }
        return code;
    }

    void process(unsigned long period_ms) {
        // bound execution frequency
        auto dt = millis() - last_time;
        if (dt < period_ms) return;
        last_time = millis();

        updateVariables(float(dt));
        log_ui("HOPCTRL", millis(), to_esp_channel(current_ch), D, chs[current_ch].R);
        
        // trigger hop
        if (D > params.d_treeshold && (millis() > next_hop_min_time)) {
            next_hop_min_time = millis() + params.hop_cooldown_ms;
            log_ui("HOPCTRLT_TRIGGER", next_hop_min_time, millis());
            espWifiChannel best_ch = get_best_channel();
            forceHop(best_ch);
        }
    }
    

};