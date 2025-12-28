import streamlit as st
import pandas as pd
import re

# --- Google Sheet URLs ---
# Replace with your actual published sheet links
USERS_SHEET_URL = "https://docs.google.com/spreadsheets/d/<USERS_SHEET_ID>/edit?gid=<TAB_ID>"
SERVERS_SHEET_URL = "https://docs.google.com/spreadsheets/d/<SERVERS_SHEET_ID>/edit?gid=<TAB_ID>"

def get_csv_export_url(sheet_url):
    """Convert a Google Sheet URL into a CSV export link."""
    sheet_id_match = re.search(r'/d/([a-zA-Z0-9-_]+)', sheet_url)
    if not sheet_id_match:
        return None
    sheet_id = sheet_id_match.group(1)

    gid = "0"
    gid_match = re.search(r'[#&?]gid=([0-9]+)', sheet_url)
    if gid_match:
        gid = gid_match.group(1)

    return f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}"

# --- Load data directly from Google Sheets ---
users_df = pd.read_csv(get_csv_export_url(USERS_SHEET_URL))
servers_df = pd.read_csv(get_csv_export_url(SERVERS_SHEET_URL))

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
