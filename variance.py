import streamlit as st
import pandas as pd
from datetime import datetime
import gspread 
from google.oauth2.service_account import Credentials 

# ==========================================
# PAGE CONFIG
# ==========================================
st.set_page_config(page_title="Outlet & Feedback Dashboard", layout="wide")

# ==========================================
# GOOGLE SHEETS SETUP
# ==========================================
# 1. Configuration - REPLACE WITH YOUR SHEET URL
SHEET_URL = "https://docs.google.com/spreadsheets/d/1MK5WDETIFCRes-c8X16JjrNdrlEpHwv9vHvb96VVtM0/edit?gid=0#gid=0"
ITEMS_SHEET_NAME = "Items"
FEEDBACK_SHEET_NAME = "Feedback"

# 2. Authorization
try:
    scope = ["https://spreadsheets.google.com/feeds",
             "https://www.googleapis.com/auth/drive"]

    # Load credentials from Streamlit Secrets (same as your first app)
    creds = Credentials.from_service_account_info(
        st.secrets["google_service_account"], scopes=scope
    )

    # Authorize client and open the spreadsheet
    client = gspread.authorize(creds)
    sh = client.open_by_url(SHEET_URL)
    items_worksheet = sh.worksheet(ITEMS_SHEET_NAME) # Target for Outlet Dashboard data
    feedback_worksheet = sh.worksheet(FEEDBACK_SHEET_NAME) # Target for Feedback data
    
    # Flag for successful connection
    sheets_connected = True
except Exception as e:
    # Use a warning instead of a hard error to allow the UI to load for testing, 
    # but submission won't work.
    st.warning(f"⚠️ Google Sheets Connection Issue: Ensure 'google_service_account' is set up. Submissions are disabled. Error: {e}")
    sheets_connected = False

# ==========================================
# CUSTOM STYLES (MODIFIED for Emoji Rating - Tick Under Emoji)
# ==========================================
CUSTOM_RATING_CSS = """
<style>
/* --- Original Item Entry Form CSS (Preserved) --- */
/* Target the div that contains the radio buttons */
div[data-testid="stForm"] > div > div:nth-child(4) > div > div > div > div:nth-child(3) > div {
    display: flex; /* Makes the rating options sit in a row */
    justify-content: space-around;
    align-items: center;
    padding: 10px 0;
}

/* Style for each individual rating box */
div[data-testid="stForm"] > div > div:nth-child(4) div[role="radiogroup"] label {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    width: 40px; 
    height: 40px; 
    border: 1px solid #ccc;
    border-radius: 4px;
    margin: 5px;
    cursor: pointer;
    transition: background-color 0.2s, border-color 0.2s;
    user-select: none;
}

/* Style for the text inside the box (the number) */
div[data-testid="stForm"] > div > div:nth-child(4) div[role="radiogroup"] label > div {
    font-size: 16px;
    font-weight: bold;
    color: #333;
}

/* Style when the radio button is checked (the green effect) */
div[data-testid="stForm"] > div > div:nth-child(4) div[role="radiogroup"] label input:checked + div {
    background-color: #38C172 !important; /* Green background */
    border-color: #38C172 !important; /* Green border */
    color: white !important; /* White text */
}

/* Hides the default Streamlit radio circle */
div[data-testid="stForm"] > div > div:nth-child(4) div[role="radiogroup"] label input {
    display: none;
}

/* To ensure the green background applies correctly, we need to target the internal div Streamlit uses */
div[data-testid="stForm"] > div > div:nth-child(4) div[role="radiogroup"] label input:checked + div {
    background-color: #38C172 !important;
}

/* This targets the actual box content div */
div[data-testid="stForm"] > div > div:nth-child(4) div[role="radiogroup"] label > div:nth-child(2) > div {
    padding: 0;
    margin: 0;
}


/* --- NEW EMOJI FEEDBACK STYLING (HIGHLY LOCALIZED) --- */

/* This selector targets the st.radio group ONLY in the Customer Feedback form (the second form block on the page) */
/* It ensures the styling is limited to the emoji buttons. */
div[data-testid="stForm"]:nth-of-type(2) div[role="radiogroup"] label {
    width: 50px; /* Make boxes slightly bigger for emojis */
    height: 50px;
    border-radius: 8px; 
    position: relative;
    padding: 0;
    margin: 5px;
}

/* The emoji itself inside the button */
div[data-testid="stForm"]:nth-of-type(2) div[role="radiogroup"] label > div > div > div {
    font-size: 30px !important; 
}

/* Style when the emoji button is checked (Light green background/border) */
div[data-testid="stForm"]:nth-of-type(2) div[role="radiogroup"] label:has(input:checked) {
    background-color: #e0ffe0; /* Light green background when selected */
    border-color: #38C172; /* Green border when selected */
}

/* The Checkmark Tick (Now positioned centered under the emoji) */
div[data-testid="stForm"]:nth-of-type(2) div[role="radiogroup"] label input:checked + div::after {
    content: '✅'; /* Checkmark emoji */
    position: absolute;
    bottom: -10px; /* Position it below the emoji box */
    left: 50%; /* Center horizontally */
    transform: translateX(-50%); /* Adjust for its own width to truly center */
    font-size: 16px;
    background-color: white;
    border-radius: 50%;
    padding: 2px;
    box-shadow: 0 0 5px rgba(0,0,0,0.2);
}

</style>
"""
# ==========================================
# CUSTOM JAVASCRIPT/HTML TO FORCE NUMERIC KEYBOARD (Existing)
# ==========================================
def inject_numeric_keyboard_script(target_label):
    """
    Injects JavaScript to find the text input widget by its label and set
    its HTML 'inputmode' attribute to 'numeric', triggering the number keyboard on mobile.
    """
    script = f"""
    <script>
        function setInputMode() {{
            const elements = document.querySelectorAll('label');
            elements.forEach(label => {{
                if (label.textContent.includes('{target_label}')) {{
                    const input = label.nextElementSibling.querySelector('input');
                    if (input) {{
                        input.setAttribute('inputmode', 'numeric');
                        input.setAttribute('pattern', '[0-9]*');
                    }}
                }}
            }});
        }}
        // Run on load and whenever Streamlit rerenders the component (e.g., after a form submit)
        window.onload = setInputMode;
        // Also observe for changes in the DOM (needed for dynamic Streamlit content)
        new MutationObserver(setInputMode).observe(document.body, {{ childList: true, subtree: true }});
    </script>
    """
    st.markdown(script, unsafe_allow_html=True)

# ==========================================
# LOAD ITEM DATA (for auto-fill) (Existing)
# ==========================================
@st.cache_data
def load_item_data():
    # NOTE: The actual file "alllist.xlsx" must be present in the directory 
    file_path = "ItemSearchList_31102025_1159 (1).xlsx" 
    try:
        df = pd.read_excel(file_path)
        # Ensure column names are clean
        df.columns = df.columns.str.strip()
        
        # Check only critical columns needed for the app to run
        required_cols = ["Item Bar Code", "Item Name", "LP Supplier"] 
        for col in required_cols:
