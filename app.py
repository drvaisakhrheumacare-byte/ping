import os
import json
import tempfile
import streamlit as st
import gspread

# Config
SHEET_URL = st.secrets.get("sheet_url", os.environ.get("SHEET_URL", "https://docs.google.com/spreadsheets/d/1uf4pqKHEAbw6ny7CVZZVMw23PTfmv0QZzdCyj4fU33c/edit"))

def ensure_credentials_file():
    """
    Ensure GOOGLE_APPLICATION_CREDENTIALS points to a valid JSON file.
    Priority:
      1. If env var GOOGLE_APPLICATION_CREDENTIALS points to an existing file, use it.
      2. If st.secrets['gcp_service_account'] exists, write it to a temp file and set env var.
      3. If credentials.json exists in repo root (local dev), use it (but .gitignore prevents committing).
    """
    env_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
    if env_path and os.path.isfile(env_path):
        return env_path

    # 2) Streamlit secret
    if "gcp_service_account" in st.secrets:
        json_text = st.secrets["gcp_service_account"]
        # write to a temp file
        fd, path = tempfile.mkstemp(prefix="gcp_creds_", suffix=".json")
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(json_text)
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = path
        return path

    # 3) Local credentials.json
    local_path = os.path.join(os.getcwd(), "credentials.json")
    if os.path.isfile(local_path):
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = local_path
        return local_path

    return None

def test_gs_access(creds_path):
    try:
        gc = gspread.service_account(filename=creds_path)
        sh = gc.open_by_url(SHEET_URL)
        worksheets = [ws.title for ws in sh.worksheets()]
        return True, sh.title, worksheets
    except Exception as e:
        return False, type(e).__name__ + ": " + str(e), None

def main():
    st.title("Server Logger - Auth Check")
    creds_path = ensure_credentials_file()
    if not creds_path:
        st.error("No credentials found. Locally place credentials.json or add the JSON to Streamlit secret 'gcp_service_account'.")
        st.stop()

    st.info(f"Using credentials file: {creds_path}")
    ok, info, worksheets = test_gs_access(creds_path)
    if ok:
        st.success(f"Opened spreadsheet: {info}")
        st.write("Worksheets:", worksheets)
    else:
        st.error("Auth failed. See details below.")
        st.code(info)

if __name__ == "__main__":
    main()
