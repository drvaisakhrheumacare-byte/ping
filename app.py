import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# === Google Sheets setup ===
SHEET_ID = "1uf4pqKHEAbw6ny7CVZZVMw23PTfmv0QZzdCyj4fU33c"
USERS_TAB = "aaa"
SERVERS_TAB = "ServerStatus"

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

users_df = load_users()
servers_df = load_servers()

def get_user_centres(users_df, username):
    row = users_df.loc[users_df["Username"] == username].iloc[0]
    centres = str(row["Centre"]).strip()
    return centres

st.set_page_config(page_title="Server Monitoring", page_icon="🖥️", layout="wide")

st.image(
    "https://github.com/drvaisakhrheumacare-byte/clinic-ops-app/blob/main/logo.png?raw=true",
    width=200
)
st.title("🖥️ Server Monitoring Dashboard")

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        if username in users_df["Username"].values:
            row = users_df.loc[users_df["Username"] == username].iloc[0]
            if password == str(row["Password"]).strip():
                st.session_state.logged_in = True
                st.session_state.username = username
                # no rerun call — dashboard will render immediately
            else:
                st.error("Incorrect password")
        else:
            st.error("Username not found")

if st.session_state.logged_in:
    username = st.session_state.username
    row = users_df.loc[users_df["Username"] == username].iloc[0]
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

        order = ["Main Server", "Backup Server", "Bitvoice Gateway", "Bitvoice Server"]
        filtered_servers["Server Name"] = pd.Categorical(
            filtered_servers["Server Name"],
            categories=order,
            ordered=True
        )
        filtered_servers = filtered_servers.sort_values("Server Name")

        def color_status(val):
            if str(val).lower() == "success":
                return "background-color: lightgreen"
            elif str(val).lower() == "failed":
                return "background-color: lightcoral"
            else:
                return ""

        display_cols = ["Centre", "Status", "Timestamp", "ResponseTime(ms)", "Server IP"]

        for category in order:
            subset = filtered_servers[filtered_servers["Server Name"] == category]
            if not subset.empty:
                st.subheader(f"{category}")
                subset = subset[display_cols]
                st.dataframe(
                    subset.style.applymap(color_status, subset=["Status"]),
                    use_container_width=True
                )
