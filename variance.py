import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection

st.set_page_config(page_title="Google Sheets Form", page_icon="📝", layout="centered")

st.title("📝 Data Entry Form")

# Create connection to Google Sheets (using secrets in Streamlit Cloud)
conn = st.connection("gsheets", type=GSheetsConnection)

# Your Google Sheet URL
sheet_url = "https://docs.google.com/spreadsheets/d/1MK5WDETIFCRes-c8X16JjrNdrlEpHwv9vHvb96VVtM0/edit?gid=0#gid=0"

# Read the current data (if any)
existing_data = conn.read(spreadsheet=sheet_url, worksheet="Sheet1")
if existing_data is None or existing_data.empty:
    existing_data = pd.DataFrame(columns=["Name", "Email", "Age", "Feedback"])

# Streamlit form for user input
with st.form("data_entry_form"):
    st.subheader("Fill in your details 👇")

    name = st.text_input("Name")
    email = st.text_input("Email")
    age = st.number_input("Age", min_value=0, step=1)
    feedback = st.text_area("Feedback")

    submitted = st.form_submit_button("Submit")

    if submitted:
        if name and email:
            # Add new row
            new_row = pd.DataFrame([[name, email, age, feedback]], columns=existing_data.columns)
            updated_data = pd.concat([existing_data, new_row], ignore_index=True)

            # Update Google Sheet
            conn.update(spreadsheet=sheet_url, worksheet="Sheet1", data=updated_data)
            st.success("✅ Data submitted successfully!")
        else:
            st.warning("⚠️ Please fill in all required fields (Name and Email).")

# Display existing records
st.divider()
st.subheader("📊 Submitted Entries")
st.dataframe(existing_data)
