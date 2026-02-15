import streamlit as st
import pandas as pd
import os
import base64
from barcode import Code128
from barcode.writer import ImageWriter
from io import BytesIO
from streamlit_qrcode_scanner import qrcode_scanner
from PIL import Image, ImageDraw, ImageFont
# --- ADDED: Google Sheets Connection ---
from streamlit_gsheets import GSheetsConnection

# --- FILE PATHS ---
DB_FILE = "inventory.csv"
AUTH_FILE = "credentials.csv"
SETTINGS_FILE = "settings.csv"
LOGO_FILE = "logo.jpg"

st.set_page_config(page_title="Yadin's Baligya Barato", layout="wide", page_icon="₱")

# --- CUSTOM CSS ---
st.markdown("""
    <style>
    .scrolling-wrapper { display: flex; flex-wrap: nowrap; overflow-x: auto; padding-bottom: 20px; gap: 20px; }
    .scrolling-wrapper::-webkit-scrollbar { height: 8px; }
    .scrolling-wrapper::-webkit-scrollbar-thumb { background-color: #cccccc; border-radius: 10px; }
    .slide-card { flex: 0 0 auto; width: 250px; background: white; border-radius: 15px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); padding: 15px; text-align: center; transition: transform 0.3s; border: 1px solid #f0f0f0; }
    .slide-card:hover { transform: scale(1.03); }
    .slide-card img { border-radius: 10px; object-fit: cover; height: 150px; width: 100%; margin-bottom: 10px; }
    .stock-badge { position: absolute; top: 10px; right: 10px; background: rgba(255,255,255,0.95); padding: 4px 8px; border-radius: 5px; font-size: 0.8em; font-weight: bold; box-shadow: 0 2px 5px rgba(0,0,0,0.2); }
    .fb-link { text-decoration: none; color: #1877F2; font-weight: bold; font-size: 1em; margin-right: 20px; display: inline-block; padding: 8px 12px; background-color: #f0f2f5; border-radius: 8px; margin-bottom: 10px; }
    .fb-link:hover { background-color: #e4e6eb; text-decoration: none; }
    .stButton>button { width: 100%; border-radius: 8px; font-weight: bold; }
    </style>
""", unsafe_allow_html=True)

# --- GOOGLE SHEETS CONNECTION ---
conn = st.connection("gsheets", type=GSheetsConnection)

# --- MASTER FUNCTIONS ---
def save_all():
    # 1. Local Backup
    st.session_state.inventory.to_csv(DB_FILE, index=False)
    pd.DataFrame([st.session_state.settings]).to_csv(SETTINGS_FILE, index=False)
    
    # 2. AUTO-SAVE EVERYTHING TO CLOUD
    try:
        conn.update(worksheet="Inventory", data=st.session_state.inventory)
        settings_df = pd.DataFrame([st.session_state.settings])
        conn.update(worksheet="Settings", data=settings_df)
        if os.path.exists(AUTH_FILE):
            admin_df = pd.read_csv(AUTH_FILE)
            conn.update(worksheet="Admin", data=admin_df)
        st.toast("🚀 Auto-Saved to Cloud!")
    except Exception as e:
        st.error(f"Cloud Save Failed: {e}")

def process_image(uploaded_file):
    if uploaded_file is not None:
        try:
            img = Image.open(uploaded_file)
            img.thumbnail((300, 300))
            buf = BytesIO()
            img.save(buf, format="PNG")
            return base64.b64encode(buf.getvalue()).decode()
        except Exception: return ""
    return ""

# --- INITIALIZATION ---
if 'inventory' not in st.session_state:
    try:
        df = conn.read(worksheet="Inventory", ttl=0)
        df['Barcode'] = df['Barcode'].astype(str)
        required_cols = ["Barcode", "Name", "Category", "Price", "Quantity", "Min_Threshold", "Image_Data", "Description"]
        for col in required_cols:
            if col not in df.columns: df[col] = ""
        st.session_state.inventory = df

        settings_df = conn.read(worksheet="Settings", ttl=0)
        if not settings_df.empty:
            st.session_state.settings = settings_df.iloc[0].to_dict()
        
        admin_df = conn.read(worksheet="Admin", ttl=0)
        if not admin_df.empty:
            admin_df.to_csv(AUTH_FILE, index=False)
    except Exception:
        if os.path.exists(DB_FILE):
            st.session_state.inventory = pd.read_csv(DB_FILE, dtype={'Barcode': str})
        else:
            st.session_state.inventory = pd.DataFrame(columns=["Barcode", "Name", "Category", "Price", "Quantity", "Min_Threshold", "Image_Data", "Description"])
        
        if os.path.exists(SETTINGS_FILE):
            st.session_state.settings = pd.read_csv(SETTINGS_FILE).iloc[0].to_dict()
        else:
            st.session_state.settings = {
                "Store Name": "Yadin's Baligya Barato", "DTI": "Pending", "BIR": "Pending",
                "Address": "Philippines", "Phone": "", "Email": "",
                "FB_Montevista": "https://www.facebook.com/yadin.s.baligya.barato",
                "FB_Compostela": "https://www.facebook.com/yadin.s.baligya.barato.nabunturan"
            }

if 'selected_product_barcode' not in st.session_state:
    st.session_state.selected_product_barcode = None

# --- UI COMPONENTS ---
def display_header():
    c_logo, c_text = st.columns([1, 5])
    if os.path.exists(LOGO_FILE): c_logo.image(LOGO_FILE, width=130)
    with c_text:
        st.title(st.session_state.settings.get("Store Name", "My Store"))
        addr, ph, em = st.session_state.settings.get("Address", ""), st.session_state.settings.get("Phone", ""), st.session_state.settings.get("Email", "")
        st.caption(f"📍 {addr} | 📞 {ph} | ✉️ {em}")
        fb1 = st.session_state.settings.get("FB_Montevista", "")
        if fb1: st.markdown(f'<a class="fb-link" href="{fb1}" target="_blank">🔵 Facebook</a>', unsafe_allow_html=True)
    st.divider()

def generate_custom_label(barcode_val, product_name, width, height):
    rv = BytesIO()
    Code128(str(barcode_val), writer=ImageWriter()).write(rv)
    barcode_img = Image.open(rv)
    label = Image.new('RGB', (width, height), color=(255, 255, 255))
    draw = ImageDraw.Draw(label)
    draw.rectangle([(0, 0), (width - 1, height - 1)], outline="black", width=2)
    try: font = ImageFont.truetype("arial.ttf", 20)
    except: font = ImageFont.load_default()
    draw.text((20, 20), product_name[:20], fill="black", font=font)
    label.paste(barcode_img.resize((width - 40, 80)), (20, 50))
    return label

def show_product_card(item, detailed=False):
    if detailed:
        st.button("⬅️ Back", on_click=lambda: st.session_state.update(selected_product_barcode=None))
        st.title(item['Name'])
        img = item['Image_Data']
        if pd.notnull(img) and img != "": st.image(base64.b64decode(img), use_container_width=True)
        st.write(f"**Price:** ₱{item['Price']:,.2f}")
    else:
        with st.container(border=True):
            st.write(f"**{item['Name']}**")
            if st.button("View Details", key=f"btn_{item['Barcode']}"):
                st.session_state.selected_product_barcode = item['Barcode']; st.rerun()

# --- ACCOUNT MANAGEMENT ---
def update_credentials(new_user, new_pass, new_email):
    pd.DataFrame([{"user": new_user, "pass": new_pass, "email": new_email}]).to_csv(AUTH_FILE, index=False)
    save_all() # IMMEDIATE CLOUD UPDATE
    st.success("Credentials Auto-Saved!")
    st.session_state.authenticated = False; st.rerun()

def recover_password(email_input):
    if os.path.exists(AUTH_FILE):
        creds = pd.read_csv(AUTH_FILE)
        if email_input == str(creds.iloc[0]['email']): 
            st.info(f"Your Password is: {creds.iloc[0]['pass']}")
        else: st.error("Email does not match our records.")
    else: st.error("No account found.")

def check_auth():
    if "authenticated" not in st.session_state: st.session_state.authenticated = False
    if st.session_state.authenticated:
        with st.sidebar:
            st.divider(); st.write("👤 **Admin Account**")
            with st.expander("Manage Credentials"):
                with st.form("update_creds"):
                    nu, np, ne = st.text_input("User"), st.text_input("Pass", type="password"), st.text_input("Recovery Email")
                    if st.form_submit_button("Update"):
                        if nu and np and ne: update_credentials(nu, np, ne)
            if st.button("Logout"): st.session_state.authenticated = False; st.rerun()
        return True
    with st.sidebar:
        if not os.path.exists(AUTH_FILE):
            st.title("🆕 Create Account")
            u, p, e = st.text_input("User"), st.text_input("Pass", type="password"), st.text_input("Recovery Email")
            if st.button("Register"): 
                if u and p and e: update_credentials(u, p, e)
        else:
            st.title("🔐 Admin Login")
            u_in, p_in = st.text_input("User"), st.text_input("Pass", type="password")
            if st.button("Login"):
                creds = pd.read_csv(AUTH_FILE)
                if u_in == str(creds.iloc[0]['user']) and p_in == str(creds.iloc[0]['pass']):
                    st.session_state.authenticated = True; st.rerun()
                else: st.error("Access Denied")
            st.divider()
            with st.expander("Forgot Password?"):
                rec_email = st.text_input("Enter Recovery Email")
                if st.button("Recover"): recover_password(rec_email)
    return False

# --- PAGES ---
nav = st.sidebar.radio("Navigation", ["Customer View", "Admin Portal"])

if nav == "Customer View":
    display_header()
    if st.session_state.selected_product_barcode:
        match = st.session_state.inventory[st.session_state.inventory['Barcode'] == st.session_state.selected_product_barcode]
        if not match.empty: show_product_card(match.iloc[0], detailed=True)
    else:
        for _, row in st.session_state.inventory.iterrows(): show_product_card(row)

elif nav == "Admin Portal":
    if check_auth():
        display_header()
        if st.button("🔄 Refresh Data"): st.cache_data.clear(); st.rerun()
        t1, t2, t3, t4, t5 = st.tabs(["📋 List", "➕ Add", "✏️ Edit", "🏷️ Label", "⚙️ Settings"])
        with t2:
            with st.form("add_form"):
                b, n, p, q = st.text_input("Barcode"), st.text_input("Name"), st.number_input("Price"), st.number_input("Stock")
                if st.form_submit_button("Save"):
                    new_row = pd.DataFrame([{"Barcode": b, "Name": n, "Category": "General", "Price": p, "Quantity": q, "Min_Threshold": 5, "Image_Data": "", "Description": ""}])
                    st.session_state.inventory = pd.concat([st.session_state.inventory, new_row], ignore_index=True); save_all(); st.rerun()
        with t5:
            st.subheader("💾 Backup & Settings")
            backup_csv = st.session_state.inventory.to_csv(index=False).encode('utf-8')
            st.download_button("📥 Download Backup (CSV)", data=backup_csv, file_name="inventory_backup.csv")
            with st.form("settings_form"):
                sn, ad = st.text_input("Store Name", st.session_state.settings['Store Name']), st.text_input("Address", st.session_state.settings['Address'])
                if st.form_submit_button("Save Settings"):
                    st.session_state.settings.update({"Store Name": sn, "Address": ad})
                    save_all(); st.success("Settings Saved!"); st.rerun()
