# app.py - minimal Streamlit viewer for Main Server per centre
import streamlit as st
import gspread
import pandas as pd
from datetime import datetime, timezone, timedelta
from dateutil import parser
import os, json, tempfile

# CONFIG
SHEET_URL = "https://docs.google.com/spreadsheets/d/1uf4pqKHEAbw6ny7CVZZVMw23PTfmv0QZzdCyj4fU33c/edit"
CHECK_SHEET = "ServerCheck"
USERS_SHEET = "Users"
IST = timezone(timedelta(hours=5, minutes=30))
FAIL_THRESHOLD = 5

# If running on Streamlit Cloud, write service account JSON from secrets to a temp file
if "gcp_service_account" in st.secrets:
    sa_json = st.secrets["gcp_service_account"]
    # st.secrets stores strings; if you uploaded JSON text, use it directly
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".json")
    tmp.write(sa_json.encode("utf-8"))
    tmp.flush()
    tmp.close()
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = tmp.name

CRED = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", r"D:\dev\Serverlog\credentials.json")

def auth():
    return gspread.service_account(filename=CRED)

def read_df(gc, name):
    sh = gc.open_by_url(SHEET_URL)
    ws = sh.worksheet(name)
    vals = ws.get_all_values()
    if not vals: return pd.DataFrame()
    return pd.DataFrame(vals[1:], columns=vals[0])

def parse_ts(v):
    if v is None or v=="":
        return None
    try:
        if isinstance(v,(int,float)) or (isinstance(v,str) and v.replace('.','',1).isdigit()):
            s = float(v)
            ms = (s - 25569) * 86400 * 1000
            return datetime.utcfromtimestamp(ms/1000.0).replace(tzinfo=timezone.utc).astimezone(IST)
    except: pass
    try:
        d = parser.parse(v)
        if d.tzinfo is None:
            d = d.replace(tzinfo=timezone.utc).astimezone(IST)
        else:
            d = d.astimezone(IST)
        return d
    except:
        return None

st.title("Simple Ping Monitor")

try:
    gc = auth()
except Exception as e:
    st.error("Auth failed. Ensure credentials are available and the sheet is shared with the service account.")
    st.stop()

df_users = read_df(gc, USERS_SHEET)
users = {}
if not df_users.empty:
    df_users.columns = [c.strip() for c in df_users.columns]
    for _, r in df_users.iterrows():
        users[str(r.get("Username","")).strip()] = str(r.get("Password","")).strip()

st.sidebar.header("Login")
u = st.sidebar.text_input("Username")
p = st.sidebar.text_input("Password", type="password")
if not (u in users and users[u]==p):
    st.info("Sign in with Users sheet credentials")
    st.stop()

df = read_df(gc, CHECK_SHEET)
if df.empty:
    st.warning("No data in ServerCheck")
    st.stop()

df.columns = [c.strip() for c in df.columns]
df['TS_parsed'] = df['Timestamp'].apply(parse_ts)
df = df.dropna(subset=['TS_parsed']).sort_values('TS_parsed')

latest = df.groupby(['Centre','Server Name']).last().reset_index()
centres = sorted(latest['Centre'].unique())
sel = st.selectbox("Centre", centres)
row = latest[(latest['Centre']==sel) & (latest['Server Name']=="Main Server")]
if row.empty:
    st.warning("No Main Server for this centre")
else:
    r = row.iloc[0]
    st.subheader(f"{sel} — Main Server")
    st.write("**Status:**", r.get('Status','N/A'))
    st.write("**IP:**", r.get('Server IP','N/A'))
    st.write("**Ping (ms):**", r.get('ResponseTime(ms)','N/A'))
    ts = r['TS_parsed']
    st.write("**Last check (IST):**", ts.strftime("%Y-%m-%d %H:%M:%S") if ts else "N/A")

    hist = df[(df['Centre']==sel) & (df['Server Name']=="Main Server")][['TS_parsed','Status']]
    consec = 0
    last_offline = None
    for _,h in hist.iterrows():
        if str(h['Status']).lower() in ('failed','fail','down','offline'):
            consec += 1
            if consec >= FAIL_THRESHOLD:
                last_offline = h['TS_parsed']
        else:
            consec = 0
    st.write("**Last Offline (threshold 5):**", last_offline.strftime("%Y-%m-%d %H:%M:%S") if last_offline else "None")
