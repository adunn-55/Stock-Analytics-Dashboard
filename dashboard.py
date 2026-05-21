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

st.sidebar.markdown("---")
# 3. Action Trigger (Prevents automated API spamming while typing)
run_analysis = st.sidebar.button("🔍 Run Financial Analysis", use_container_width=True)

# --- Helper Functions with Native Adaptive Resolution ---
@st.cache_data(ttl=3600)  # 1-hour memory cache protects shared cloud IP limits
def load_single_data(symbol, start, end):
    stock_data = yf.download(symbol, start=start, end=end, interval="1d")
    
    # Flatten Multi-Index Columns safely if present
    if isinstance(stock_data.columns, pd.MultiIndex):
        stock_data.columns = stock_data.columns.get_level_values(0)
        
    info = yf.Ticker(symbol).info
    return stock_data, info

@st.cache_data(ttl=3600)
def load_multi_data(symbols, start, end):
    df_multi = yf.download(symbols, start=start, end=end)['Close']
    return pd.DataFrame(df_multi)

# =====================================================================
# MODE 1: SINGLE TICKER LOOKUP
# =====================================================================
if app_mode == "Single Ticker Lookup":
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
            options=["1M", "YTD", "1Y", "5Y", "MAX"],
            default="1Y",
            label_visibility="collapsed"
        )

    # Dynamic Timeframe Calculations
    now = datetime.today()
    
    if use_custom_dates:
        start_date = sidebar_start
        end_date_input = sidebar_end
    else:
        end_date_input = now
        if timeframe == "1M":
            start_date = now - timedelta(days=30)
        elif timeframe == "YTD":
            start_date = datetime(now.year, 1, 1)
        elif timeframe == "1Y":
            start_date = now - timedelta(days=365)
        elif timeframe == "5Y":
            start_date = now - timedelta(days=5*365)
        else:
            start_date = datetime(1970, 1, 1)

    # Execution requires clicking the sidebar analysis button or first load
    if run_analysis or 'initialized' not in st.session_state:
        st.session_state['initialized'] = True
        try:
            with st.spinner(f"Fetching data for {ticker}..."):
                df, stock_info = load_single_data(ticker, start_date, end_date_input)
            
            if df.empty:
                st.warning("No data returned for this asset ticker sequence.")
            else:
                # Financial Health KPIs
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

                # --- Main Chart Render ---
                fig = go.Figure()
                
                # CRITICAL: Force the index to native datetime objects so rangebreaks map perfectly
                timeline_index = pd.to_datetime(df.index)
                
                if chart_type == "Candlestick":
                    fig.add_trace(go.Candlestick(
                        x=timeline_index, 
                        open=df['Open'].squeeze(), 
                        high=df['High'].squeeze(), 
                        low=df['Low'].squeeze(), 
                        close=df['Close'].squeeze(), 
                        name="Market Data"
                    ))
                else:
                    fig.add_trace(go.Scatter(
                        x=timeline_index, 
                        y=df['Close'].squeeze(), 
                        mode='lines', 
                        name='Close Price', 
                        line=dict(color='#00FFCC', width=2)
                    ))

                fig.update_layout(
                    template="plotly_dark", 
                    xaxis_rangeslider_visible=False, 
                    margin=dict(l=20, r=20, t=10, b=20), 
                    height=500,
                    xaxis=dict(
                        type='date',
                        tickmode='auto',
                        nticks=8,
                        rangebreaks=[
                            dict(bounds=["sat", "mon"])  # Seamlessly removes weekend blank blocks
                        ]
                    )
                )
                st.plotly_chart(fig, use_container_width=True)

                # Trading Volume
                st.subheader("Trading Volume")
                vol_fig = go.Figure(data=[go.Bar(x=timeline_index, y=df['Volume'].squeeze(), marker_color='royalblue')])
                vol_fig.update_layout(
                    template="plotly_dark", 
                    height=200, 
                    margin=dict(l=20, r=20, t=10, b=10),
                    xaxis=dict(
                        type='date',
                        tickmode='auto',
                        nticks=8,
                        rangebreaks=[
                            dict(bounds=["sat", "mon"])
                        ]
                    )
                )
                st.plotly_chart(vol_fig, use_container_width=True)

                st.markdown("---")
                st.subheader("Company Profile")
                st.write(stock_info.get('longBusinessSummary', "No summary available."))

        except Exception as e:
            st.error(f"Error loading data for ticker '{ticker}'. Technical details: {e}")
    else:
        st.info("💡 Adjust your dashboard criteria in the sidebar and click 'Run Financial Analysis' to pull fresh market matrices.")

# =====================================================================
# MODE 2: MULTI-TICKER COMPARISON
# =====================================================================
else:
    st.subheader("⚔️ Relative Performance Comparison")
    st.markdown("Type and add multiple tickers below to compare their cumulative returns over time.")
    
    tickers_input = ticker_container.text_input("Enter Tickers (separated by commas)", value="AAPL, NVDA, MSFT, SPY")
    ticker_list = [t.strip().upper() for t in tickers_input.split(",") if t.strip()]
    
    if use_custom_dates:
        start_date = sidebar_start
        end_date_input = sidebar_end
    else:
        end_date_input = datetime.today()
        start_date = end_date_input - timedelta(days=365)
        
    if run_analysis or 'initialized' not in st.session_state:
        st.session_state['initialized'] = True
        if ticker_list:
            try:
                with st.spinner("Fetching comparative market data..."):
                    df_multi = load_multi_data(ticker_list, start_date, end_date_input)
                
                if not df_multi.empty:
                    if isinstance(df_multi.columns, pd.MultiIndex):
                        df_multi.columns = df_multi.columns.get_level_values(1) if 'Close' in df_multi.columns.get_level_values(0) else df_multi.columns.get_level_values(0)
                    
                    if isinstance(df_multi, pd.Series):
                        df_multi = df_multi.to_frame(name=ticker_list[0])
                    
                    df_multi = df_multi.dropna(how='all')
                    df_normalized = (df_multi.ffill().bfill() / df_multi.ffill().bfill().iloc[0] - 1) * 100
                    
                    comp_fig = go.Figure()
                    for asset in df_normalized.columns:
                        comp_fig.add_trace(go.Scatter(x=df_normalized.index, y=df_normalized[asset], mode='lines', name=asset, line=dict(width=2)))
                    
                    comp_fig.update_layout(
                        template="plotly_dark", 
                        xaxis_title="Date", 
                        yaxis_title="Cumulative Return (%)", 
                        hovermode="x unified", 
                        height=600, 
                        margin=dict(l=20, r=20, t=30, b=20), 
                        yaxis=dict(tickformat="+.1f%")
                    )
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
    else:
        st.info("💡 Click 'Run Financial Analysis' to compute normalized comparative paths.")
