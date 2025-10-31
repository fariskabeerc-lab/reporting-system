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
SHEET_URL = "https://docs.google.com/spreadsheets/d/1MK5WDETIFCRes-c8X16JjrNdrlEpHwv9vHvb96VVtM0/edit?gid=1883887055#gid=1883887055"
ITEMS_SHEET_NAME = "Items"
FEEDBACK_SHEET_NAME = "Feedback"

# 2. Authorization
try:
    scope = ["https://spreadsheets.google.com/feeds",
             "https://www.googleapis.com/auth/drive"]

    # Load credentials from Streamlit Secrets 
    creds = Credentials.from_service_account_info(
        st.secrets["google_service_account"], scopes=scope
    )

    # Authorize client and open the spreadsheet
    client = gspread.authorize(creds)
    sh = client.open_by_url(SHEET_URL)
    items_worksheet = sh.worksheet(ITEMS_SHEET_NAME) 
    feedback_worksheet = sh.worksheet(FEEDBACK_SHEET_NAME) 
    
    # Flag for successful connection
    sheets_connected = True
except Exception as e:
    # Changed to st.sidebar.error to keep the main app visible if possible
    st.sidebar.error(f"⚠️ Google Sheets Connection Error: Error: {e}")
    sheets_connected = False

# ==========================================
# CUSTOM STYLES (Existing)
# ==========================================
# ... (CUSTOM_RATING_CSS remains the same) ...
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

/* This targets the actual box content div */
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
# LOAD ITEM DATA (for auto-fill) (MODIFIED FOR EXCEL ERROR AND UNIT/CF)
# ==========================================
@st.cache_data
def load_item_data():
    # NOTE: The actual file "alllist.xlsx" must be present in the directory 
    file_path = "alllist(1).Xlsx" 
    try:
        # **FIX:** Specify the engine for .xlsx format to resolve the error
        df = pd.read_excel(file_path, engine='openpyxl') 
        
        # Ensure column names are clean
        df.columns = df.columns.str.strip()
        
        # Check all critical columns needed for the app to run (ADDED Unit and CF)
        required_cols = ["Item Bar Code", "Item Name", "LP Supplier", "Unit", "CF"] 
        for col in required_cols:
            if col not in df.columns:
                st.error(f"⚠️ Missing critical column: '{col}' in {file_path}. Please check the file.")
                return pd.DataFrame()
        return df
    except FileNotFoundError:
        st.error(f"⚠️ Data file not found: {file_path}. Please ensure the file is in the application directory.")
    except Exception as e:
           st.error(f"⚠️ Error loading {file_path}: Please ensure the file is a valid .xlsx file and 'openpyxl' is installed. Error: {e}")
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

# Initialize session state variables (MODIFIED: Added unit and cf state variables)
for key in ["logged_in", "selected_outlet", "submitted_items",
            "barcode_value", "item_name_input", "supplier_input", 
            "unit_input", "cf_input", # <--- NEW state variables for storing lookup results
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


# --- Lookup Logic Function (Callback for Barcode Form) --- (MODIFIED for Unit/CF)
def lookup_item_and_update_state():
    """Performs the barcode lookup and updates relevant session state variables."""
    barcode = st.session_state.lookup_barcode_input
    
    # Reset lookup and previous item states
    st.session_state.lookup_data = pd.DataFrame()
    st.session_state.barcode_value = barcode 
    st.session_state.item_name_input = ""
    st.session_state.supplier_input = ""
    st.session_state.unit_input = "" # <--- Reset NEW state
    st.session_state.cf_input = ""   # <--- Reset NEW state
    st.session_state.barcode_found = False
    
    if not barcode:
        st.toast("⚠️ Barcode cleared.", icon="❌")
        return

    if not item_data.empty:
        # Match using string comparison on stripped values
        match = item_data[item_data["Item Bar Code"].astype(str).str.strip() == str(barcode).strip()] 
        
        if not match.empty:
            st.session_state.barcode_found = True
            row = match.iloc[0]
            
            # 1. Prepare data for display table (ADDED Unit and CF)
            df_display = row[["Item Name", "LP Supplier", "Unit", "CF"]].to_frame().T
            df_display.columns = ["Item Name", "Supplier", "Unit", "CF"] # Updated column names for display
            st.session_state.lookup_data = df_display.reset_index(drop=True)
            
            # 2. Automatically transfer details to the main state variables (ADDED Unit and CF)
            st.session_state.item_name_input = str(row["Item Name"])
            st.session_state.supplier_input = str(row["LP Supplier"])
            # Use a default of 1.0 for CF if it's missing/invalid, to prevent errors in number_input
            try:
                cf_val = float(row["CF"]) 
            except (ValueError, TypeError, KeyError): # Added KeyError for safety
                cf_val = 1.0
                
            st.session_state.unit_input = str(row["Unit"])  # <--- Set NEW state
            st.session_state.cf_input = str(cf_val)         # <--- Set NEW state (as string for consistency)
            
            st.toast("✅ Item found. Details loaded.", icon="🔍")
        else:
            # Barcode not found 
            st.session_state.barcode_found = False 
            st.toast("⚠️ Barcode not found. Enter details manually.", icon="⚠️")
# ------------------------------------------------------------------

# -------------------------------------------------
# --- Main Form Submission Handler (MODIFIED: Added unit and cf) ---
# -------------------------------------------------
def process_item_entry(barcode, item_name, qty, cost, selling, expiry, supplier, unit, cf, remarks, form_type, outlet_name, staff_name):
    
    # Validation (ADD Unit and CF checks)
    if not barcode.strip():
        st.toast("⚠️ Barcode is required before adding.", icon="❌")
        return False
    if not item_name.strip():
        st.toast("⚠️ Item Name is required before adding.", icon="❌")
        return False
    if not staff_name.strip():
        st.toast("⚠️ Staff Name is required before adding.", icon="❌")
        return False
    # Unit is often a requirement for inventory systems
    if not unit.strip(): 
        st.toast("⚠️ Unit is required before adding.", icon="❌")
        return False
        
    try:
        cf_float = float(cf) 
    except ValueError:
        st.toast("⚠️ CF must be a valid number.", icon="❌")
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
        "Unit": unit.strip(), # <--- NEW field
        "CF": round(cf_float, 2), # <--- NEW field
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
    st.session_state.item_name_input = ""
    st.session_state.supplier_input = ""
    st.session_state.unit_input = ""
    st.session_state.cf_input = ""
    
    st.toast("✅ Added to list successfully!", icon="➕")
    return True
# -------------------------------------------------


# -------------------------------------------------
# --- Function to Submit ALL Collected Data to Google Sheets (Existing) ---
# -------------------------------------------------
def submit_all_items_to_sheets():
    # ... (Function body remains the same as provided) ...
    """Takes all items in session_state and appends them to the Items Google Sheet."""
    if not sheets_connected:
        st.error("Cannot submit: Google Sheets not connected.")
        return

    df_to_upload = pd.DataFrame(st.session_state.submitted_items)
    
    headers = list(df_to_upload.columns)
    
    try:
        current_headers = items_worksheet.row_values(1)
        if not current_headers:
             items_worksheet.append_row(headers)
    except Exception as e:
        st.error(f"Error checking/writing headers to '{ITEMS_SHEET_NAME}': {e}")
        return

    data_rows = df_to_upload.values.tolist()
    
    try:
        items_worksheet.append_rows(data_rows) 
        st.success(f"✅ Successfully submitted {len(st.session_state.submitted_items)} items to Google Sheet: '{ITEMS_SHEET_NAME}'!")
        return True
    except Exception as e:
        st.error(f"❌ Error submitting items to Google Sheet: {e}")
        return False
# -------------------------------------------------

# -------------------------------------------------
# --- Function to Submit Single Feedback to Google Sheets (Existing) ---
# -------------------------------------------------
def submit_feedback_to_sheets(feedback_entry):
    # ... (Function body remains the same as provided) ...
    """Appends a single feedback entry (dictionary) to the Feedback Google Sheet."""
    if not sheets_connected:
        st.error("Cannot submit: Google Sheets not connected.")
        return False
        
    headers = list(feedback_entry.keys())
    
    try:
        current_headers = feedback_worksheet.row_values(1)
        if not current_headers:
             feedback_worksheet.append_row(headers)
    except Exception as e:
        st.error(f"Error checking/writing headers to '{FEEDBACK_SHEET_NAME}': {e}")
        return False

    data_row = list(feedback_entry.values())
    
    try:
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
    # APPLY CUSTOM CSS FOR RATING BOXES HERE
    st.markdown(CUSTOM_RATING_CSS, unsafe_allow_html=True) 
    
    page = st.sidebar.radio("📌 Select Page", ["Outlet Dashboard", "Customer Feedback"])

    # ==========================================
    # OUTLET DASHBOARD (MODIFIED: Form and Logic)
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

        # --- 1. Dedicated Lookup Form ---
        with st.form("barcode_lookup_form", clear_on_submit=False):
            
            col_bar, col_btn = st.columns([5, 1])
            
            with col_bar:
                st.text_input(
                    "Barcode Lookup",
                    key="lookup_barcode_input", 
                    placeholder="Enter or scan barcode and press Enter to search details",
                    value=st.session_state.barcode_value # The value to display on load
                )
            
            with col_btn:
                st.markdown("<div style='height: 33px;'></div>", unsafe_allow_html=True) # Spacer
                st.form_submit_button(
                    "🔍 Search", 
                    on_click=lookup_item_and_update_state, # Calls the function to update state
                    help="Click or press Enter in the barcode field to look up item.",
                    type="secondary",
                    use_container_width=True
                )

        # --- 2. Item Details Display Panel (Display lookup success) ---
        if not st.session_state.lookup_data.empty:
            st.markdown("### 🔍 Found Item Details")
            st.dataframe(st.session_state.lookup_data, use_container_width=True, hide_index=True)
        
        # --- 2b. Manual Entry Fallback Alert (Simple alert replaces complex manual inputs) ---
        elif st.session_state.barcode_value.strip() and not st.session_state.barcode_found:
             st.warning("⚠️ Barcode not found. Please enter Item Name, Unit, Supplier, and CF manually in the form below.")


        if st.session_state.barcode_value.strip():
             st.markdown("---") 


        # --- 3. Start of the Main Item Entry Form (UPDATED to include Unit/CF inputs) ---
        with st.form("item_entry_form", clear_on_submit=True): 
            
            # --- Row A: Item Name, Supplier ---
            col_name, col_supplier = st.columns(2)
            with col_name:
                item_name_input = st.text_input(
                    "Item Name", 
                    value=st.session_state.item_name_input, # Auto-filled from lookup
                    key="item_name_final_input",
                    placeholder="Item Name (Required)"
                )
            with col_supplier:
                supplier_input = st.text_input(
                    "Supplier",
                    value=st.session_state.supplier_input, # Auto-filled from lookup
                    key="supplier_final_input",
                    placeholder="LP Supplier (Required)"
                )
                
            # --- Row B: Unit and CF ---
            col_unit, col_cf = st.columns(2) 
            with col_unit:
                unit_input = st.text_input(
                    "Unit", 
                    value=st.session_state.unit_input, # Auto-filled from lookup
                    key="unit_final_input",
                    placeholder="Unit (e.g., CASE, PKT)"
                )
            with col_cf:
                # Need to convert string CF back to float for st.number_input
                default_cf = float(st.session_state.cf_input) if st.session_state.cf_input else 1.0
                cf_input = st.number_input(
                    "CF (Conversion Factor)", 
                    min_value=1.0, 
                    value=default_cf,
                    step=1.0,
                    key="cf_final_input"
                )
            
            st.markdown("---")

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

        # --- Handle Main Form Submission ONLY on Button Click ---
        if submitted_item:
            
            # Since the form inputs were used, we capture their values directly from their keys
            final_unit = st.session_state.unit_final_input
            final_cf = st.session_state.cf_final_input
            final_item_name = st.session_state.item_name_final_input
            final_supplier = st.session_state.supplier_final_input
            final_staff_name = st.session_state.staff_name 
            
            if not st.session_state.barcode_value.strip():
                 st.toast("❌ Please search a Barcode first.", icon="❌")
                 st.rerun() 
            
            if not final_staff_name.strip():
                st.toast("❌ Please enter your Staff Name.", icon="❌")
                st.rerun()

            success = process_item_entry(
                st.session_state.barcode_value, 
                final_item_name,             
                qty,         
                cost,    
                selling, 
                expiry,      
                final_supplier,              
                final_unit, # <--- Unit passed
                final_cf,   # <--- CF passed
                remarks,     
                form_type,   
                outlet_name,
                final_staff_name 
            )
            
            if success:
                 # Rerun to clear the form and display the updated list
                 st.rerun()


        # Displaying and managing the list
        if st.session_state.submitted_items:
            st.markdown("### 🧾 Items Added")
            # Use columns in the display dataframe for consistency
            display_cols = ["Form Type", "Barcode", "Item Name", "Unit", "CF", "Qty", "Cost", "Selling", "GP%", "Expiry", "Supplier"]
            df = pd.DataFrame(st.session_state.submitted_items)[display_cols]
            st.dataframe(df, use_container_width=True, hide_index=True)

            col_submit, col_delete = st.columns([1, 1])
            with col_submit:
                if st.button("📤 Submit All to Google Sheets", type="primary"):
                    if submit_all_items_to_sheets(): 
                        # FINAL RESET
                        st.session_state.submitted_items = []
                        st.session_state.barcode_value = ""
                        st.session_state.item_name_input = ""
                        st.session_state.supplier_input = ""
                        st.session_state.unit_input = ""
                        st.session_state.cf_input = ""
                        st.session_state.barcode_found = False
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
    # CUSTOMER FEEDBACK PAGE (Existing)
    # ==========================================
    else:
        outlet_name = st.session_state.selected_outlet
        st.title("📝 Customer Feedback Form")
        st.markdown(f"Submitting feedback for **{outlet_name}**")
        st.markdown("---")

        with st.form("feedback_form", clear_on_submit=True):
            name = st.text_input("Customer Name")
            
            st.markdown("🌟 **Rate Our Outlet**")
            rating = st.radio(
                "hidden_rating_label", 
                options=[1, 2, 3, 4, 5],
                index=4, 
                horizontal=True, 
                key="customer_rating_radio",
                label_visibility="collapsed"
            )
            
            feedback = st.text_area("Your Feedback (Required)")
            submitted = st.form_submit_button("📤 Submit Feedback")

        if submitted:
            if name.strip() and feedback.strip():
                new_feedback_entry = {
                    "Customer Name": name,
                    "Email": "N/A", 
                    "Rating": f"{rating} / 5",
                    "Outlet": outlet_name,
                    "Feedback": feedback,
                    "Submitted At": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
                
                if submit_feedback_to_sheets(new_feedback_entry):
                    st.session_state.submitted_feedback.append(new_feedback_entry)
                    st.success("✅ Feedback submitted successfully to Google Sheets! The form has been cleared.")
            else:
                st.error("⚠️ Please fill **Customer Name** and **Feedback** before submitting.")

        if st.session_state.submitted_feedback:
            st.markdown("### 🗂 Recent Customer Feedback")
            df = pd.DataFrame(st.session_state.submitted_feedback)
            st.dataframe(df.iloc[::-1], use_container_width=True, hide_index=True)

            if st.button("🗑 Clear All Feedback Records", type="secondary"):
                st.session_state.submitted_feedback = []
                st.rerun()
