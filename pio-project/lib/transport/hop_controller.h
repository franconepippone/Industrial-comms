#pragma once
#include <Arduino.h>
#include "robust_msg.h"

struct Channel {
    float R = .5;
    unsigned long timeout = 0;
};


class HopController {
    Channel chs[14];
    uint8 current_ch;

    // used for calculating TXS, TXF
    uint64_t last_tx_succ = 0;
    uint64_t last_tx_fail = 0;
    unsigned long last_time = millis();
public:
    struct {
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
        chs[current_ch].R += (r_succ - R) + (r_fail - R);   
    }

public:
    HopController() {
        current_ch = WiFi.channel();
        params = {
            .d_treeshold = .8,
            .k_d = 0,
            .k_s = 0,
            .k_f = 0
        };
    }

    void process(unsigned long period_ms) {
        // bound execution frequency
        auto dt = millis() - last_time;
        if (dt < period_ms) return;
        last_time = millis();

        updateVariables(float(dt));
        log_ui("HOPCTRL", millis(), current_ch, D, chs[current_ch].R);

        if (D > params.d_treeshold) {}




    }
    

};