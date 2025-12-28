import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# === Google Sheets setup ===
SHEET_ID = "1uf4pqKHEAbw6ny7CVZZVMw23PTfmv0QZzdCyj4fU33c"  # your sheet ID
USERS_TAB = "aaa"             # tab for users
SERVERS_TAB = "ServerStatus"  # tab for server status

# --- Load credentials from Streamlit secrets ---
creds_dict = st.secrets["gcp_service_account"]
scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive"
]
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
client = gspread.authorize(creds)

# === Loaders ===
@st.cache_data(ttl=30)
def load_users():
    ws = client.open_by_key(SHEET_ID).worksheet(USERS_TAB)
    data = ws.get_all_records()
    df = pd.DataFrame(data)
    df.columns = df.columns.str.strip()
    return df

@st.cache_data(ttl=30)
def load_servers():
    ws = client.open_by_key(SHEET_ID).worksheet(SERVERS_TAB)
    data = ws.get_all_records()
    df = pd.DataFrame(data)
    df.columns = df.columns.str.strip()
    return df

# === Use loaders ===
users_df = load_users()
servers_df = load_servers()

st.write("Users data:", users_df.head())
st.write("Servers data:", servers_df.head())
