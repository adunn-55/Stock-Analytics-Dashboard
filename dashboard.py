%%writefile dashboard.py
import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
from datetime import datetime, timedelta

# --- Page Configuration ---
st.set_page_config(page_title="Stock Analytics Dashboard", layout="wide")
st.title("📈 Real-Time Stock Analytics Dashboard")

# --- Sidebar Inputs ---
st.sidebar.header("Dashboard Settings")
ticker = st.sidebar.text_input("Enter Stock Ticker (e.g., AAPL, TSLA, MSFT)", value="AAPL").upper()

end_date = datetime.today()
start_date_default = end_date - timedelta(days=365)
start_date = st.sidebar.date_input("Start Date", value=start_date_default)
end_date_input = st.sidebar.date_input("End Date", value=end_date)

# Add a hard reset button to the sidebar layout
if st.sidebar.button("🔄 Force Live Refresh"):
    st.cache_data.clear()  # Wipes out all stored stock data completely
    st.rerun()             # Reruns the entire page from scratch

# Caches data for exactly 60 seconds. Fast UI navigation, but automatically updates live every minute.
@st.cache_data(ttl=60)
def load_data(symbol, start, end):
    stock_data = yf.download(symbol, start=start, end=end)
    info = yf.Ticker(symbol).info
    return stock_data, info

try:
    with st.spinner(f"Fetching data for {ticker}..."):
        df, stock_info = load_data(ticker, start_date, end_date_input)
    
    current_price = stock_info.get('currentPrice', df['Close'].iloc[-1].item() if not df.empty else 0)
    prev_close = stock_info.get('previousClose', df['Close'].iloc[-2].item() if len(df) > 1 else current_price)
    price_change = current_price - prev_close
    pct_change = (price_change / prev_close) * 100
    currency = stock_info.get('currency', 'USD')

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Company Name", stock_info.get('longName', ticker))
    col2.metric("Current Price", f"{current_price:,.2f} {currency}", f"{price_change:+.2f} ({pct_change:+.2f}%) Kishan")
    col3.metric("Market Cap", f"${stock_info.get('marketCap', 0):,}")
    col4.metric("52 Week High", f"{stock_info.get('fiftyTwoWeekHigh', 0):,.2f} {currency}")

    st.markdown("---")
    st.subheader("Price Movement & Analysis")
    chart_type = st.radio("Select Chart Type", ["Candlestick", "Line"], horizontal=True)
    
    fig = go.Figure()
    if chart_type == "Candlestick":
        fig.add_trace(go.Candlestick(x=df.index, open=df['Open'].squeeze(), high=df['High'].squeeze(), low=df['Low'].squeeze(), close=df['Close'].squeeze(), name="Market Data"))
    else:
        fig.add_trace(go.Scatter(x=df.index, y=df['Close'].squeeze(), mode='lines', name='Close Price', line=dict(color='#00FFCC', width=2)))

    fig.update_layout(template="plotly_dark", xaxis_rangeslider_visible=False, margin=dict(l=20, r=20, t=20, b=20), height=500)
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("Trading Volume")
    vol_fig = go.Figure(data=[go.Bar(x=df.index, y=df['Volume'].squeeze(), marker_color='royalblue')])
    vol_fig.update_layout(template="plotly_dark", height=200, margin=dict(l=20, r=20, t=10, b=10))
    st.plotly_chart(vol_fig, use_container_width=True)

    st.markdown("---")
    st.subheader("Company Profile")
    st.write(stock_info.get('longBusinessSummary', "No summary available."))

except Exception as e:
    st.error(f"Error loading data for ticker '{ticker}'. Please check the symbol and try again.")
