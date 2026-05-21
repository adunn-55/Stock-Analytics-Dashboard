import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
import pandas as pd
from datetime import datetime, timedelta

# --- Page Configuration ---
st.set_page_config(page_title="Stock Analytics Dashboard", layout="wide")
st.title("📈 Advanced Stock Analytics Platform")

# --- Initialize Session States for Change Tracking ---
if 'last_ticker' not in st.session_state:
    st.session_state['last_ticker'] = "AAPL"
if 'last_timeframe' not in st.session_state:
    st.session_state['last_timeframe'] = "1Y"
if 'last_multi_tickers' not in st.session_state:
    st.session_state['last_multi_tickers'] = "AAPL, NVDA, MSFT, SPY"
if 'data_dirty' not in st.session_state:
    st.session_state['data_dirty'] = False

# --- Sidebar Inputs ---
st.sidebar.header("Dashboard Settings")

# 1. Primary Ticker / Multi-Ticker Input Container (Always at the absolute top)
ticker_container = st.sidebar.container()

# 2. Action Trigger (Moved high-profile right beneath the ticker inputs)
run_analysis = st.sidebar.button("🔍 Fetch & Update Data", use_container_width=True)

st.sidebar.markdown("---")

# 3. Date Parameters (Manual Override)
st.sidebar.subheader("Custom Date Filter")
use_custom_dates = st.sidebar.checkbox("Use Custom Dates Instead", value=False)

end_date = datetime.today()
start_date_default = end_date - timedelta(days=365)
sidebar_start = st.sidebar.date_input("Start Date", value=start_date_default, disabled=not use_custom_dates)
sidebar_end = st.sidebar.date_input("End Date", value=end_date, disabled=not use_custom_dates)

st.sidebar.markdown("---")

# 4. Choose Mode (Instant UI Toggle)
app_mode = st.sidebar.radio("Select Dashboard Mode", ["Single Ticker Lookup", "Multi-Ticker Comparison"])

# --- Helper Functions with Native Adaptive Resolution ---
@st.cache_data(ttl=3600)
def load_single_data(symbol, start, end):
    stock_data = yf.download(symbol, start=start, end=end, interval="1d", group_by="ticker")
    info = yf.Ticker(symbol).info
    
    if isinstance(stock_data.columns, pd.MultiIndex):
        if symbol in stock_data.columns.get_level_values(0):
            df_cleaned = stock_data[symbol].copy()
        else:
            df_cleaned = stock_data.copy()
            if isinstance(df_cleaned.columns, pd.MultiIndex):
                df_cleaned.columns = df_cleaned.columns.get_level_values(0)
    else:
        df_cleaned = stock_data.copy()
        
    return df_cleaned, info

@st.cache_data(ttl=3600)
def load_multi_data(symbols, start, end):
    df_multi = yf.download(symbols, start=start, end=end)['Close']
    return pd.DataFrame(df_multi)

# =====================================================================
# MODE 1: SINGLE TICKER LOOKUP
# =====================================================================
if app_mode == "Single Ticker Lookup":
    ticker = ticker_container.text_input("Enter Stock Ticker", value=st.session_state['last_ticker']).upper()
    
    st.markdown("---")
    st.subheader("Interactive Price Chart")
    
    time_col1, time_col2 = st.columns([2, 3])
    with time_col1:
        chart_type = st.radio("Chart Type", ["Candlestick", "Line"], horizontal=True, label_visibility="collapsed")
        
    with time_col2:
        timeframe = st.segmented_control(
            "Timeframe",
            options=["1M", "YTD", "1Y", "5Y", "MAX"],
            default=st.session_state['last_timeframe'],
            label_visibility="collapsed"
        )

    # State Change Detection
    if ticker != st.session_state['last_ticker'] or timeframe != st.session_state['last_timeframe']:
        st.session_state['data_dirty'] = True

    # Calculate Timeframe
    now = datetime.today()
    if use_custom_dates:
        start_date = sidebar_start
        end_date_input = sidebar_end
    else:
        end_date_input = now
        if timeframe == "1M": start_date = now - timedelta(days=30)
        elif timeframe == "YTD": start_date = datetime(now.year, 1, 1)
        elif timeframe == "1Y": start_date = now - timedelta(days=365)
        elif timeframe == "5Y": start_date = now - timedelta(days=5*365)
        else: start_date = datetime(1970, 1, 1)

    # Process Data Loading
    if run_analysis or not st.session_state['data_dirty']:
        if run_analysis:
            st.session_state['last_ticker'] = ticker
            st.session_state['last_timeframe'] = timeframe
            st.session_state['data_dirty'] = False
            
        try:
            with st.spinner(f"Processing structural matrices for {ticker}..."):
                df, stock_info = load_single_data(st.session_state['last_ticker'], start_date, end_date_input)
            
            if df.empty:
                st.warning("No data returned for this asset ticker sequence.")
            else:
                # KPIs
                current_price = stock_info.get('currentPrice', df['Close'].iloc[-1].item() if not df.empty else 0)
                prev_close = stock_info.get('previousClose', df['Close'].iloc[-2].item() if len(df) > 1 else current_price)
                price_change = current_price - prev_close
                pct_change = (price_change / prev_close) * 100
                currency = stock_info.get('currency', 'USD')

                col1, col2, col3, col4 = st.columns(4)
                col1.metric("Company Name", stock_info.get('longName', st.session_state['last_ticker']))
                col2.metric("Current Price", f"{current_price:,.2f} {currency}", f"{price_change:+.2f} ({pct_change:+.2f}%)")
                col3.metric("Market Cap", f"${stock_info.get('marketCap', 0):,}")
                col4.metric("52 Week High", f"{stock_info.get('fiftyTwoWeekHigh', 0):,.2f} {
