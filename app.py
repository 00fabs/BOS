import streamlit as st
from logic import calculate_metrics

st.set_page_config(page_title="Quant Breakout Verifier", layout="wide")

# Initialize Session State for Clearing
if 'data_count' not in st.session_state:
    st.session_state.data_count = 0

st.title("⚡ Quant Breakout Dashboard")

# --- SIDEBAR: TWEAK PARAMETERS ---
st.sidebar.header("Model Parameters")
sms_weight = st.sidebar.slider("SMS Weight", 0.0, 1.0, 0.4)
idx_weight = st.sidebar.slider("Index Weight", 0.0, 1.0, 0.6)
valid_threshold = st.sidebar.number_input("Validation Threshold", value=1.0, step=0.1)

# --- MAIN INPUTS ---
col1, col2, col3 = st.columns(3)

with col1:
    st.subheader("Price Data")
    price = st.number_input("Current Price", format="%.5f")
    prev_price = st.number_input("Previous Price", format="%.5f")
    atr = st.number_input("ATR (14)", format="%.5f")

with col2:
    st.subheader("Structure")
    r_high = st.number_input("Range High", format="%.5f")
    r_low = st.number_input("Range Low", format="%.5f")

with col3:
    st.subheader("Macro (15m Momentum)")
    eurx_mom = st.number_input("EURX Momentum", format="%.4f")
    usdx_mom = st.number_input("USDX Momentum", format="%.4f")

# --- EXECUTION ---
if st.button("VERIFY BREAKOUT"):
    weights = {"sms": sms_weight, "index": idx_weight}
    results = calculate_metrics(price, prev_price, r_high, r_low, atr, eurx_mom, usdx_mom, weights, valid_threshold)
    
    st.divider()
    res_col1, res_col2, res_col3, res_col4 = st.columns(4)
    res_col1.metric("SMS", results["SMS"])
    res_col2.metric("ICR", results["ICR"])
    res_col3.metric("BVS", results["BVS"])
    res_col4.subheader(results["Status"])

# --- RESET BUTTON ---
if st.button("RESET DATA"):
    st.rerun()
