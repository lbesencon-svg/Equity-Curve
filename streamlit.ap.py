from google.oauth2.service_account import Credentials  # ADD THIS IMPORT
import gspread  # Line 6 is correct
import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime


def get_gspread_client():
    creds = Credentials.from_service_account_info(
        st.secrets["connections"]["gsheets"],
        scopes=["https://www.googleapis.com/auth/spreadsheets"]
    )
    client = gspread.authorize(creds)
    return client


# Initialize the gspread client and connect to the sheet
gc = get_gspread_client()
spreadsheet_url = st.secrets["connections"]["gsheets"]["spreadsheet"]
sh = gc.open_by_key(spreadsheet_url)
worksheet = sh.worksheet("Sheet1")

st.set_page_config(
    layout="wide", page_title="Stock Trading Equity Curve Tracker")

# streamer.ap.py (Around Line 24)


def log_pl():
    # 1. Access the data from st.session_state
    # Make sure you import datetime at the top of your script if you haven't yet!
    date_to_log = st.session_state['date_input'].strftime('%Y-%m-%d')
    pnl_to_log = st.session_state['pnl_input']

    # 2. Append the data to the Google Sheet
    new_data = [date_to_log, pnl_to_log]
    # Use 'worksheet' as defined on line 19 of your current file
    worksheet.append_row(new_data, value_input_option='USER_ENTERED')

    # 3. Success and Rerun
    st.cache_data.clear()
    st.success("Entry logged successfully and saved to Google Sheet!")

# --- Data Fetching and Caching (Cached for 10 minutes) ---


@st.cache_data(ttl=600)
def load_data(cache_key):  # <--- FINAL ARGUMENT IS HERE
    """Loads data from Google Sheet, calculates Equity, and caches the result."""

    # 2. Read the data from the sheet
    # 'worksheet' must be initialized at the top of your script
    data = worksheet.get_all_values()

    # 3. Create the DataFrame (skipping the header row)
    # Assumes headers are 'date' and 'amount'
    df = pd.DataFrame(data[1:], columns=['date', 'amount'])

    # 4. Clean and convert the 'amount' column
    df['amount'] = pd.to_numeric(df['amount'], errors='coerce')
    df.dropna(subset=['amount'], inplace=True)

    # 5. Format the date and sort the data
    df['date'] = pd.to_datetime(df['date'])
    df.sort_values(by='date', reset_index=True, inplace=True)

    # 6. Calculate the cumulative equity (required for your chart)
    df['Equity'] = df['amount'].cumsum()

    return df

# --- Load Data ---
# Forcing a full deploy build


# 1. Initialize/Retrieve the key (THIS IS THE MISSING PIECE)
if 'sheet_update_key' not in st.session_state:
    st.session_state['sheet_update_key'] = 0

update_key = st.session_state['sheet_update_key']

# 2. Call the function ONCE and PASS THE KEY (This fixes Line 75)
df = load_data(update_key)

# -----------------------------------------------------------
# Sidebar Form (Daily P/L Entry)
# -----------------------------------------------------------

with st.sidebar:
    st.header("Daily P/L Entry")

    # ... your st.date_input and st.number_input here ...

    # The button MUST be here in the sidebar
    st.button("Log P/L", on_click=log_pl)

    st.date_input("Date of P/L", value=datetime.today(), key='date_input')

    # Use a number input for the Daily P/L
    # streamer.ap.py (Final Correct Code)
    st.number_input("Daily P/L ($)", step=0.01, format="%.2f",
                    key='pnl_input', value=0.00)


# -----------------------------------------------------------
# Main Content
# -----------------------------------------------------------
st.title("📈 Stock Trading Equity Curve Tracker")

# 1. Performance Summary (Simplified)
st.header("Performance Summary")
total_pl = df['amount'].sum()

col_total, col_start = st.columns(2)
col_total.metric("TOTAL P/L", f"${total_pl:,.2f}")
col_start.write("Start: **$0.00**")


# 2. Total Equity Curve Chart
st.header("Total Equity Curve")

if not df.empty:
    fig = px.line(df, x='Date', y='Equity', title='Cumulative P/L Over Time')
    st.plotly_chart(fig, use_container_width=True)
    st.markdown(
        "This chart shows your cumulative P/L over time, starting from $0.00.")
else:
    st.info("No data logged yet. Enter your first Daily P/L on the left!")


# 3. Raw Data Log (with Conditional Formatting)
st.header("Raw Data Log")

# Function to apply color styling


def color_negative_red_positive_green(value):
    """Styles a cell with red background for negative, green for positive."""
    if isinstance(value, (int, float)):
        if value < 0:
            return 'background-color: #ff9999'  # Light Red
        elif value > 0:
            return 'background-color: #ccffcc'  # Light Green
    return ''


# Select and rename columns for display
display_df = df[['date', 'amount', 'Equity']].copy()
display_df.rename(columns={'amount': 'Daily P/L',
                  'Equity': 'Cumulative Equity'}, inplace=True)

# Apply styling to the 'Daily P/L' column
styled_df = display_df.style.applymap(
    color_negative_red_positive_green, subset=['Daily P/L'])

# Display the styled DataFrame
st.dataframe(styled_df, use_container_width=True)
