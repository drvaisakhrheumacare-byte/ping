import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# === Google Sheets setup ===
SHEET_ID = "1uf4pqKHEAbw6ny7CVZZVMw23PTfmv0QZzdCyj4fU33c"  # your sheet ID
USERS_TAB = "aaa"             # tab for users
SERVERS_TAB = "ServerStatus"  # tab for server status
SERVERCHECK_TAB = "ServerCheck"  # tab for server check history

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

@st.cache_data(ttl=30)
def load_servercheck():
    ws = client.open_by_key(SHEET_ID).worksheet(SERVERCHECK_TAB)
    data = ws.get_all_records()
    df = pd.DataFrame(data)
    df.columns = df.columns.str.strip()
    return df

users_df = load_users()
servers_df = load_servers()
servercheck_df = load_servercheck()

# --- Helpers ---
def normalize_centre(s):
    return str(s).strip().upper()

def get_user_centres(users_df, username):
    row = users_df.loc[users_df["Username"] == username].iloc[0]
    centres_raw = str(row["Centre"]).strip()
    centres_list = []
    seen = set()
    for c in centres_raw.split(","):
        norm = normalize_centre(c)
        if norm and norm not in seen:
            centres_list.append(norm)
            seen.add(norm)
    return centres_list

# --- Streamlit UI ---
st.set_page_config(page_title="Server Monitoring", page_icon="🖥️", layout="wide")

# Add logo at the top
st.image(
    "https://github.com/drvaisakhrheumacare-byte/clinic-ops-app/blob/main/logo.png?raw=true",
    width=200
)

st.title("🖥️ Server Monitoring Dashboard")

# --- Login state ---
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
                st.rerun()
            else:
                st.error("Incorrect password")
        else:
            st.error("Username not found")

if st.session_state.logged_in:
    username = st.session_state.username
    row = users_df.loc[users_df["Username"] == username].iloc[0]

    servers_df["Centre"] = servers_df["Centre"].apply(normalize_centre)
    servercheck_df["Centre"] = servercheck_df["Centre"].apply(normalize_centre)
    servercheck_df["Server Name"] = servercheck_df["Server Name"].str.strip()
    servercheck_df["Timestamp"] = pd.to_datetime(servercheck_df["Timestamp"], errors="coerce")

    user_centres_list = get_user_centres(users_df, username)
    is_all = len(user_centres_list) == 1 and user_centres_list[0] == "ALL"

    if is_all:
        filtered_servers = servers_df.copy()
        natural_order = []
        seen = set()
        for c in servers_df["Centre"]:
            if c not in seen:
                natural_order.append(c)
                seen.add(c)
        centre_order = natural_order
    else:
        filtered_servers = servers_df[servers_df["Centre"].isin(user_centres_list)].copy()
        centre_order = user_centres_list

    if filtered_servers.empty:
        st.error(f"No servers found for centres: {', '.join(centre_order)}")
    else:
        # Compute last success per (Centre, Server Name)
        last_success = (
            servercheck_df[servercheck_df["Status"].str.lower() == "success"]
            .sort_values("Timestamp")
            .groupby(["Centre", "Server Name"])["Timestamp"]
            .last()
            .reset_index()
            .rename(columns={"Timestamp": "Last Success"})
        )

        # Merge into filtered_servers
        filtered_servers = pd.merge(
            filtered_servers,
            last_success,
            on=["Centre", "Server Name"],
            how="left"
        )

        def color_status(val):
            v = str(val).strip().lower()
            if v == "success":
                return "background-color: lightgreen"
            if v == "failed":
                return "background-color: lightcoral"
            return ""

        server_type_order = ["Main Server", "Backup Server", "Bitvoice Gateway", "Bitvoice Server"]
        filtered_servers["Server Name"] = pd.Categorical(
            filtered_servers["Server Name"],
            categories=server_type_order,
            ordered=True
        )

        centre_index = {c: i for i, c in enumerate(centre_order)}

        st.write(f"Showing servers for centres (ordered): {', '.join(centre_order)}")

        display_cols = ["Centre", "Status", "Timestamp", "ResponseTime(ms)", "Server IP", "Last Success"]

        for category in server_type_order:
            subset = filtered_servers[filtered_servers["Server Name"] == category].copy()
            if subset.empty:
                continue

            subset["__order__"] = subset["Centre"].map(lambda c: centre_index.get(c, float("inf")))
            subset = subset.sort_values("__order__", kind="stable").drop(columns="__order__")

            for col in display_cols:
                if col not in subset.columns:
                    subset[col] = ""
            subset = subset[display_cols]

            st.subheader(f"{category}")
            st.dataframe(
                subset.style.applymap(color_status, subset=["Status"]),
                use_container_width=True
            )
