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

# 1. Choose Mode
app_mode = st.sidebar.radio("Select Dashboard Mode", ["Single Ticker Lookup", "Multi-Ticker Comparison"])

# 2. Date Parameters (Now acts as a fallback/override for custom ranges)
st.sidebar.markdown("---")
st.sidebar.subheader("Custom Date Filter")
use_custom_dates = st.sidebar.checkbox("Use Custom Dates Instead", value=False)

end_date = datetime.today()
start_date_default = end_date - timedelta(days=365)
sidebar_start = st.sidebar.date_input("Start Date", value=start_date_default, disabled=not use_custom_dates)
sidebar_end = st.sidebar.date_input("End Date", value=end_date, disabled=not use_custom_dates)

st.sidebar.markdown("---")

# 3. Choose Mode Selector Placement
ticker_container = st.sidebar.container()

# --- Manual Refresh Button ---
if st.sidebar.button("🔄 Force Live Refresh"):
    st.cache_data.clear()
    st.rerun()

# --- Helper Functions with Dynamic Interval Handling ---
@st.cache_data(ttl=60)
def load_single_data(symbol, start, end, interval="1d"):
    # If it's a 1-day view, we fetch intraday data using period instead of strict start/end dates
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
    ticker = ticker_container.text_input("Enter Stock Ticker", value="AAPL").upper()
    
    st.markdown("---")
    
    # --- Timeframe Selector Buttons (Aesthetic Row right above the chart) ---
    st.subheader("Interactive Price Chart")
    time_col1, time_col2 = st.columns([2, 3])
    
    with time_col1:
        chart_type = st.radio("Chart Type", ["Candlestick", "Line"], horizontal=True, label_visibility="collapsed")
        
    with time_col2:
        # Segmented control layout for Timeframes
        timeframe = st.segmented_control(
            "Timeframe",
            options=["1D", "1W", "1M", "YTD", "1Y", "5Y", "MAX"],
            default="1Y",
            label_visibility="collapsed"
        )

    # Calculate dynamic dates and intervals based on selected button
    now = datetime.today()
    interval = "1d"
    
    if use_custom_dates:
        start_date = sidebar_start
        end_date_input = sidebar_end
    else:
        end_date_input = now
        if timeframe == "1D":
            start_date = now - timedelta(days=1)
            interval = "1m"  # 1-minute bars for fine-grained intraday tracking
        elif timeframe == "1W":
            start_date = now - timedelta(days=7)
            interval = "2m"  # 2-minute bars for smooth weekly views
        elif timeframe == "1M":
            start_date = now - timedelta(days=30)
        elif timeframe == "YTD":
            start_date = datetime(now.year, 1, 1)
        elif timeframe == "1Y":
            start_date = now - timedelta(days=365)
        elif timeframe == "5Y":
            start_date = now - timedelta(days=5*365)
        else: # MAX
            start_date = datetime(1970, 1, 1)

    try:
        with st.spinner(f"Fetching data for {ticker}..."):
            df, stock_info = load_single_data(ticker, start_date, end_date_input, interval)
        
        # Financial Summary KPI Block
        current_price = stock_info.get('currentPrice', df['Close'].iloc[-1].item() if not df.empty else 0)
        prev_close = stock_info.get('previousClose', df['Close'].iloc[-2].item() if len(df) > 1 else current_price)
        price_change = current_price - prev_close
        pct_change = (price_change / prev_close) * 100
        currency = stock_info.get('currency', 'USD')

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Company Name", stock_info.get('longName', ticker))
        col2.metric("Current Price", f"{current_price:,.2f} {currency}", f"{price_change:+.2f} ({pct_change:+.2f}%)")
        col3.metric("Market Cap", f"${stock_info.get('marketCap', 0):,}")
        col4.metric("52 Week High", f"{stock_info.get('fiftyTwoWeekHigh', 0):,.2f} {currency}")

        # Render Main Graph
        fig = go.Figure()
        if chart_type == "Candlestick":
            fig.add_trace(go.Candlestick(x=df.index, open=df['Open'].squeeze(), high=df['High'].squeeze(), low=df['Low'].squeeze(), close=df['Close'].squeeze(), name="Market Data"))
        else:
            fig.add_trace(go.Scatter(x=df.index, y=df['Close'].squeeze(), mode='lines', name='Close Price', line=dict(color='#00FFCC', width=2)))

        fig.update_layout(template="plotly_dark", xaxis_rangeslider_visible=False, margin=dict(l=20, r=20, t=10, b=20), height=500)
        st.plotly_chart(fig, use_container_width=True)

        # Trading Volume Graph
        st.subheader("Trading Volume")
        vol_fig = go.Figure(data=[go.Bar(x=df.index, y=df['Volume'].squeeze(), marker_color='royalblue')])
        vol_fig.update_layout(template="plotly_dark", height=200, margin=dict(l=20, r=20, t=10, b=10))
        st.plotly_chart(vol_fig, use_container_width=True)

        st.markdown("---")
        st.subheader("Company Profile")
        st.write(stock_info.get('longBusinessSummary', "No summary available."))

    except Exception as e:
        st.error(f"Error loading data for ticker '{ticker}'. This timeframe might not be supported for this asset.")

# =====================================================================
# MODE 2: MULTI-TICKER COMPARISON
# =====================================================================
else:
    st.subheader("⚔️ Relative Performance Comparison")
    st.markdown("Type and add multiple tickers below to compare their cumulative returns over time.")
    
    tickers_input = ticker_container.text_input("Enter Tickers (separated by commas)", value="AAPL, NVDA, MSFT, SPY")
    ticker_list = [t.strip().upper() for t in tickers_input.split(",") if t.strip()]
    
    # Calculate operational dates for multi-comparison mode
    if use_custom_dates:
        start_date = sidebar_start
        end_date_input = sidebar_end
    else:
        end_date_input = datetime.today()
        start_date = end_date_input - timedelta(days=365) # Defaults back to a trailing year for sanity
        
    if ticker_list:
        try:
            with st.spinner("Fetching comparative market data..."):
                df_multi = load_multi_data(ticker_list, start_date, end_date_input)
            
            if not df_multi.empty:
                if isinstance(df_multi, pd.Series):
                    df_multi = df_multi.to_frame(name=ticker_list[0])
                
                df_multi = df_multi.dropna(how='all')
                df_normalized = (df_multi.ffill().bfill() / df_multi.ffill().bfill().iloc[0] - 1) * 100
                
                comp_fig = go.Figure()
                for crypto_or_stock in df_normalized.columns:
                    comp_fig.add_trace(go.Scatter(x=df_normalized.index, y=df_normalized[crypto_or_stock], mode='lines', name=crypto_or_stock, line=dict(width=2)))
                
                comp_fig.update_layout(template="plotly_dark", xaxis_title="Date", yaxis_title="Cumulative Return (%)", hovermode="x unified", height=600, margin=dict(l=20, r=20, t=30, b=20), yaxis=dict(tickformat="+.1f%"))
                st.plotly_chart(comp_fig, use_container_width=True)
                
                st.subheader("Performance Summary Breakdown")
                final_returns = df_normalized.iloc[-1]
                summary_data = []
                for asset in final_returns.index:
                    summary_data.append({"Ticker": asset, "Total Return Since Start Date": f"{final_returns[asset]:+.2f}%"})
                st.table(pd.DataFrame(summary_data))
                
            else:
                st.warning("No data found for the provided symbols.")
        except Exception as e:
            st.error(f"Error executing multi-ticker build: {e}")
