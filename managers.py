import streamlit as st
import pandas as pd
from datetime import datetime
import gspread
import time

# --- Configuration ---
# NOTE: In a real environment, __gspread_credentials will be provided by the hosting service.
# If running locally, you must provide your Google Sheets credentials in `st.secrets`.

# === CRITICAL CHANGE: USE YOUR GOOGLE SHEET URL HERE ===
# ⚠️ ACTION REQUIRED: Replace the placeholder URL below with the actual URL of your Google Sheet.
SPREADSHEET_URL = "https://docs.google.com/spreadsheets/d/1MK5WDETIFCRes-c8X16JjrNdrlEpHwv9vHvb96VVtM0/edit?gid=0#gid=0" 
ITEMS_WORKSHEET_NAME = "Items"           # The sheet containing the submitted data

# --- Session State Initialization (Minimal) ---
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'data_loaded' not in st.session_state:
    st.session_state.data_loaded = False
if 'df_gsheet' not in st.session_state:
    st.session_state.df_gsheet = pd.DataFrame()
if 'df_edited' not in st.session_state:
    st.session_state.df_edited = pd.DataFrame()

# --- Google Sheets Connection ---

@st.cache_resource(show_spinner="Connecting to Google Sheets...")
def get_gspread_client():
    """Initializes and returns the gspread client using credentials, using the URL."""
    try:
        # Check for provided credentials (used by Streamlit Cloud)
        if '__gspread_credentials' in globals():
            creds = globals()['__gspread_credentials']
        else:
            # Fallback for local testing (requires st.secrets or local creds file)
            if "gcp_service_account" not in st.secrets:
                 st.error("Google Sheets credentials not found. Please ensure 'gcp_service_account' is set in st.secrets.")
                 return None
            creds = st.secrets["gcp_service_account"]

        gc = gspread.service_account_from_dict(creds)
        # === CRITICAL CHANGE: open_by_url instead of open ===
        spreadsheet = gc.open_by_url(SPREADSHEET_URL)
        items_worksheet = spreadsheet.worksheet(ITEMS_WORKSHEET_NAME)
        return items_worksheet
    except gspread.exceptions.SpreadsheetNotFound:
        st.error(f"Spreadsheet at URL not found or access denied.")
        return None
    except gspread.exceptions.WorksheetNotFound:
        st.error(f"Worksheet '{ITEMS_WORKSHEET_NAME}' not found.")
        return None
    except Exception as e:
        st.error(f"Failed to connect to Google Sheets: {e}")
        return None

items_worksheet = get_gspread_client()
sheets_connected = items_worksheet is not None


# --- Data Loading Function (Fetches all data and row numbers) ---
@st.cache_data(ttl=60) # Cache for 1 minute
def load_action_data(worksheet):
    """
    Fetches all data, including row indices, for tracking changes.
    Returns a DataFrame and the list of column headers.
    """
    if not sheets_connected:
        return pd.DataFrame(), []

    try:
        data = worksheet.get_all_values()
        if not data:
            return pd.DataFrame(), []

        headers = data[0]
        records = data[1:]

        df = pd.DataFrame(records, columns=headers)
        
        # Add a temporary 'GSHEET_ROW_INDEX' column (1-based index)
        df['GSHEET_ROW_INDEX'] = range(2, len(df) + 2)

        # Convert numeric columns safely
        for col in ['Qty', 'Cost', 'Selling', 'Amount', 'GP%', 'CF']:
             if col in df.columns:
                 df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0) 
        
        # Ensure date columns are in a reasonable format
        if 'Date Submitted' in df.columns:
            df['Date Submitted'] = pd.to_datetime(df['Date Submitted'], errors='coerce')
        # === CRITICAL CHANGE: Ensure Expiry is parsed as datetime for filtering ===
        if 'Expiry' in df.columns: 
            df['Expiry'] = pd.to_datetime(df['Expiry'], errors='coerce')
        
        # Ensure 'Action Took' column exists for filtering, defaulting to a blank string
        if 'Action Took' not in df.columns:
            df['Action Took'] = ''
            
        return df, headers

    except Exception as e:
        st.error(f"❌ Error loading dashboard data from Google Sheets: {e}")
        return pd.DataFrame(), []

# --- Data Submission Function (Writes back to GSheet) ---
def save_edited_data(df_original, df_edited, worksheet):
    """
    Compares the original and edited DataFrames and writes only the 
    modified 'Action Took' cells back to Google Sheets.
    """
    if df_original.empty or df_edited.empty:
        st.warning("No data to save.")
        return

    if 'GSHEET_ROW_INDEX' not in df_edited.columns:
        st.error("Cannot save: Missing row index.")
        return
        
    changes_made = 0
    updates = []
    
    # Iterate through the edited DataFrame to find changes in 'Action Took'
    for index, row_edited in df_edited.iterrows():
        # Find the original row using the unique GSHEET_ROW_INDEX
        original_row_match = df_original[df_original['GSHEET_ROW_INDEX'] == row_edited['GSHEET_ROW_INDEX']]
        if original_row_match.empty:
            continue
            
        original_row = original_row_match.iloc[0]

        # Check if Action Took has changed
        if 'Action Took' in df_edited.columns and str(row_edited['Action Took']) != str(original_row['Action Took']):
            
            gsheet_row = int(row_edited['GSHEET_ROW_INDEX'])
            new_action = str(row_edited['Action Took'])
            
            # Find the column index for 'Action Took' (1-based index for gspread)
            try:
                action_col_index = df_original.columns.get_loc('Action Took') + 1
            except KeyError:
                st.error("The column 'Action Took' was not found in the sheet headers.")
                return 

            # Create the update object: [row, col, value]
            updates.append({
                'range': gspread.utils.rowcol_to_a1(gsheet_row, action_col_index),
                'values': [[new_action]]
            })
            changes_made += 1

    if changes_made > 0:
        with st.spinner(f"Saving {changes_made} changes..."):
            worksheet.batch_update(updates)
        st.success(f"✅ Successfully updated {changes_made} records in Google Sheets!")
        st.session_state.df_gsheet = df_edited.copy()
        load_action_data.clear() 
    else:
        st.info("No changes detected in the 'Action Took' column to save.")
        
    st.session_state.df_edited = st.session_state.df_gsheet.copy()
    st.rerun()


# --- Application Layout ---
st.set_page_config(
    page_title="Action Tracking Dashboard", 
    layout="wide", 
    initial_sidebar_state="collapsed"
)

st.title("Manager Action Tracking Dashboard")
st.markdown("---")


# 1. Login (Simple Auth for Management Role)
if not st.session_state.logged_in:
    st.subheader("Manager Login")
    user = st.text_input("Username", key="login_user")
    pwd = st.text_input("Password", type="password", key="login_pwd")
    
    # Simple hardcoded management login
    if st.button("Log In to Dashboard"):
        if user.lower() == "manager" and pwd == "tracker456": # Use a simple, predefined password
            st.session_state.logged_in = True
            st.toast("Access Granted.", icon="🔓")
            st.rerun()
        else:
            st.error("Invalid credentials.")
    st.markdown("<br>Use Username: `manager`, Password: `tracker456`", unsafe_allow_html=True)

# 2. Main Dashboard Content
elif sheets_connected:
    
    # Load or Refresh Data
    if st.button("🔄 Reload Data from Google Sheet"):
        load_action_data.clear()
        st.session_state.data_loaded = False
        st.rerun()

    if not st.session_state.data_loaded:
        df_gsheet, headers = load_action_data(items_worksheet)
        st.session_state.df_gsheet = df_gsheet
        st.session_state.df_edited = df_gsheet.copy() # Initialize edited state
        st.session_state.data_loaded = True
    
    df_display = st.session_state.df_edited.copy()

    if df_display.empty:
        st.warning("No item submission data found in the 'Items' worksheet.")
    else:
        # Initialize filtered_df with the full data
        df_filtered = df_display.copy()
        
        # --- NEW: FILTER CONTAINER ---
        st.markdown("### 🔍 Data Filters")
        
        # 1. Date Range Filter
        col_date_start, col_date_end, col_dummy = st.columns(3)
        
        if 'Date Submitted' in df_filtered.columns and not df_filtered['Date Submitted'].dropna().empty:
            
            # Use only date part for min/max calculation
            df_dates = df_filtered['Date Submitted'].dropna().dt.date
            min_date = df_dates.min()
            max_date = df_dates.max()
            
            # Ensure min_date is before max_date, or use today as a fallback
            if min_date > max_date:
                 min_date = max_date 

            with col_date_start:
                start_date = st.date_input("Start Date (Submitted)", value=min_date, min_value=min_date, max_value=max_date, key='start_date')
            with col_date_end:
                end_date = st.date_input("End Date (Submitted)", value=max_date, min_value=min_date, max_value=max_date, key='end_date')

            if start_date and end_date:
                # Filter by submitted date range
                df_filtered = df_filtered[
                    (df_filtered['Date Submitted'].dt.date >= start_date) & 
                    (df_filtered['Date Submitted'].dt.date <= end_date)
                ]
            
        # 2. Expiry, Submission Type, and Action Status Filters
        col_exp, col_form, col_action = st.columns(3)
        
        # 2a. Expiry Filter (Near Expiry)
        with col_exp:
            expiry_options = {
                "All Expiry Dates": 99999,
                "Expiring in 7 Days": 7,
                "Expiring in 30 Days": 30,
                "Expiring in 60 Days": 60,
                "Already Expired": 0
            }
            expiry_filter_selection = st.selectbox(
                "Filter by Item Expiry",
                options=list(expiry_options.keys()),
                index=0,
                key="expiry_filter_select"
            )
            
            days_until_expiry = expiry_options[expiry_filter_selection]
            
            if days_until_expiry != 99999 and 'Expiry' in df_filtered.columns:
                today = pd.to_datetime(datetime.now().date())
                
                if days_until_expiry == 0: # Already Expired
                    df_filtered = df_filtered[df_filtered['Expiry'].notna() & (df_filtered['Expiry'] < today)]
                else:
                    future_date = today + pd.Timedelta(days=days_until_expiry)
                    # Filter items expiring between today and future_date (inclusive)
                    df_filtered = df_filtered[
                        df_filtered['Expiry'].notna() & 
                        (df_filtered['Expiry'] >= today) & 
                        (df_filtered['Expiry'] <= future_date)
                    ]

        # 2b. Form Type Filter (Near Expiry / Damages / Expiry)
        with col_form:
            form_types = df_display['Form Type'].dropna().unique().tolist()
            form_type_selection = st.selectbox(
                "Filter by Submission Type",
                options=["-- All Submission Types --"] + form_types,
                index=0,
                key="form_type_filter"
            )

            if form_type_selection != "-- All Submission Types --":
                df_filtered = df_filtered[df_filtered['Form Type'] == form_type_selection]


        # 2c. Action Took Status Filter
        with col_action:
            action_took_statuses = df_display['Action Took'].dropna().unique().tolist()
            filter_action_status = st.selectbox(
                "Filter by Action Took Status",
                options=["-- All Action Statuses --"] + action_took_statuses,
                index=0,
                key="action_status_filter"
            )

            if filter_action_status != "-- All Action Statuses --":
                df_filtered = df_filtered[df_filtered['Action Took'] == filter_action_status]
            
        st.markdown("---") # End of filter container
        
        # Update subheader with filtered count
        st.subheader(f"Filtered Results ({len(df_filtered)} Records)")

        # Define which columns are visible and how they behave
        column_config = {
            # Make these primary info columns non-editable
            "Date Submitted": st.column_config.DatetimeColumn("Date Submitted", format="DD MMM YY HH:mm", disabled=True),
            "Expiry": st.column_config.DateColumn("Expiry Date", format="DD MMM YY", disabled=True), # Added Expiry
            "Outlet": st.column_config.TextColumn("Outlet", disabled=True),
            "Item Name": st.column_config.TextColumn("Item Name", disabled=True),
            "Barcode": st.column_config.TextColumn("Barcode", disabled=True),
            "Qty": st.column_config.NumberColumn("Qty", disabled=True),
            "Unit": st.column_config.TextColumn("Unit", disabled=True),
            "CF": st.column_config.NumberColumn("CF", disabled=True),
            
            # Make 'Action Took' editable, and suggest common options
            "Action Took": st.column_config.SelectboxColumn(
                "Action Took",
                required=True,
                options=[
                    "Pending Review", "Ordered", "Rejected - Duplicate", 
                    "Rejected - Out of Stock", "Needs Clarification", "Completed"
                ],
                help="Select the action taken on this item request.",
            ),
            
            # Hide the internal row index
            "GSHEET_ROW_INDEX": st.column_config.TextColumn(disabled=True, is_table_index=True, width="tiny"), 
        }
        
        # Define the visible columns in order (Added Expiry)
        visible_cols = [
            "Date Submitted", "Expiry", "Outlet", "Item Name", "Barcode", "Qty", "Unit", 
            "Action Took", "Staff Name", "Supplier", "Remarks", "Cost", "Selling", "GP%", "Form Type"
        ]

        # 3. Interactive Data Editor
        edited_df = st.data_editor(
            df_filtered[visible_cols + ['GSHEET_ROW_INDEX']], # Include index for saving
            column_config=column_config,
            disabled=[col for col in visible_cols if col != "Action Took"], # Disable all but Action Took
            key="action_editor",
            use_container_width=True,
            height=400
        )
        
        # Check if the edited data is different from the original data (only used to enable save button)
        # Note: We compare the edited view against the *filtered* original view
        is_modified = not edited_df.equals(df_filtered[visible_cols + ['GSHEET_ROW_INDEX']])

        # 4. Save Button
        st.markdown("---")
        col_save, col_spacer = st.columns([1, 4])
        
        with col_save:
            if st.button("💾 Save All Changes to Google Sheet", type="primary", disabled=not is_modified):
                # 1. Update the full df_edited state with changes from the filtered view
                df_temp = st.session_state.df_edited.set_index('GSHEET_ROW_INDEX')
                for index, row in edited_df.iterrows():
                    gsheet_row_index = row['GSHEET_ROW_INDEX']
                    # We only care about the Action Took column change
                    df_temp.loc[gsheet_row_index, 'Action Took'] = row['Action Took']
                
                st.session_state.df_edited = df_temp.reset_index()
                
                # 2. Save the full state
                save_edited_data(st.session_state.df_gsheet, st.session_state.df_edited, items_worksheet)
            
        if not is_modified:
            st.caption("Edit a cell in the 'Action Took' column to enable the Save button.")

elif not sheets_connected:
    st.error("Cannot proceed. Google Sheets connection failed. Please check the URL and sheet names.")

# --- Logout Button (Available once logged in) ---
if st.session_state.logged_in and st.button("🔓 Logout", key="logout_btn"):
    st.session_state.logged_in = False
    st.session_state.data_loaded = False
    st.rerun()
