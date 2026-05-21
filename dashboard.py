import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
import pandas as pd
from datetime import datetime, timedelta

# --- Page Configuration ---
st.set_page_config(page_title="Stock Analytics Dashboard", layout="wide")
st.title("📈 Advanced Stock Analytics Platform")

# --- Sidebar Inputs ---
st.sidebar.header("Dashboard Settings")

# Placeholder container at the very top of the sidebar for context-aware inputs
ticker_container = st.sidebar.container()

st.sidebar.markdown("---")

# 1. Date Parameters (Acts as custom manual override)
st.sidebar.subheader("Custom Date Filter")
use_custom_dates = st.sidebar.checkbox("Use Custom Dates Instead", value=False)

end_date = datetime.today()
start_date_default = end_date - timedelta(days=365)
sidebar_start = st.sidebar.date_input("Start Date", value=start_date_default, disabled=not use_custom_dates)
sidebar_end = st.sidebar.date_input("End Date", value=end_date, disabled=not use_custom_dates)

st.sidebar.markdown("---")

# 2. Choose Mode (Cleanly positioned at the bottom of the sidebar panel)
app_mode = st.sidebar.radio("Select Dashboard Mode", ["Single Ticker Lookup", "Multi-Ticker Comparison"])

# --- Manual Refresh Button ---
if st.sidebar.button("🔄 Force Live Refresh"):
    st.cache_data.clear()
    st.rerun()

# --- Helper Functions with Adaptive Resolution ---
@st.cache_data(ttl=60)
def load_single_data(symbol, start, end, interval="1d"):
    if interval == "1m":
        stock_data = yf.download(symbol, period="1d", interval="1m")
    elif interval == "2m":
        stock_data = yf.download(symbol, period="5d", interval="2m")
    else:
        stock_data = yf.download(symbol, start=start, end=end, interval=interval)
    info = yf.Ticker(symbol).info
    return stock_data, info

@st.cache_data(ttl=60)
def load_multi_data(symbols, start, end):
    df_multi = yf.download(symbols, start=start, end=end)['Close']
    return pd.DataFrame(df_multi)

# =====================================================================
# MODE 1: SINGLE TICKER LOOKUP
# =====================================================================
if app_mode == "Single Ticker Lookup":
    # Inject input straight to the top of the sidebar panel
    ticker = ticker_container.text_input("Enter Stock Ticker", value="AAPL").upper()
    
    st.markdown("---")
    st.subheader("Interactive Price Chart")
    
    # Grid alignment for graph customizers
    time_col1, time_col2 = st.columns([2, 3])
    
    with time_col1:
        chart_type = st.radio("Chart Type", ["Candlestick", "Line"], horizontal=True, label_visibility="collapsed")
        
    with time_col2:
        timeframe = st.segmented_control(
            "Timeframe",
            options=["1D", "1W", "1M", "YTD", "1Y", "5Y", "MAX"],
            default="1Y",
            label_visibility="collapsed"
        )

    # Dynamic Timeframe Calculations
    now = datetime.today()
    interval = "1d"
    
    if use_custom_dates:
        start_date = sidebar_start
        end_date_input = sidebar_end
    else:
        end_date_input = now
        if timeframe == "1D":
            start_date = now - timedelta(days=1)
            interval = "1m"
        elif timeframe == "1W":
            start_date = now - timedelta(days=7)
            interval = "2m"
        elif timeframe == "1M":
            start_date = now - timedelta(days=30)
        elif timeframe == "YTD":
            start_date = datetime(now.year, 1, 1)
        elif timeframe == "1Y":
            start_date = now - timedelta(days=365)
        elif timeframe == "5Y":
            start_date = now - timedelta(days=5*365)
        else:
            start_date = datetime(1970, 1, 1)

    try:
        with st.spinner(f"Fetching data for {ticker}..."):
            df, stock_info = load_single_data(ticker, start_date, end_date_input, interval)
        
        # Financial Health KPIs
        current_price = stock_info.get('currentPrice', df['Close'].iloc[-1].item() if not df.empty else 0)
        prev_close = stock_info.get('previousClose', df['Close'].iloc[-2].item() if len(df) > 1 else current_price)
        price_change = current_price - prev_close
        pct_change = (price_change / prev_close) * 100
        currency = stock_info.get('currency', 'USD')

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Company Name", stock_info.get('longName', ticker))
        col2.metric("Current Price", f"{current_price:,.2f} {currency}", f"{price_change:+.2f} ({pct_
