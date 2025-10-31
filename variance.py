import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

st.set_page_config(page_title="Google Sheets Form", page_icon="📝", layout="centered")
st.title("📝 Data Entry Form")

# ---- Google Sheets Setup ----
SHEET_URL = "https://docs.google.com/spreadsheets/d/1MK5WDETIFCRes-c8X16JjrNdrlEpHwv9vHvb96VVtM0/edit?gid=0"

# Define scope for Google Sheets & Drive
scope = ["https://spreadsheets.google.com/feeds",
         "https://www.googleapis.com/auth/drive"]

# Load credentials from Streamlit Secrets
creds = Credentials.from_service_account_info(
    st.secrets["google_service_account"], scopes=scope
)

# Authorize client
client = gspread.authorize(creds)
sh = client.open_by_url(SHEET_URL)
worksheet = sh.worksheet("Sheet1")  # Use the sheet/tab name “streamli”

# ---- Read existing data ----
data = pd.DataFrame(worksheet.get_all_records())

# ---- Streamlit form ----
with st.form("entry_form"):
    st.subheader("Enter your details 👇")

    name = st.text_input("Name")
    email = st.text_input("Email")
    age = st.number_input("Age", min_value=0, step=1)
    feedback = st.text_area("Feedback")

    submitted = st.form_submit_button("Submit")

    if submitted:
        if name and email:
            # Add new row to Google Sheet
            worksheet.append_row([name, email, age, feedback])
            st.success("✅ Data submitted successfully!")
        else:
            st.warning("⚠️ Please fill in all required fields.")

# ---- Show data ----
st.divider()
st.subheader("📊 Existing Records")
st.dataframe(data)
