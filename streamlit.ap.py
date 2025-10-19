from google.oauth2.service_account import Credentials  # ADD THIS IMPORT
import gspread  # Line 6 is correct
import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(
    layout="wide", page_title="Stock Trading Equity Curve Tracker")

# --- Connection ---
# # Use st.secrets to load the JSON key file content


# --- Connection ---
# Use st.secrets to load the JSON key file content

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

# --- Data Fetching and Caching (Cached for 10 minutes) ---


@st.cache_data(ttl=600)
@st.cache_data(ttl=600)
def load_data():
    """Loads data from Google Sheet, calculates Equity, and caches the result."""

    # Read the first two columns (Date and Amount/P&L) from Sheet1
    # Assumes headers are 'Date' in A1 and 'Amount' in B1
    data = worksheet.get_all_values()

    df = pd.DataFrame(data[1:], columns=['date', 'amount'])

    # Convert 'Amount' to numeric, dropping invalid rows
    df['amount'] = pd.to_numeric(df['amount'], errors='coerce')
    df.dropna(subset=['amount'], inplace=True)

    # Ensure Date is in datetime format and sort the data
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values(by='date').reset_index(drop=True)

    # Calculate the cumulative equity curve (using 'amount' as P&L)
    df['Equity'] = df['amount'].cumsum()

    return df


# --- Load Data ---
df = load_data()

# -----------------------------------------------------------
# Sidebar Form (Daily P/L Entry)
# -----------------------------------------------------------

st.sidebar.title("Daily P/L Entry")

with st.sidebar.form("daily_pl_form", clear_on_submit=True):
    date_input = st.date_input("Date of P/L", value=pd.to_datetime('today'))

    # Use a number input for the Daily P/L
    pl_input = st.number_input(
        "Daily P/L ($)", step=0.01, format="%.2f", value=0.00)

    submitted = st.form_submit_button("Log P/L")

if submitted:
    # 1. Prepare the new data row to match Google Sheet headers ('Date', 'Amount')
    new_data = pd.DataFrame([{
        "Date": date_input.strftime("%Y-%m-%d"),
        "Amount": pl_input  # 'Amount' is the header in your Google Sheet (B1)
    }])

    try:
        # 2. Append the data as a new row to the Google Sheet
        worksheet.append_row(
            new_data.iloc[0].tolist(), value_input_option='USER_ENTERED')

        # 3. Clear cache and re-run to update the view with the new data
        st.cache_data.clear()
        st.success("Entry logged successfully and saved to Google Sheet!")
        st.rerun()

    except Exception as e:
        st.sidebar.error(
            f"Failed to write to Google Sheet. Check your secrets and sheet permissions. Error: {e}")


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
