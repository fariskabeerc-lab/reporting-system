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
# GOOGLE SHEETS SETUP (NEW Section)
# ==========================================
# 1. Configuration - REPLACE WITH YOUR SHEET URL
SHEET_URL = "https://docs.google.com/spreadsheets/d/1MK5WDETIFCRes-c8X16JjrNdrlEpHwv9vHvb96VVtM0/edit?gid=1883887055#gid=1883887055"
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
    st.error(f"⚠️ Google Sheets Connection Error: Ensure your 'google_service_account' is correct and the sheet URL is valid. Error: {e}")
    sheets_connected = False

# ==========================================
# CUSTOM STYLES (Existing - Removed custom radio CSS for cleaner st.feedback)
# ==========================================
# NOTE: The CUSTOM_RATING_CSS is now defined but will not be used 
# when st.feedback is implemented, but kept here for reference if you switch back.
CUSTOM_RATING_CSS = """
<style>
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
    user-select: none; /* Prevents text selection on tap */
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

/* Apply the checked style to the parent label div */
div[data-testid="stForm"] > div > div:nth-child(4) div[role="radiogroup"] label input:checked {
    /* This rule is complex in Streamlit's shadow DOM. We rely on the checked + div selector above. */
}

/* To ensure the green background applies correctly, we need to target the internal div Streamlit uses */
div[data-testid="stForm"] > div > div:nth-child(4) div[role="radiogroup"] label input:checked + div {
    /* Streamlit structure is complex, this targets the inner container of the radio button. */
    background-color: #38C172 !important;
}

/* This targets the actual box content div */
div[data-testid="stForm"] > div > div:nth-child(4) div[role="radiogroup"] label > div:nth-child(2) > div {
    padding: 0;
    margin: 0;
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
                        // Use 'tel' inputmode for better mobile experience for phone numbers
                        input.setAttribute('inputmode', 'tel'); 
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
    file_path = "alllist.xlsx" 
    try:
        df = pd.read_excel(file_path)
        # Ensure column names are clean
        df.columns = df.columns.str.strip()
        
        # Check only critical columns needed for the app to run
        required_cols = ["Item Bar Code", "Item Name", "LP Supplier"] 
        for col in required_cols:
            if col not in df.columns:
                st.error(f"⚠️ Missing critical column: '{col}' in alllist.xlsx. Please check the file.")
                return pd.DataFrame()
        return df
    except FileNotFoundError:
        st.error(f"⚠️ Data file not found: {file_path}. Please ensure the file is in the application directory.")
    except Exception as e:
        st.error(f"⚠️ Error loading alllist.xlsx: {e}")
    return pd.DataFrame()

item_data = load_item_data()

# ==========================================
# LOGIN SYSTEM (Existing)
# ==========================================
outlets = [
    "Hilal", "Safa Super", "Azhar HP", "Azhar", "Blue Pearl", "Fida", "Hadeqat",
    "Jais", "Sabah", "Sahat", "Shams salem", "Shams Liwan", "Superstore",
    "Tay Tay", "Safa oudmehta", "Port saeed"
]
password = "123123"

# Initialize session state variables (Existing)
for key in ["logged_in", "selected_outlet", "submitted_items",
             "barcode_value", "item_name_input", "supplier_input", 
             "temp_item_name_manual", "temp_supplier_manual",
             "lookup_data", "submitted_feedback", "barcode_found",
             "staff_name"]: 
    
    if key not in st.session_state:
        if key in ["submitted_items", "submitted_feedback"]:
            st.session_state[key] = []
        elif key == "lookup_data":
            st.session_state[key] = pd.DataFrame()
        elif key == "barcode_found":
            st.session_state[key] = False 
        else:
            st.session_state[key] = ""

# --- Helper functions to synchronize manual inputs --- (Existing)
def update_item_name_state():
    """Updates the main item_name_input state variable from the temp manual input."""
    st.session_state.item_name_input = st.session_state.temp_item_name_manual

def update_supplier_state():
    """Updates the main supplier_input state variable from the temp manual input."""
    st.session_state.supplier_input = st.session_state.temp_supplier_manual
# ------------------------------------------------------------------

# --- Lookup Logic Function (Callback for Barcode Form) --- (Existing)
def lookup_item_and_update_state():
    """Performs the barcode lookup and updates relevant session state variables."""
    # (Function logic remains the same)
    barcode = st.session_state.lookup_barcode_input
    
    # Reset lookup and previous item states
    st.session_state.lookup_data = pd.DataFrame()
    st.session_state.barcode_value = barcode 
    st.session_state.item_name_input = ""
    st.session_state.supplier_input = ""
    st.session_state.barcode_found = False
    
    # Reset temporary keys for manual entry fields
    st.session_state.temp_item_name_manual = ""
    st.session_state.temp_supplier_manual = "" 
    
    if not barcode:
        st.toast("⚠️ Barcode cleared.", icon="❌")
        return

    if not item_data.empty:
        match = item_data[item_data["Item Bar Code"].astype(str).str.strip() == str(barcode).strip()]
        
        if not match.empty:
            st.session_state.barcode_found = True
            row = match.iloc[0]
            
            # 1. Prepare data for display table
            df_display = row[["Item Name", "LP Supplier"]].to_frame().T
            df_display.columns = ["Item Name", "Supplier"]
            st.session_state.lookup_data = df_display.reset_index(drop=True)
            
            # 2. Automatically transfer details to the main state variables
            st.session_state.item_name_input = str(row["Item Name"])
            st.session_state.supplier_input = str(row["LP Supplier"])
            
            st.toast("✅ Item found. Details loaded.", icon="🔍")
        else:
            # Barcode not found 
            st.session_state.barcode_found = False 
            st.toast("⚠️ Barcode not found. Please enter item name and supplier manually.", icon="⚠️")
# ------------------------------------------------------------------

# -------------------------------------------------
# --- Main Form Submission Handler (Modified to just collect data) ---
# -------------------------------------------------
def process_item_entry(barcode, item_name, qty, cost, selling, expiry, supplier, remarks, form_type, outlet_name, staff_name):
    
    # Validation (Remains the same)
    if not barcode.strip():
        st.toast("⚠️ Barcode is required before adding.", icon="❌")
        return False
    if not item_name.strip():
        st.toast("⚠️ Item Name is required before adding.", icon="❌")
        return False
    if not staff_name.strip():
        st.toast("⚠️ Staff Name is required before adding.", icon="❌")
        return False

    try:
        cost = float(cost)
    except ValueError:
        cost = 0.0
    try:
        selling = float(selling)
    except ValueError:
        selling = 0.0

    expiry_display = expiry.strftime("%d-%b-%y") if expiry else ""
    gp = ((selling - cost) / cost * 100) if cost else 0

    st.session_state.submitted_items.append({
        "Date Submitted": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), 
        "Form Type": form_type,
        "Barcode": barcode.strip(),
        "Item Name": item_name.strip(),
        "Qty": qty,
        "Cost": round(cost, 2),
        "Selling": round(selling, 2),
        "Amount": round(cost * qty, 2),
        "GP%": round(gp, 2),
        "Expiry": expiry_display,
        "Supplier": supplier.strip(),
        "Remarks": remarks.strip(),
        "Outlet": outlet_name,
        "Staff Name": staff_name.strip() 
    })

    # --- CLEAR ONLY THE NON-FORM/NON-ITEM STATE VARIABLES ---
    st.session_state.barcode_value = ""          
    st.session_state.lookup_data = pd.DataFrame()
    st.session_state.barcode_found = False
    
    st.toast("✅ Added to list successfully!", icon="➕")
    return True
# -------------------------------------------------


# -------------------------------------------------
# --- Function to Submit ALL Collected Data to Google Sheets ---
# -------------------------------------------------
def submit_all_items_to_sheets():
    """Takes all items in session_state and appends them to the Items Google Sheet."""
    if not sheets_connected:
        st.error("Cannot submit: Google Sheets not connected.")
        return

    df_to_upload = pd.DataFrame(st.session_state.submitted_items)
    
    # Prepare data rows for gspread
    headers = list(df_to_upload.columns)
    
    try:
        current_headers = items_worksheet.row_values(1)
        if not current_headers:
             items_worksheet.append_row(headers)
    except Exception as e:
        st.error(f"Error checking/writing headers to '{ITEMS_SHEET_NAME}': {e}")
        return

    # Convert DataFrame to a list of lists (rows)
    data_rows = df_to_upload.values.tolist()
    
    try:
        # Append all rows at once for efficiency
        items_worksheet.append_rows(data_rows) 
        st.success(f"✅ Successfully submitted {len(st.session_state.submitted_items)} items to Google Sheet: '{ITEMS_SHEET_NAME}'!")
        return True
    except Exception as e:
        st.error(f"❌ Error submitting items to Google Sheet: {e}")
        return False
# -------------------------------------------------

# -------------------------------------------------
# --- Function to Submit Single Feedback to Google Sheets ---
# -------------------------------------------------
def submit_feedback_to_sheets(feedback_entry):
    """Appends a single feedback entry (dictionary) to the Feedback Google Sheet."""
    if not sheets_connected:
        st.error("Cannot submit: Google Sheets not connected.")
        return False
        
    # Get header row (in the order you want)
    headers = list(feedback_entry.keys())
    
    # Check if headers exist in the sheet
    try:
        current_headers = feedback_worksheet.row_values(1)
        if not current_headers:
             feedback_worksheet.append_row(headers)
    except Exception as e:
        st.error(f"Error checking/writing headers to '{FEEDBACK_SHEET_NAME}': {e}")
        return False

    # Get values in the order of the keys (headers)
    data_row = list(feedback_entry.values())
    
    try:
        # Append the single row
        feedback_worksheet.append_row(data_row) 
        return True
    except Exception as e:
        st.error(f"❌ Error submitting feedback to Google Sheet: {e}")
        return False
# -------------------------------------------------


# ==========================================
# PAGE SELECTION (Existing)
# ==========================================
if not st.session_state.logged_in:
    st.title("🔐 Outlet Login")
    username = st.text_input("Username", placeholder="Enter username")
    outlet = st.selectbox("Select your outlet", outlets)
    pwd = st.text_input("Password", type="password")

    if st.button("Login"):
        if username == "almadina" and pwd == password:
            st.session_state.logged_in = True
            st.session_state.selected_outlet = outlet
            st.rerun()
        else:
            st.error("❌ Invalid username or password")

else:
    # NOTE: The CUSTOM_RATING_CSS is no longer necessary but is commented out
    # to show that the new widget is used.
    # st.markdown(CUSTOM_RATING_CSS, unsafe_allow_html=True) 
    
    page = st.sidebar.radio("📌 Select Page", ["Outlet Dashboard", "Customer Feedback"])

    # ==========================================
    # OUTLET DASHBOARD
    # ==========================================
    if page == "Outlet Dashboard":
        outlet_name = st.session_state.selected_outlet
        st.markdown(f"<h2 style='text-align:center;'>🏪 {outlet_name} Dashboard</h2>", unsafe_allow_html=True)
        form_type = st.sidebar.radio("📋 Select Form Type", ["Expiry", "Damages", "Near Expiry"])
        st.markdown("---")
        
        # Inject the script to change the barcode field's inputmode
        inject_numeric_keyboard_script("Barcode Lookup")


        # --- 0. Staff Name Input --- (Existing)
        st.session_state.staff_name = st.text_input(
            "👤 Staff Name (Required)",
            value=st.session_state.staff_name,
            key="staff_name_input_key", 
            placeholder="Enter your full name"
        )
        st.markdown("---")

        # --- 1. Dedicated Lookup Form (Existing) ---
        with st.form("barcode_lookup_form", clear_on_submit=False):
            
            col_bar, col_btn = st.columns([5, 1])
            
            with col_bar:
                st.text_input(
                    "Barcode Lookup",
                    key="lookup_barcode_input", 
                    placeholder="Enter or scan barcode and press Enter to search details",
                    value=st.session_state.barcode_value
                )
            
            with col_btn:
                st.markdown("<div style='height: 33px;'></div>", unsafe_allow_html=True) # Spacer
                st.form_submit_button(
                    "🔍 Search", 
                    on_click=lookup_item_and_update_state, 
                    help="Click or press Enter in the barcode field to look up item.",
                    type="secondary",
                    use_container_width=True
                )

        # --- 2. Item Details Display Panel (Existing) ---
        if not st.session_state.lookup_data.empty:
            st.markdown("### 🔍 Found Item Details")
            st.dataframe(st.session_state.lookup_data, use_container_width=True, hide_index=True)
        
        # --- 2b. Manual Entry Fallback (Existing) ---
        if st.session_state.barcode_value.strip() and not st.session_state.barcode_found:
             st.markdown("### ⚠️ Manual Item Entry (Barcode Not Found)")
             col_manual_name, col_manual_supplier = st.columns(2)
             with col_manual_name:
                 st.text_input(
                     "Item Name (Manual)", 
                     value=st.session_state.item_name_input, 
                     key="temp_item_name_manual", 
                     on_change=update_item_name_state
                 )
             with col_manual_supplier:
                 st.text_input(
                     "Supplier Name (Manual)", 
                     value=st.session_state.supplier_input, 
                     key="temp_supplier_manual", 
                     on_change=update_supplier_state
                 )

        if st.session_state.barcode_value.strip():
             st.markdown("---") 


        # --- 3. Start of the Main Item Entry Form (Existing) ---
        with st.form("item_entry_form", clear_on_submit=True): 
            
            # --- Row 1: Qty and Expiry ---
            col1, col2 = st.columns(2)
            with col1:
                qty = st.number_input("Qty [PCS]", min_value=1, value=1, step=1)
            with col2:
                if form_type != "Damages":
                    expiry = st.date_input("Expiry Date", datetime.now().date())
                else:
                    expiry = None

            # --- Row 2: Cost, Selling ---
            col5, col6 = st.columns(2)
            with col5:
                cost = st.number_input("Cost", min_value=0.0, value=0.0, step=0.01)
            with col6:
                selling = st.number_input("Selling Price", min_value=0.0, value=0.0, step=0.01)

            # Calculate and display GP%
            temp_cost = float(cost)
            temp_selling = float(selling)
                
            gp = ((temp_selling - temp_cost) / temp_cost * 100) if temp_cost else 0
            st.info(f"💹 **GP% (Profit Margin)**: {gp:.2f}%")

            # --- Remarks and Submit Button ---
            remarks = st.text_area("Remarks [if any]", value="")

            submitted_item = st.form_submit_button(
                "➕ Add to List", 
                type="primary",
            )
            # --- End of the Item Entry Form ---

        # --- Handle Main Form Submission ONLY on Button Click (Existing) ---
        if submitted_item:
            
            final_item_name = st.session_state.item_name_input
            final_supplier = st.session_state.supplier_input
            final_staff_name = st.session_state.staff_name 

            if not st.session_state.barcode_value.strip():
                 st.toast("❌ Please enter a Barcode before adding to the list.", icon="❌")
                 st.rerun() 
            
            if not final_staff_name.strip():
                st.toast("❌ Please enter your Staff Name before adding to the list.", icon="❌")
                st.rerun()

            success = process_item_entry(
                st.session_state.barcode_value, 
                final_item_name,             
                qty,         
                cost,    
                selling, 
                expiry,      
                final_supplier,              
                remarks,     
                form_type,   
                outlet_name,
                final_staff_name 
            )
            
            if success:
                 st.rerun()


        # Displaying and managing the list
        if st.session_state.submitted_items:
            st.markdown("### 🧾 Items Added")
            df = pd.DataFrame(st.session_state.submitted_items)
            st.dataframe(df, use_container_width=True, hide_index=True)

            col_submit, col_delete = st.columns([1, 1])
            with col_submit:
                if st.button("📤 Submit All to Google Sheets", type="primary"): 
                    if submit_all_items_to_sheets(): 
                        # FINAL RESET OF ITEM LOOKUP DATA AND STAFF NAME
                        st.session_state.submitted_items = []
                        st.session_state.barcode_value = ""
                        st.session_state.item_name_input = ""
                        st.session_state.supplier_input = ""
                        st.session_state.barcode_found = False
                        st.session_state.temp_item_name_manual = "" 
                        st.session_state.temp_supplier_manual = "" 
                        st.session_state.lookup_data = pd.DataFrame() 
                        st.session_state.staff_name = "" 
                        st.rerun() 

            with col_delete:
                options = [f"{i+1}. {item['Item Name']} ({item['Qty']} pcs)" for i, item in enumerate(st.session_state.submitted_items)]
                if options:
                    to_delete = st.selectbox("Select Item to Delete", ["Select item to remove..."] + options)
                    if to_delete != "Select item to remove...":
                        if st.button("❌ Delete Selected", type="secondary"):
                            index = options.index(to_delete) 
                            st.session_state.submitted_items.pop(index)
                            st.success("✅ Item removed")
                            st.rerun()

    
    # ==========================================
    # CUSTOMER FEEDBACK PAGE (MODIFIED: Rating Widget and Submission)
    # ==========================================
    else:
        outlet_name = st.session_state.selected_outlet
        st.title("📝 Kindly rate your shopping experience with us")
        st.markdown(f"Submitting feedback for **{outlet_name}**")
        st.markdown("---")
        
        # Inject the script to change the mobile number field's inputmode
        inject_numeric_keyboard_script("Mobile Number") 

        with st.form("feedback_form", clear_on_submit=True):
            name = st.text_input("Customer Name")
            mobile_number = st.text_input("Mobile Number (Optional)", placeholder="e.g., +971501234567")
            
            st.markdown("🌟 **Rate Our Outlet**")
            
            # --- MODIFIED: Using st.feedback for a cleaner, official star rating ---
            # st.feedback returns 0 for 1-star, 1 for 2-stars, ..., 4 for 5-stars.
            st.feedback(
                options="stars", 
                key="customer_rating_stars", 
                # Optional: set an initial value (e.g., to 5 stars, which is 4 for the widget)
                # This needs to be done via key/session state for clear_on_submit=True forms
            )
            
            feedback = st.text_area("Your Feedback (Required)")
            submitted = st.form_submit_button("📤 Submit Feedback")

        if submitted:
            # 1. Retrieve the raw value (0-4) from session state
            submitted_raw_rating = st.session_state.customer_rating_stars
            
            # 2. Convert raw rating (0-4) to final integer rating (1-5)
            # If the user didn't select a rating (it returns None), default to 5
            final_rating_value = (submitted_raw_rating + 1) if submitted_raw_rating is not None else 5
            
            if name.strip() and feedback.strip():
                new_feedback_entry = {
                    "Customer Name": name,
                    "Mobile Number": mobile_number if mobile_number.strip() else "N/A",  
                    # --- MODIFIED: Storing the final integer (1-5) ---
                    "Rating": final_rating_value,
                    "Outlet": outlet_name,
                    "Feedback": feedback,
                    "Submitted At": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
                
                # Submit to Google Sheet
                if submit_feedback_to_sheets(new_feedback_entry):
                    st.session_state.submitted_feedback.append(new_feedback_entry)
                    st.success("✅ Feedback submitted successfully to Google Sheets! The form has been cleared.")
            else:
                st.error("⚠️ Please fill **Customer Name** and **Feedback** before submitting.")
