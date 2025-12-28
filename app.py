import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

# --- Authenticate with Google using secrets.toml ---
scope = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]
creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scope)
client = gspread.authorize(creds)

# --- Google Sheet IDs (replace with your actual IDs) ---
USERS_SHEET_ID = "1uf4pqKHEAbw6ny7CVZZVMw23PTfmv0QZzdCyj4fU33c"     # Users sheet
SERVERS_SHEET_ID = "1z3GnmXOaouQH6Z0ZG59b8AftTTuL0gc5cgcAKHUqPiY"   # ServerStatus sheet

# --- Load data from Google Sheets ---
users_ws = client.open_by_key(USERS_SHEET_ID).sheet1   # first tab of Users sheet
servers_ws = client.open_by_key(SERVERS_SHEET_ID).sheet1   # first tab of Servers sheet

users_df = pd.DataFrame(users_ws.get_all_records())
servers_df = pd.DataFrame(servers_ws.get_all_records())

# --- Helper function ---
def get_user_centres(users_df, username):
    """Return the centres string for a given user."""
    row = users_df.loc[users_df["Username"] == username].iloc[0]
    centres = str(row["Centre"]).strip()
    return centres

# --- Streamlit UI ---
st.set_page_config(page_title="Server Monitoring", page_icon="🖥️")
st.title("🖥️ Server Monitoring Dashboard")

# --- Login ---
username = st.text_input("Username")
password = st.text_input("Password", type="password")

if st.button("Login"):
    if username in users_df["Username"].values:
        row = users_df.loc[users_df["Username"] == username].iloc[0]
        if password == str(row["Password"]).strip():
            st.success(f"Welcome {row['Name']}!")

            # --- Get centres for this user ---
            user_centre = get_user_centres(users_df, username)

            if user_centre.lower() == "all":
                filtered_servers = servers_df
            else:
                user_centres = [c.strip() for c in user_centre.split(",") if c.strip()]
                filtered_servers = servers_df[servers_df["Centre"].isin(user_centres)]

            if filtered_servers.empty:
                st.error(f"No servers found for centres: {user_centre}")
            else:
                st.write(f"Showing servers for centres: {user_centre}")

                # Highlight status with colors
                def color_status(val):
                    if str(val).lower() == "success":
                        return "background-color: lightgreen"
                    elif str(val).lower() == "failed":
                        return "background-color: lightcoral"
                    else:
                        return ""
                st.dataframe(filtered_servers.style.applymap(color_status, subset=["Status"]))

        else:
            st.error("Incorrect password")
    else:
        st.error("Username not found")
