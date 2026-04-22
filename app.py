import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
from streamlit_lightweight_charts import render_lightweight_chart

st.set_page_config(layout="wide", page_title="Quant Scalp Lab")

# --- CUSTOM CSS FOR MOBILE ---
st.markdown("""
    <style>
    .stNumberInput input { font-size: 18px !important; }
    .stButton button { width: 100%; height: 50px; font-weight: bold; }
    </style>
""", unsafe_allow_html=True)

# --- DATA HANDLING ---
if 'results' not in st.session_state: st.session_state.results = []
if 'df' not in st.session_state: st.session_state.df = None

st.sidebar.title("📁 Data Source")
source = st.sidebar.radio("Source", ["yfinance", "CSV Upload"])

if source == "yfinance":
    t_input = st.sidebar.text_input("Ticker", "EURUSD=X")
    interval = st.sidebar.selectbox("TF", ["1m", "5m", "15m", "1h"], index=2)
    if st.sidebar.button("Pull Data"):
        data = yf.download(t_input, period="60d", interval=interval, auto_adjust=True)
        if isinstance(data.columns, pd.MultiIndex): data.columns = data.columns.get_level_values(0)
        st.session_state.df = data.reset_index()

else:
    file = st.sidebar.file_uploader("Upload CSV", type="csv")
    if file:
        st.session_state.df = pd.read_csv(file, parse_dates=True).reset_index()

# --- THE LAB ---
if st.session_state.df is not None:
    df = st.session_state.df.copy()
    
    # 1. Format for Lightweight Charts
    # TV requires 'time' as a timestamp or string
    chart_data = df.rename(columns={'Date': 'time', 'Datetime': 'time', 
                                    'Open': 'open', 'High': 'high', 
                                    'Low': 'low', 'Close': 'close'})
    chart_data['time'] = chart_data['time'].dt.strftime('%Y-%m-%d %H:%M:%S')
    candles = chart_data[['time', 'open', 'high', 'low', 'close']].to_dict('records')

    # 2. Render Chart
    st.subheader("📊 Range Identification")
    render_lightweight_chart(candles, {
        "layout": {"background": {"color": "#131722"}, "textColor": "#d1d4dc"},
        "grid": {"vertLines": {"color": "#242733"}, "horzLines": {"color": "#242733"}},
        "crosshair": {"mode": 0},
        "priceScale": {"borderColor": "#485c7b"},
        "timeScale": {"borderColor": "#485c7b", "timeVisible": True, "secondsVisible": False}
    })

    # 3. Range Inputs (Index based for mobile speed)
    st.divider()
    col_in1, col_in2 = st.columns(2)
    with col_in1:
        s_idx = st.number_input("Range START Index", 0, len(df)-1, value=len(df)-30)
    with col_in2:
        e_idx = st.number_input("Range END Index", 0, len(df)-1, value=len(df)-5)

    if st.button("🔥 VALIDATE BREAKOUT"):
        # MATH ENGINE
        # Calculate ATR(14)
        df['tr'] = np.maximum(df['High'] - df['Low'], 
                   np.maximum(abs(df['High'] - df['Close'].shift(1)), 
                   abs(df['Low'] - df['Close'].shift(1))))
        df['atr'] = df['tr'].rolling(14).mean()
        
        # Slice the range
        r_slice = df.iloc[s_idx:e_idx+1]
        r_high = r_slice['High'].max()
        r_low = r_slice['Low'].min()
        r_mid = (r_high + r_low) / 2
        
        # Breakout Candle (The one immediately after your range end)
        if e_idx + 1 < len(df):
            bo_candle = df.iloc[e_idx + 1]
            atr_at_end = df.iloc[e_idx]['atr']
            
            # SMS Logic
            sms = abs(bo_candle['Close'] - r_mid) / atr_at_end
            
            # ICR Logic
            icr = (bo_candle['Close'] - df.iloc[e_idx]['Close']) / (r_high - r_low)
            
            status = "VALID ✅" if sms > 1.1 else "INVALID ❌"
            
            # Display Metrics
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Range Height", f"{(r_high-r_low):.5f}")
            m2.metric("SMS", round(sms, 2))
            m3.metric("ICR", round(icr, 2))
            m4.subheader(status)
            
            # Save Result
            st.session_state.results.append({
                "Time": bo_candle.get('Datetime', bo_candle.get('Date')),
                "SMS": round(sms, 2), "ICR": round(icr, 2), "Status": status
            })
        else:
            st.warning("Not enough data after the range to calculate breakout.")

    # 4. Results Table & Export
    if st.session_state.results:
        st.divider()
        st.subheader("📝 Collected Dataset")
        res_df = pd.DataFrame(st.session_state.results)
        st.dataframe(res_df, use_container_width=True)
        
        col_ex1, col_ex2 = st.columns(2)
        with col_ex1:
            csv = res_df.to_csv(index=False).encode('utf-8')
            st.download_button("📥 Download Results CSV", data=csv, file_name="quant_dataset.csv")
        with col_ex2:
            if st.button("🗑️ CLEAR DATASET"):
                st.session_state.results = []
                st.rerun()
