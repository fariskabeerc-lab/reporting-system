import streamlit as st
import pandas as pd

# ==========================================
# PAGE CONFIG
# ==========================================
st.set_page_config(page_title="Stock & New Arrival Dashboard", layout="wide")

# ==========================================
# MANUAL FILE NAMES AND DATES
# ==========================================
# ⚠️ Make sure both Excel files are in the same folder as this script.
files = {
    "warehouse_stock": {
        "path": "stock ware.xlsx", # UPDATED PATH
        "date": "2025-10-29"
    },
    "new_arrival": {
        "path": "NEW ARRAIVAL-27-OCT-25 (1).xlsx",
        "date": "2025-10-29"
    }
}

# ==========================================
# LOAD DATA FUNCTION
# ==========================================
@st.cache_data
def load_excel(file_path):
    try:
        df = pd.read_excel(file_path)
        # Clean column names by stripping whitespace
        df.columns = df.columns.str.strip()
        return df
    except Exception as e:
        st.error(f"❌ Error loading {file_path}. Please ensure the file exists and is readable: {e}")
        return pd.DataFrame()

# ==========================================
# READ BOTH FILES
# ==========================================
# Load the dataframes. They will be empty if the file loading fails.
stock_df = load_excel(files["warehouse_stock"]["path"])
arrival_df = load_excel(files["new_arrival"]["path"])

# ==========================================
# DATA STRUCTURE (for internal use)
# ==========================================
# This structure isn't strictly necessary for the app but is good for debugging/display
data = {
    "stock": {
        "data": stock_df.to_dict(orient="records"),
        "date": files["warehouse_stock"]["date"]
    },
    "new_arrival": {
        "data": arrival_df.to_dict(orient="records"),
        "date": files["new_arrival"]["date"]
    }
}


# ==========================================
# CONFIGURATION CONSTANTS FOR DISPLAY/FILTERING
# ==========================================
CATEGORY_COLUMN = "Category" # Column used for sidebar filtering
COST_COLUMN = "cost"         # Assumed column to be renamed
SELLING_COLUMN = "selling"   # New column name


# ==========================================
# HELPER FUNCTION FOR DISPLAY FORMATTING
# ==========================================
def format_df_for_display(df):
    """
    Creates a copy of the DataFrame, drops the category column, 
    and renames the cost column to selling for presentation.
    """
    # Defensive copy to avoid modifying the cached original DataFrame
    df_display = df.copy() 
    
    # 1. Drop Category Column (Requested by user)
    if CATEGORY_COLUMN in df_display.columns:
        df_display = df_display.drop(columns=[CATEGORY_COLUMN])
    
    # 2. Rename Cost Column to Selling (Requested by user)
    # Note: We assume the column is exactly named 'cost'
    if COST_COLUMN in df_display.columns:
        df_display = df_display.rename(columns={COST_COLUMN: SELLING_COLUMN})
        
    return df_display


# ==========================================
# SIDEBAR FILTERING
# ==========================================
st.sidebar.title("Filter Options")

# --- Category Filter Logic ---
# Check if the assumed category column exists in both dataframes
if CATEGORY_COLUMN in stock_df.columns and CATEGORY_COLUMN in arrival_df.columns:
    
    # Get all unique categories from both dataframes
    all_categories = pd.concat([
        stock_df[CATEGORY_COLUMN].dropna().astype(str),
        arrival_df[CATEGORY_COLUMN].dropna().astype(str)
    ]).str.strip().unique().tolist()
    all_categories.sort()
    all_categories.insert(0, "All Categories")

    # Create the single-select filter
    selected_category = st.sidebar.selectbox(
        "Select Inventory Category", 
        all_categories,
        index=0 # Default to "All Categories"
    )
    
    # Prepare the filtered dataframes
    if selected_category != "All Categories":
        # Filter logic: convert column to string and strip spaces for safe comparison
        filtered_stock_df = stock_df[stock_df[CATEGORY_COLUMN].astype(str).str.strip() == selected_category]
        filtered_arrival_df = arrival_df[arrival_df[CATEGORY_COLUMN].astype(str).str.strip() == selected_category]
    else:
        filtered_stock_df = stock_df
        filtered_arrival_df = arrival_df

else:
    st.sidebar.warning(f"⚠️ Cannot find '{CATEGORY_COLUMN}' column. Displaying unfiltered data.")
    selected_category = "All Categories" # Bypass filtering logic
    filtered_stock_df = stock_df
    filtered_arrival_df = arrival_df


# ==========================================
# COMMON SEARCH BAR (TOP)
# ==========================================
st.title("📦 Inventory Dashboard")
st.markdown("---")

# Global CSS to clean up UI (Center Tabs, Hide Download Button)
st.markdown("""
<style>
/* Center the tabs for better mobile viewing */
.stTabs [data-baseweb="tab-list"] {
    justify-content: center;
    margin-bottom: 20px;
}

/* 🎯 AGGRESSIVE DOWNLOAD BUTTON HIDING 🎯 */

/* 1. Target by common test ID and fully remove the element */
[data-testid="stDownloadButton"] {
    display: none !important;
}

/* 2. Target the container div that holds the download button (often the second child of the toolbar) */
[data-testid^="stDataFrameToolbar"] > div:nth-child(2) {
    display: none !important; 
}
</style>
""", unsafe_allow_html=True)

# Input for search query is now global/common
query = st.text_input(
    "🔍 Search for Item Name or Barcode across all inventory:", 
    placeholder="Enter Barcode or Item Description here...",
    label_visibility="visible"
).strip().lower()

# ==========================================
# SEARCH LOGIC AND DISPLAY
# NOTE: Search always operates on the full, unfiltered stock_df and arrival_df
# ==========================================
if query:
    st.subheader(f"Search Results for: **'{query}'**")
    
    # 1. Search warehouse stock (using original, unfiltered DF)
    results_stock = stock_df[
        stock_df.apply(lambda row: query in str(row.get("itembarcode", "")).lower() or
                                   query in str(row.get("description", "")).lower(), axis=1)
    ] if not stock_df.empty else pd.DataFrame()

    # 2. Search new arrivals (using original, unfiltered DF)
    results_arrival = arrival_df[
        arrival_df.apply(lambda row: query in str(row.get("itembarcode", "")).lower() or
                                     query in str(row.get("description", "")).lower(), axis=1)
    ] if not arrival_df.empty else pd.DataFrame()

    if not results_stock.empty or not results_arrival.empty:
        
        # Display Stock results if found, applying display formatting
        if not results_stock.empty:
            st.markdown("### 🏬 Found in Warehouse Stock")
            st.dataframe(format_df_for_display(results_stock), use_container_width=True)
        
        # Display Arrival results if found, applying display formatting
        if not results_arrival.empty:
            st.markdown("### 🆕 Found in New Arrivals")
            st.dataframe(format_df_for_display(results_arrival), use_container_width=True)
    else:
        st.warning(f"❌ No matching items found for **'{query}'** in either dataset.")
        
# ==========================================
# TABBED PAGE VIEWS (If no search query is active)
# ==========================================
else:
    # Determine the status text based on category selection
    filter_status = f"({f'Filtered by **{selected_category}**' if selected_category != 'All Categories' else 'All Stock'})"

    # Use st.tabs to create the two main pages below the search bar
    # The CSS is now applied globally above
    
    tab1, tab2 = st.tabs(["🏬 Warehouse Stock", "🆕 New Arrival"])

    with tab1:
        st.subheader("🏬 Warehouse Stock")
        st.write(f"📅 Last Updated: **{data['stock']['date']}** {filter_status}")

        # Display filtered stock, applying display formatting
        if not filtered_stock_df.empty:
            st.dataframe(format_df_for_display(filtered_stock_df), use_container_width=True)
        elif not stock_df.empty:
            # Show a warning if the data is filtered out, but the original DF wasn't empty
            st.info(f"No items found in Warehouse Stock for category: **{selected_category}**.")
        else:
            st.warning(f"⚠️ Could not display data from **{files['warehouse_stock']['path']}**.")

    with tab2:
        st.subheader("🆕 New Arrival")
        st.write(f"📅 Last Updated: **{data['new_arrival']['date']}** {filter_status}")

        # Display filtered arrival, applying display formatting
        if not filtered_arrival_df.empty:
            st.dataframe(format_df_for_display(filtered_arrival_df), use_container_width=True)
        elif not arrival_df.empty:
            # Show a warning if the data is filtered out, but the original DF wasn't empty
            st.info(f"No items found in New Arrivals for category: **{selected_category}**.")
        else:
            st.warning(f"⚠️ Could not display data from **{files['new_arrival']['path']}**.")
