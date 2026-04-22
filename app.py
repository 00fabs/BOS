import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
from streamlit_lightweight_charts import render_lightweight_chart

# --- PAGE CONFIG ---
st.set_page_config(layout="wide", page_title="Quant Scalp Lab v2")

# Consolidating Logic into App.py to prevent ImportErrors
def calculate_quant_metrics(df, s_idx, e_idx):
    """Calculates SMS and ICR based on the marked range."""
    # 1. Slice the range to find High/Low
    r_slice = df.iloc[s_idx:e_idx+1]
    r_high = r_slice['High'].max()
    r_low = r_slice['Low'].min()
    r_mid = (r_high + r_low) / 2
    r_height = r_high - r_low
    
    # 2. Calculate ATR(14) for the whole series
    # Using the standard True Range formula
    high_low = df['High'] - df['Low']
    high_cp = np.abs(df['High'] - df['Close'].shift(1))
    low_cp = np.abs(df['Low'] - df['Close'].shift(1))
    tr = np.maximum(high_low, np.maximum(high_cp, low_cp))
    df['atr_calc'] = tr.rolling(window=14).mean()
    
    # 3. Get values at the Breakout Point (End Index + 1)
    if e_idx + 1 >= len(df):
        return None, "Not enough data after range for breakout."
    
    atr_at_end = df.iloc[e_idx]['atr_calc']
    bo_candle = df.iloc[e_idx + 1]
    prev_close = df.iloc[e_idx]['Close']
    
    # SMS: (Breakout Close - Range Mid) / ATR
    sms = abs(bo_candle['Close'] - r_mid) / atr_at_end if atr_at_end > 0 else 0
    
    # ICR: (Breakout Close - Range Close) / Range Height
    icr = (bo_candle['Close'] - prev_close) / r_height if r_height > 0 else 0
    
    return {
        "time": bo_candle.get('Datetime', bo_candle.get('Date')),
        "sms": round(sms, 2),
        "icr": round(icr, 2),
        "r_high": r_high,
        "r_low": r_low,
        "atr": round(atr_at_end, 5)
    }, None

# --- UI STEPS ---
if 'results' not in st.session_state: st.session_state.results = []
if 'df' not in st.session_state: st.session_state.df = None

st.sidebar.title("🚀 Quant Researcher")
source = st.sidebar.radio("Data Source", ["yfinance", "CSV Upload"])

if source == "yfinance":
    ticker = st.sidebar.text_input("Ticker", "EURUSD=X")
    tf = st.sidebar.selectbox("Timeframe", ["1m", "5m", "15m", "1h"], index=2)
    if st.sidebar.button("Fetch Data"):
        data = yf.download(ticker, period="60d", interval=tf, auto_adjust=True)
        # Fix for yfinance MultiIndex
        if isinstance(data.columns, pd.MultiIndex):
            data.columns = data.columns.get_level_values(0)
        st.session_state.df = data.reset_index()

# --- MAIN APP INTERFACE ---
if st.session_state.df is not None:
    df = st.session_state.df.copy()
    
    # Format for Lightweight Charts (TradingView)
    chart_df = df.rename(columns={'Date': 'time', 'Datetime': 'time', 'Open': 'open', 'High': 'high', 'Low': 'low', 'Close': 'close'})
    chart_df['time'] = chart_df['time'].dt.strftime('%Y-%m-%d %H:%M:%S')
    candles = chart_df[['time', 'open', 'high', 'low', 'close']].to_dict('records')

    st.subheader(f"📊 {ticker if source=='yfinance' else 'Uploaded Data'}")
    
    # Render Snappy Chart
    render_lightweight_chart(candles, {
        "layout": {"background": {"color": "#0c0d10"}, "textColor": "#efefef"},
        "grid": {"vertLines": {"color": "#1e2026"}, "horzLines": {"color": "#1e2026"}},
        "timeScale": {"timeVisible": True, "secondsVisible": False}
    })

    st.markdown("---")
    
    # Range Selection
    col_a, col_b = st.columns(2)
    with col_a:
        start_idx = st.number_input("Range START Index", 0, len(df)-1, value=len(df)-25)
    with col_b:
        end_idx = st.number_input("Range END Index", 0, len(df)-1, value=len(df)-5)

    if st.button("🔍 VALIDATE BREAKOUT"):
        res, err = calculate_quant_metrics(df, start_idx, end_idx)
        
        if err:
            st.error(err)
        else:
            status = "VALID ✅" if res['sms'] > 1.1 else "INVALID ❌"
            
            # Display Results
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("ATR (at End)", res['atr'])
            m2.metric("SMS", res['sms'])
            m3.metric("ICR", res['icr'])
            m4.subheader(status)
            
            # Save to Session
            st.session_state.results.append({
                "Breakout_Time": res['time'],
                "SMS": res['sms'],
                "ICR": res['icr'],
                "Status": status
            })

    # Data Management
    if st.session_state.results:
        st.divider()
        results_df = pd.DataFrame(st.session_state.results)
        st.dataframe(results_df, use_container_width=True)
        
        c1, c2 = st.columns(2)
        with c1:
            csv_data = results_df.to_csv(index=False).encode('utf-8')
            st.download_button("📥 Export to CSV", csv_data, "breakout_labels.csv", "text/csv")
        with c2:
            if st.button("🗑️ RESET ALL"):
                st.session_state.results = []
                st.rerun()
