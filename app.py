import streamlit as st
import pandas as pd

# === CONFIG: raw GitHub CSV URLs ===
USERS_CSV_URL = "https://raw.githubusercontent.com/drvaisakhrheumacare-byte/ping/main/Users.csv"
SERVERS_CSV_URL = "https://raw.githubusercontent.com/drvaisakhrheumacare-byte/ping/main/ServerStatus.csv"

# === Loaders with caching ===
@st.cache_data(ttl=30)
def load_users():
    df = pd.read_csv(USERS_CSV_URL, dtype=str).fillna("")
    df.columns = [c.strip() for c in df.columns]
    return df

@st.cache_data(ttl=15)
def load_servers():
    df = pd.read_csv(SERVERS_CSV_URL, dtype=str).fillna("")
    df.columns = [c.strip() for c in df.columns]
    if "Status" in df.columns:
        df["Status"] = df["Status"].str.lower().str.strip()
    return df

# === Helpers ===
def get_user_row(users_df, username):
    row = users_df[users_df["username"] == username]
    return row.iloc[0] if not row.empty else None

def get_user_centres(users_df, username):
    row = get_user_row(users_df, username)
    if row is None:
        return []
    centres = str(row["centres"])
    return [c.strip() for c in centres.split(";") if c.strip()]

def tile_html(server):
    status = str(server.get("Status", "")).lower()
    color = "#d9534f" if status in ("failed", "down", "error") else "#5cb85c"
    name = server.get("Server Name", "")
    ip = server.get("Server IP", "")
    resp = server.get("ResponseTime(ms)", "")
    ts = server.get("Timestamp", "")
    html = f"""
    <div class="tile" style="background:{color};">
      <div class="tile-title">{name}</div>
      <div class="tile-ip">{ip}</div>
      <div class="tile-meta">RT: {resp} ms</div>
      <div class="tile-ts">{ts}</div>
    </div>
    """
    return html

# === App state ===
st.set_page_config(page_title="Server Tiles", layout="wide")
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "username" not in st.session_state:
    st.session_state.username = ""
if "centres" not in st.session_state:
    st.session_state.centres = []
if "current_index" not in st.session_state:
    st.session_state.current_index = 0
if "mode" not in st.session_state:
    st.session_state.mode = "tiles"  # or "list"

# === Load data ===
try:
    users_df = load_users()
    servers_df = load_servers()
except Exception as e:
    st.error("Error loading data from GitHub. " + str(e))
    st.stop()

# === Login screen ===
if not st.session_state.logged_in:
    st.title("Login")
    with st.form("login_form", clear_on_submit=False):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Sign in")
    if submitted:
        row = get_user_row(users_df, username)
        if row is None:
            st.error("Unknown user")
        else:
            stored_pw = str(row["password"]).strip()
            if password == stored_pw:
                st.session_state.logged_in = True
                st.session_state.username = username
                st.session_state.centres = get_user_centres(users_df, username)
                st.session_state.current_index = 0
                st.experimental_rerun()
            else:
                st.error("Invalid password")
    st.stop()

# === Main UI after login ===
st.markdown(f"### Welcome, **{st.session_state.username}**")
centres = st.session_state.centres
if not centres:
    st.warning("No centres assigned to your account.")
    st.stop()

# Centre selector
col_top = st.columns([1, 3, 1])
with col_top[1]:
    selected = st.selectbox("Centre", options=centres, index=st.session_state.current_index)
    st.session_state.current_index = centres.index(selected)

# Inline CSS for tiles
st.markdown("""
<style>
.tile { padding:12px; margin:8px; border-radius:8px; color:#fff; min-height:110px; box-shadow: 0 2px 6px rgba(0,0,0,0.2);}
.tile-title { font-weight:700; font-size:18px; }
.tile-ip { font-size:13px; opacity:0.95; }
.tile-meta { font-size:13px; margin-top:6px; }
.tile-ts { font-size:12px; opacity:0.9; margin-top:8px; }
</style>
""", unsafe_allow_html=True)

# Render mode
if st.session_state.mode == "tiles":
    centre = centres[st.session_state.current_index]
    st.subheader(f"Centre: {centre}")
    centre_servers = servers_df[servers_df["Centre"] == centre].sort_values(by="Server Name") if "Centre" in servers_df.columns else pd.DataFrame()
    cols = st.columns(3)
    servers_list = centre_servers.to_dict(orient="records")
    if not servers_list:
        st.info("No servers found for this centre.")
    else:
        for i, srv in enumerate(servers_list):
            col = cols[i % 3]
            with col:
                st.markdown(tile_html(srv), unsafe_allow_html=True)
else:
    st.subheader("Consolidated Dashboard")
    all_servers = servers_df.sort_values(by=["Centre", "Server Name"]) if "Centre" in servers_df.columns else servers_df
    def status_badge(s):
        s = str(s).lower()
        return "🔴" if s in ("failed", "down", "error") else "🟢"
    display = all_servers.copy()
    if "Status" in display.columns:
        display["OK"] = display["Status"].apply(status_badge)
    cols_to_show = [c for c in ["OK", "Centre", "Server Name", "Server IP", "ResponseTime(ms)", "Status", "Timestamp"] if c in display.columns or c == "OK"]
    st.dataframe(display[cols_to_show].rename(columns={"OK": "Status"}), use_container_width=True)

# Footer controls
st.markdown("---")
f1, f2, f3 = st.columns([1, 1, 1])
with f1:
    if st.button("Back"):
        st.session_state.current_index = max(0, st.session_state.current_index - 1)
        st.session_state.mode = "tiles"
        st.experimental_rerun()
with f2:
    if st.session_state.mode == "tiles":
        if st.button("Consolidated Dashboard"):
            st.session_state.mode = "list"
            st.experimental_rerun()
    else:
        if st.button("Back to Tiles"):
            st.session_state.mode = "tiles"
            st.experimental_rerun()
with f3:
    if st.button("Next"):
        st.session_state.current_index = min(len(centres) - 1, st.session_state.current_index + 1)
        st.session_state.mode = "tiles"
        st.experimental_rerun()

# Sidebar refresh
st.sidebar.markdown("### Refresh")
if st.sidebar.button("Refresh now"):
    st.experimental_rerun()
