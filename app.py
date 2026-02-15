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
st.set_page_config(page_title="Yadin's Baligya Barato", layout="centered", page_icon="₱")

# --- FILE PATHS ---
# Inventory is now handled by Google Sheets
AUTH_FILE = "credentials.csv"
SETTINGS_FILE = "settings.csv"
LOGO_FILE = "logo.jpg"

# --- ANDROID NATIVE CSS ---
st.markdown("""
    <style>
    /* Hide all web-specific headers/menus for a native app feel */
    header {visibility: hidden;}
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    .stApp { bottom: 60px; } 

    /* Card Styling for Mobile */
    .scrolling-wrapper {
        display: flex;
        flex-wrap: nowrap;
        overflow-x: auto;
        padding-bottom: 20px;
        gap: 15px;
    }
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
    
    /* Native-style Floating Buttons */
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
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    """Loads data directly from Google Sheets."""
    try:
        df = conn.read(worksheet="Inventory", ttl=0)
        df['Barcode'] = df['Barcode'].astype(str)
        # Fill missing columns if sheet is new
        required = ["Barcode", "Name", "Category", "Price", "Quantity", "Min_Threshold", "Image_Data", "Description"]
        for col in required:
            if col not in df.columns: df[col] = ""
        return df
    except Exception:
        return pd.DataFrame(columns=["Barcode", "Name", "Category", "Price", "Quantity", "Min_Threshold", "Image_Data", "Description"])

def save_data(df):
    """Auto-Saves data back to Google Sheets immediately."""
    try:
        conn.update(worksheet="Inventory", data=df)
        st.toast("✅ Auto-Saved to Cloud!")
    except Exception as e:
        st.error(f"Save Failed: {e}")

# --- INITIALIZATION ---
if 'inventory' not in st.session_state:
    st.session_state.inventory = load_data()

# Load Settings (Local CSV is fine for settings, or you can move to sheets later)
if os.path.exists(SETTINGS_FILE):
    st.session_state.settings = pd.read_csv(SETTINGS_FILE).iloc[0].to_dict()
else:
    st.session_state.settings = {
        "Store Name": "Yadin's Baligya Barato",
        "DTI": "Pending", "BIR": "Pending", "Address": "Philippines",
        "Phone": "", "Email": "",
        "FB_Montevista": "https://www.facebook.com/yadin.s.baligya.barato",
        "FB_Compostela": "https://www.facebook.com/yadin.s.baligya.barato.nabunturan"
    }

if 'selected_product_barcode' not in st.session_state:
    st.session_state.selected_product_barcode = None

# --- HELPER FUNCTIONS ---
def save_settings_local():
    pd.DataFrame([st.session_state.settings]).to_csv(SETTINGS_FILE, index=False)

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

def generate_custom_label(barcode_val, product_name, width, height):
    rv = BytesIO()
    Code128(str(barcode_val), writer=ImageWriter()).write(rv)
    barcode_img = Image.open(rv)
    label = Image.new('RGB', (width, height), color=(255, 255, 255))
    draw = ImageDraw.Draw(label)
    draw.rectangle([(0, 0), (width - 1, height - 1)], outline="black", width=2)
    
    current_y = 15
    if os.path.exists(LOGO_FILE):
        logo_size = 60
        try:
            logo = Image.open(LOGO_FILE).resize((logo_size, logo_size))
            x_pos = (width - logo_size) // 2
            label.paste(logo, (x_pos, current_y))
            current_y += logo_size + 10
        except: pass
    else: current_y += 20
    
    try: font = ImageFont.truetype("arial.ttf", 20)
    except: font = ImageFont.load_default()
    
    text_width = len(product_name[:20]) * 10
    x_text = max(10, (width - text_width) // 2)
    draw.text((x_text, current_y), product_name[:20], fill="black", font=font)
    current_y += 30
    
    bc_width, bc_height = width - 40, 80
    barcode_img = barcode_img.resize((bc_width, bc_height))
    label.paste(barcode_img, (20, current_y))
    return label

def display_header():
    c_logo, c_text = st.columns([1, 4])
    with c_logo:
        if os.path.exists(LOGO_FILE): st.image(LOGO_FILE, width=80)
    with c_text:
        st.write(f"### {st.session_state.settings.get('Store Name')}")
        st.caption("Auto-Cloud System")
    st.divider()

def show_product_card(item, detailed=False):
    if detailed:
        if st.button("⬅️ Back"):
            st.session_state.selected_product_barcode = None
            st.rerun()
        st.image(base64.b64decode(item['Image_Data']), use_container_width=True) if pd.notnull(item['Image_Data']) and item['Image_Data'] != "" else st.write("No Image")
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

# --- AUTH SYSTEM (Kept Local for Simplicity) ---
def check_auth():
    if "authenticated" not in st.session_state: st.session_state.authenticated = False
    if st.session_state.authenticated:
        if st.sidebar.button("Logout"):
            st.session_state.authenticated = False
            st.rerun()
        return True

    with st.sidebar:
        st.title("🔐 Admin Login")
        if not os.path.exists(AUTH_FILE):
             st.warning("Create Admin Account")
             u = st.text_input("New User")
             p = st.text_input("New Pass", type="password")
             if st.button("Register"):
                 pd.DataFrame([{"user": u, "pass": p}]).to_csv(AUTH_FILE, index=False)
                 st.success("Registered! Please Login.")
        else:
            u_in = st.text_input("User")
            p_in = st.text_input("Pass", type="password")
            if st.button("Login"):
                creds = pd.read_csv(AUTH_FILE)
                if u_in == str(creds.iloc[0]['user']) and p_in == str(creds.iloc[0]['pass']):
                    st.session_state.authenticated = True
                    st.rerun()
                else:
                    st.error("Wrong Password")
    return False

# --- MAIN APP ---
nav = st.sidebar.radio("Navigation", ["Customer View", "Admin Portal"])

if nav == "Customer View":
    display_header()
    if st.session_state.selected_product_barcode:
        match = st.session_state.inventory[st.session_state.inventory['Barcode'] == st.session_state.selected_product_barcode]
        if not match.empty: show_product_card(match.iloc[0], detailed=True)
        else: st.session_state.selected_product_barcode = None; st.rerun()
    else:
        # Gallery
        st.write("#### Gallery")
        if not st.session_state.inventory.empty:
            cards_html = ""
            for _, row in st.session_state.inventory.iterrows():
                if pd.notnull(row['Image_Data']) and row['Image_Data'] != "": img_src = f"data:image/png;base64,{row['Image_Data']}"
                else: img_src = "https://via.placeholder.com/150"
                cards_html += f'<div class="slide-card"><img src="{img_src}"><div style="font-weight:bold; margin-top:5px;">{row["Name"]}</div><div style="color:red;">₱{row["Price"]}</div></div>'
            st.markdown(f'<div class="scrolling-wrapper">{cards_html}</div>', unsafe_allow_html=True)
        
        st.divider()
        c1, c2 = st.columns(2)
        with c1: st.write("📷"); scanned = qrcode_scanner(key='scanner')
        with c2: search = st.text_input("Search...")
        
        if scanned:
            match = st.session_state.inventory[st.session_state.inventory['Barcode'] == str(scanned)]
            if not match.empty: st.session_state.selected_product_barcode = str(scanned); st.rerun()
            else: st.error("Not Found")
        elif search:
            matches = st.session_state.inventory[st.session_state.inventory['Name'].str.contains(search, case=False, na=False)]
            for _, row in matches.iterrows(): show_product_card(row)

elif nav == "Admin Portal":
    if check_auth():
        display_header()
        if st.button("🔄 Force Refresh Data from Cloud"):
             st.session_state.inventory = load_data()
             st.rerun()
             
        # RESTORED ALL TABS
        t1, t2, t3, t4, t5 = st.tabs(["📋 List", "➕ Add", "✏️ Edit", "🏷️ Label", "⚙️ Settings"])
        
        with t1:
            st.dataframe(st.session_state.inventory.drop(columns=['Image_Data']), use_container_width=True)
            
        with t2:
            st.write("### Add New Product")
            with st.form("add_form"):
                b = st.text_input("Barcode")
                n = st.text_input("Name")
                c_p, c_q = st.columns(2)
                p = c_p.number_input("Price", 0.0)
                q = c_q.number_input("Stock", step=1)
                cat = st.text_input("Category", "General")
                desc = st.text_area("Description")
                img = st.file_uploader("Image")
                
                if st.form_submit_button("SAVE TO CLOUD"):
                    st.session_state.inventory = load_data() # Refresh first
                    if str(b) in st.session_state.inventory['Barcode'].values:
                        st.error("Barcode Exists!")
                    else:
                        new_row = pd.DataFrame([{
                            "Barcode": str(b), "Name": n, "Category": cat, 
                            "Price": p, "Quantity": q, "Min_Threshold": 5, 
                            "Image_Data": process_image(img), "Description": desc
                        }])
                        updated_df = pd.concat([st.session_state.inventory, new_row], ignore_index=True)
                        save_data(updated_df)
                        st.session_state.inventory = updated_df
                        st.success("Saved!")

        with t3:
            st.write("### Edit Product")
            if not st.session_state.inventory.empty:
                target = st.selectbox("Select Product", st.session_state.inventory['Name'].unique())
                match = st.session_state.inventory[st.session_state.inventory['Name'] == target]
                if not match.empty:
                    idx = match.index[0]
                    item = st.session_state.inventory.loc[idx]
                    with st.form("edit_form"):
                        en = st.text_input("Name", item['Name'])
                        ep = st.number_input("Price", value=float(item['Price']))
                        eq = st.number_input("Stock", value=int(item['Quantity']))
                        ed = st.text_area("Description", item['Description'])
                        
                        if st.form_submit_button("UPDATE CLOUD"):
                            fresh_df = load_data()
                            # Locate correctly in fresh data
                            real_idx_list = fresh_df.index[fresh_df['Barcode'] == item['Barcode']].tolist()
                            if real_idx_list:
                                real_idx = real_idx_list[0]
                                fresh_df.at[real_idx, 'Name'] = en
                                fresh_df.at[real_idx, 'Price'] = ep
                                fresh_df.at[real_idx, 'Quantity'] = eq
                                fresh_df.at[real_idx, 'Description'] = ed
                                save_data(fresh_df)
                                st.session_state.inventory = fresh_df
                                st.success("Updated!")
                            else: st.error("Sync Error. Try Refresh.")
        
        with t4:
            st.write("### Label Generator")
            if not st.session_state.inventory.empty:
                l_target = st.selectbox("Product for Label", st.session_state.inventory['Name'].unique(), key="lbl_sel")
                l_item = st.session_state.inventory[st.session_state.inventory['Name'] == l_target].iloc[0]
                w, h = st.slider("Width", 200, 500, 300), st.slider("Height", 200, 500, 250)
                l_img = generate_custom_label(l_item['Barcode'], l_item['Name'], w, h)
                st.image(l_img)
                buf = BytesIO()
                l_img.save(buf, "PNG")
                st.download_button("🖨️ Download Label", buf.getvalue(), "label.png")

        with t5:
            st.write("### Settings")
            with st.form("settings_form"):
                sn = st.text_input("Store Name", st.session_state.settings.get("Store Name"))
                addr = st.text_input("Address", st.session_state.settings.get("Address"))
                if st.form_submit_button("Save Settings"):
                    st.session_state.settings["Store Name"] = sn
                    st.session_state.settings["Address"] = addr
                    save_settings_local()
                    st.success("Settings Saved!")
