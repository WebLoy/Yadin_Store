import streamlit as st
import pandas as pd
import os
import base64
from barcode import Code128
from barcode.writer import ImageWriter
from io import BytesIO
from streamlit_qrcode_scanner import qrcode_scanner
from PIL import Image, ImageDraw, ImageFont
from streamlit_gsheets import GSheetsConnection

# --- CONFIGURATION ---
# Replace this URL with your own Google Sheet Public URL if using public, 
# or set up secrets.toml for private (recommended).
# For now, this code expects a connection named "gsheets" in your secrets.
st.set_page_config(page_title="Yadin's Baligya Barato", layout="centered", page_icon="₱")

# --- FILE PATHS (LOCAL CACHE ONLY) ---
LOGO_FILE = "logo.jpg"

# --- ANDROID NATIVE CSS (KEPT AS REQUESTED) ---
st.markdown("""
    <style>
    header {visibility: hidden;}
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    .stApp { bottom: 60px; } 

    .slide-card {
        flex: 0 0 auto;
        width: 160px;
        background: white;
        border-radius: 12px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        padding: 8px;
        text-align: center;
        margin-right: 10px;
    }
    .slide-card img {
        border-radius: 8px;
        height: 100px;
        width: 100%;
        object-fit: cover;
    }
    
    .stButton>button { 
        width: 100%; 
        border-radius: 12px; 
        height: 3.5em;
        background-color: #1877F2;
        color: white;
        font-size: 16px;
    }
    </style>
""", unsafe_allow_html=True)

# --- GOOGLE SHEETS CONNECTION ---
# This creates a connection to your Google Sheet
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    """Loads data directly from Google Sheets."""
    try:
        # ttl=0 means "don't cache", always get fresh data
        df = conn.read(worksheet="Inventory", ttl=0)
        # Ensure strict string types for Barcode to prevent scientific notation
        df['Barcode'] = df['Barcode'].astype(str)
        return df
    except Exception:
        # If sheet is empty, return empty structure
        return pd.DataFrame(columns=["Barcode", "Name", "Category", "Price", "Quantity", "Min_Threshold", "Image_Data", "Description"])

def save_data(df):
    """Auto-Saves data back to Google Sheets immediately."""
    conn.update(worksheet="Inventory", data=df)
    st.toast("✅ Auto-Saved to Cloud!")

# Initialize Session State
if 'inventory' not in st.session_state:
    st.session_state.inventory = load_data()

# Refresh button to force pull latest data (useful if multiple people are editing)
if st.sidebar.button("🔄 Force Refresh"):
    st.session_state.inventory = load_data()
    st.rerun()

# --- HELPER FUNCTIONS ---
def process_image(uploaded_file):
    if uploaded_file is not None:
        try:
            img = Image.open(uploaded_file)
            img.thumbnail((300, 300))
            buf = BytesIO()
            img.save(buf, format="PNG")
            return base64.b64encode(buf.getvalue()).decode()
        except Exception:
            return ""
    return ""

def display_header():
    # Simple Mobile Header
    c_logo, c_text = st.columns([1, 3])
    with c_logo:
        if os.path.exists(LOGO_FILE): st.image(LOGO_FILE, width=80)
    with c_text:
        st.write("### Yadin's Store")
        st.caption("Auto-Cloud System")
    st.divider()

def show_product_card(item, detailed=False):
    if detailed:
        if st.button("⬅️ Back"):
            st.session_state.selected_product_barcode = None
            st.rerun()
        
        st.image(base64.b64decode(item['Image_Data']), use_column_width=True) if pd.notnull(item['Image_Data']) and item['Image_Data'] != "" else st.write("No Image")
        st.title(item['Name'])
        st.subheader(f"₱{item['Price']:,.2f}")
        
        qty = int(item['Quantity'])
        if qty == 0: st.error("Out of Stock")
        elif qty <= 5: st.warning(f"Low Stock: {qty} left")
        else: st.success(f"In Stock: {qty}")
        
        st.write(item['Description'])
        st.caption(f"ID: {item['Barcode']}")
    else:
        with st.container(border=True):
            c1, c2 = st.columns([1, 2])
            with c1:
                img = item['Image_Data']
                if pd.notnull(img) and img != "": st.image(base64.b64decode(img), use_container_width=True)
                else: st.write("No Image")
            with c2:
                st.write(f"**{item['Name']}**")
                st.write(f"₱{item['Price']:,.2f}")
                if st.button("View", key=f"btn_{item['Barcode']}"):
                    st.session_state.selected_product_barcode = item['Barcode']
                    st.rerun()

# --- MAIN APP FLOW ---
display_header()

# Create Tabs
t1, t2, t3 = st.tabs(["🛒 Shop", "➕ Add", "⚙️ Admin"])

with t1:
    if 'selected_product_barcode' not in st.session_state: st.session_state.selected_product_barcode = None
    
    if st.session_state.selected_product_barcode:
        match = st.session_state.inventory[st.session_state.inventory['Barcode'] == st.session_state.selected_product_barcode]
        if not match.empty: show_product_card(match.iloc[0], detailed=True)
        else: st.session_state.selected_product_barcode = None; st.rerun()
    else:
        # Search & Scan
        col_scan, col_search = st.columns([1,2])
        with col_scan:
            st.write("📷")
            scanned = qrcode_scanner(key='scanner')
        with col_search:
            search = st.text_input("Search Item...")
            
        if scanned:
            match = st.session_state.inventory[st.session_state.inventory['Barcode'] == str(scanned)]
            if not match.empty:
                st.session_state.selected_product_barcode = str(scanned)
                st.rerun()
            else:
                st.error("Item Not Found")

        # Scrolling Gallery
        st.write("#### Gallery")
        if not st.session_state.inventory.empty:
            cards_html = ""
            for _, row in st.session_state.inventory.iterrows():
                if pd.notnull(row['Image_Data']) and row['Image_Data'] != "": img_src = f"data:image/png;base64,{row['Image_Data']}"
                else: img_src = "https://via.placeholder.com/150"
                cards_html += f'<div class="slide-card"><img src="{img_src}"><div style="font-weight:bold; margin-top:5px;">{row["Name"]}</div><div style="color:red;">₱{row["Price"]}</div></div>'
            st.markdown(f'<div class="scrolling-wrapper">{cards_html}</div>', unsafe_allow_html=True)
        
        st.divider()
        # List all items vertical
        if search:
            matches = st.session_state.inventory[st.session_state.inventory['Name'].str.contains(search, case=False, na=False)]
            for _, row in matches.iterrows(): show_product_card(row)

with t2:
    st.write("### Add New Product")
    with st.form("add_form"):
        b = st.text_input("Barcode (Scan or Type)")
        n = st.text_input("Product Name")
        c_p, c_q = st.columns(2)
        p = c_p.number_input("Price", 0.0)
        q = c_q.number_input("Stock", step=1)
        cat = st.text_input("Category", "General")
        desc = st.text_area("Description")
        img = st.file_uploader("Image")
        
        if st.form_submit_button("SAVE TO CLOUD"):
            if b in st.session_state.inventory['Barcode'].values:
                st.error("Barcode already exists!")
            else:
                new_row = pd.DataFrame([{
                    "Barcode": str(b), "Name": n, "Category": cat, 
                    "Price": p, "Quantity": q, "Min_Threshold": 5, 
                    "Image_Data": process_image(img), "Description": desc
                }])
                # Add to local state
                st.session_state.inventory = pd.concat([st.session_state.inventory, new_row], ignore_index=True)
                # AUTO SAVE TO GOOGLE SHEETS
                save_data(st.session_state.inventory)
                st.success("Saved to Google Sheets!")

with t3:
    st.write("### Admin Tools")
    # Quick Edit Mode
    if not st.session_state.inventory.empty:
        target = st.selectbox("Edit Item", st.session_state.inventory['Name'].unique())
        idx = st.session_state.inventory[st.session_state.inventory['Name'] == target].index[0]
        item = st.session_state.inventory.loc[idx]
        
        new_q = st.number_input("Update Stock", value=int(item['Quantity']))
        new_p = st.number_input("Update Price", value=float(item['Price']))
        
        if st.button("Update Cloud"):
            st.session_state.inventory.at[idx, 'Quantity'] = new_q
            st.session_state.inventory.at[idx, 'Price'] = new_p
            save_data(st.session_state.inventory)
            st.success("Updated!")
            
    st.divider()
    if st.button("Force Backup Download"):
        csv = st.session_state.inventory.to_csv(index=False).encode('utf-8')
        st.download_button("Download CSV", csv, "backup.csv", "text/csv")
