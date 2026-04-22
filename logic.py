import numpy as np

def calculate_metrics(p, p_prev, r_high, r_low, atr, eurx_mom, usdx_mom, weights, threshold):
    # 1. SMS: Structure Momentum Score
    range_mid = (r_high + r_low) / 2
    sms = abs(p - range_mid) / atr if atr > 0 else 0
    
    # 2. ICR: Impulse-Correction Ratio
    range_height = r_high - r_low
    icr = (p - p_prev) / range_height if range_height > 0 else 0
    
    # 3. BVS: Breakout Validity Score
    # We weigh the SMS and the Index Divergence
    # EURX positive/USDX negative is bullish for EURUSD
    index_score = (eurx_mom * 100) + (usdx_mom * -100) 
    bvs = (sms * weights['sms']) + (index_score * weights['index'])
    
    is_valid = bvs >= threshold
    
    return {
        "SMS": round(sms, 2),
        "ICR": round(icr, 2),
        "BVS": round(bvs, 2),
        "Status": "VALID ✅" if is_valid else "INVALID ❌"
  }
