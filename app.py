import streamlit as st
import pandas as pd
import os
import base64
from barcode import Code128
from barcode.writer import ImageWriter
from io import BytesIO
from streamlit_qrcode_scanner import qrcode_scanner
from PIL import Image, ImageDraw, ImageFont
# --- GOOGLE SHEETS CONNECTION ---
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

# --- CONNECTION ---
conn = st.connection("gsheets", type=GSheetsConnection)

# --- FUNCTIONS ---
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
        st.toast("🚀 EVERYTHING Auto-Saved to Cloud!")
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
        except: return ""
    return ""

# --- INITIALIZATION ---
if 'inventory' not in st.session_state:
    try:
        df = conn.read(worksheet="Inventory", ttl=0)
        df['Barcode'] = df['Barcode'].astype(str)
        st.session_state.inventory = df
        settings_df = conn.read(worksheet="Settings", ttl=0)
        if not settings_df.empty: st.session_state.settings = settings_df.iloc[0].to_dict()
        admin_df = conn.read(worksheet="Admin", ttl=0)
        if not admin_df.empty: admin_df.to_csv(AUTH_FILE, index=False)
    except:
        if os.path.exists(DB_FILE): st.session_state.inventory = pd.read_csv(DB_FILE, dtype={'Barcode': str})
        else: st.session_state.inventory = pd.DataFrame(columns=["Barcode", "Name", "Category", "Price", "Quantity", "Min_Threshold", "Image_Data", "Description"])
        if os.path.exists(SETTINGS_FILE): st.session_state.settings = pd.read_csv(SETTINGS_FILE).iloc[0].to_dict()
        else: st.session_state.settings = {"Store Name": "Yadin's Baligya Barato", "DTI": "Pending", "BIR": "Pending", "Address": "Philippines", "Phone": "", "Email": "", "FB_Montevista": "", "FB_Compostela": ""}

if 'Description' not in st.session_state.inventory.columns: st.session_state.inventory['Description'] = ""
if 'selected_product_barcode' not in st.session_state: st.session_state.selected_product_barcode = None

# --- UI ---
def display_header():
    c_logo, c_text = st.columns([1, 5])
    if os.path.exists(LOGO_FILE): c_logo.image(LOGO_FILE, width=130)
    with c_text:
        st.title(st.session_state.settings.get("Store Name", "My Store"))
        addr, ph, em = st.session_state.settings.get("Address", ""), st.session_state.settings.get("Phone", ""), st.session_state.settings.get("Email", "")
        st.caption(f"📍 {addr} | 📞 {ph} | ✉️ {em}")
        fb1, fb2 = st.session_state.settings.get("FB_Montevista", ""), st.session_state.settings.get("FB_Compostela", "")
        links_html = ""
        if fb1: links_html += f'<a class="fb-link" href="{fb1}" target="_blank">🔵 Montevista Branch</a>'
        if fb2: links_html += f'<a class="fb-link" href="{fb2}" target="_blank">🔵 Compostela Branch</a>'
        st.markdown(links_html, unsafe_allow_html=True)
    st.divider()

def show_product_card(item, detailed=False):
    if detailed:
        st.button("⬅️ Back to List", on_click=lambda: st.session_state.update(selected_product_barcode=None))
        st.title(item['Name'])
        c1, c2 = st.columns([1, 1])
        with c1:
            img = item['Image_Data']
            if pd.notnull(img) and img != "": st.image(base64.b64decode(img), use_container_width=True)
            else: st.image(LOGO_FILE) if os.path.exists(LOGO_FILE) else st.write("No Image")
        with c2:
            st.subheader(f"Price: ₱{item['Price']:,.2f}")
            st.write(f"**Stock:** {item['Quantity']} units")
            st.write(item['Description'])
            st.caption(f"Barcode: {item['Barcode']}")
    else:
        with st.container(border=True):
            c1, c2 = st.columns([1, 2])
            with c1:
                img = item['Image_Data']
                if pd.notnull(img) and img != "": st.image(base64.b64decode(img), use_container_width=True)
                else: st.image(LOGO_FILE) if os.path.exists(LOGO_FILE) else st.write("No Image")
            with c2:
                st.header(item['Name']); st.metric("Price", f"₱{item['Price']:,.2f}")
                if st.button("View Details", key=f"btn_{item['Barcode']}"):
                    st.session_state.selected_product_barcode = item['Barcode']; st.rerun()

# --- AUTH ---
def check_auth():
    if "authenticated" not in st.session_state: st.session_state.authenticated = False
    if st.session_state.authenticated:
        with st.sidebar:
            st.write("👤 **Admin Account**")
            with st.expander("Update Login/Recovery"):
                with st.form("upd"):
                    nu, np, ne = st.text_input("User"), st.text_input("Pass", type="password"), st.text_input("Recovery Email")
                    if st.form_submit_button("Save"):
                        pd.DataFrame([{"user": nu, "pass": np, "email": ne}]).to_csv(AUTH_FILE, index=False)
                        save_all(); st.success("Updated!"); st.rerun()
            if st.button("Logout"): st.session_state.authenticated = False; st.rerun()
        return True
    with st.sidebar:
        if not os.path.exists(AUTH_FILE):
            u, p, e = st.text_input("User"), st.text_input("Pass", type="password"), st.text_input("Recovery Email")
            if st.button("Register"): pd.DataFrame([{"user": u, "pass": p, "email": e}]).to_csv(AUTH_FILE, index=False); save_all(); st.rerun()
        else:
            st.title("🔐 Login")
            u_in, p_in = st.text_input("User"), st.text_input("Pass", type="password")
            if st.button("Login"):
                creds = pd.read_csv(AUTH_FILE)
                if u_in == str(creds.iloc[0]['user']) and p_in == str(creds.iloc[0]['pass']):
                    st.session_state.authenticated = True; st.rerun()
            with st.expander("Forgot Password?"):
                rec = st.text_input("Recovery Email")
                if st.button("Show Pass"):
                    creds = pd.read_csv(AUTH_FILE)
                    if rec == str(creds.iloc[0]['email']): st.info(f"Pass: {creds.iloc[0]['pass']}")
    return False

# --- PAGES ---
nav = st.sidebar.radio("Navigation", ["Customer View", "Admin Portal"])

if nav == "Customer View":
    display_header()
    if st.session_state.selected_product_barcode:
        match = st.session_state.inventory[st.session_state.inventory['Barcode'] == st.session_state.selected_product_barcode]
        if not match.empty: show_product_card(match.iloc[0], detailed=True)
    else:
        st.subheader("🔥 Store Gallery")
        if not st.session_state.inventory.empty:
            cards_html = ""
            for _, row in st.session_state.inventory.iterrows():
                img_src = f"data:image/png;base64,{row['Image_Data']}" if pd.notnull(row['Image_Data']) and row['Image_Data'] != "" else "https://via.placeholder.com/150"
                qty = int(row['Quantity'])
                status = '<span style="color:red;">🔴 SOLD OUT</span>' if qty == 0 else (f'<span style="color:orange;">⚠️ Low: {qty}</span>' if qty <= 5 else "")
                cards_html += f'<div class="slide-card"><div style="position:relative;"><img src="{img_src}">{"<div class=\"stock-badge\">" + status + "</div>" if status else ""}</div><h4>{row["Name"]}</h4><p style="color:#e63946; font-weight:bold;">₱{row["Price"]:,.2f}</p></div>'
            st.markdown(f'<div class="scrolling-wrapper">{cards_html}</div>', unsafe_allow_html=True)
        
        c1, c2 = st.columns(2)
        with c1: st.write("📷 **Scan**"); scanned = qrcode_scanner(key='scanner')
        with c2: st.write("🔍 **Search**"); search = st.text_input("Search items...")
        
        if scanned:
            st.session_state.selected_product_barcode = str(scanned); st.rerun()
        
        items_to_show = st.session_state.inventory if not search else st.session_state.inventory[st.session_state.inventory['Name'].str.contains(search, case=False, na=False)]
        for _, row in items_to_show.iterrows(): show_product_card(row)

elif nav == "Admin Portal":
    if check_auth():
        display_header()
        t1, t2, t3, t4, t5 = st.tabs(["📋 List", "➕ Add", "✏️ Edit", "🏷️ Label", "⚙️ Settings"])
        with t2:
            with st.form("add"):
                b, n, p, q = st.text_input("Barcode"), st.text_input("Name"), st.number_input("Price"), st.number_input("Stock")
                cat, desc, img = st.text_input("Category"), st.text_area("Description"), st.file_uploader("Image")
                if st.form_submit_button("Save"):
                    new_row = pd.DataFrame([{"Barcode": b, "Name": n, "Category": cat, "Price": p, "Quantity": q, "Min_Threshold": 5, "Image_Data": process_image(img), "Description": desc}])
                    st.session_state.inventory = pd.concat([st.session_state.inventory, new_row], ignore_index=True); save_all(); st.rerun()
        with t5:
            st.subheader("💾 Backup & Branding")
            backup_csv = st.session_state.inventory.to_csv(index=False).encode('utf-8')
            st.download_button("📥 Download CSV Backup", data=backup_csv, file_name="inventory_backup.csv")
            with st.form("set"):
                sn, ad, dti, bir = st.text_input("Store Name", st.session_state.settings['Store Name']), st.text_input("Address", st.session_state.settings['Address']), st.text_input("DTI", st.session_state.settings['DTI']), st.text_input("BIR", st.session_state.settings['BIR'])
                ph, em, fm, fc = st.text_input("Phone", st.session_state.settings['Phone']), st.text_input("Email", st.session_state.settings['Email']), st.text_input("Montevista FB", st.session_state.settings['FB_Montevista']), st.text_input("Compostela FB", st.session_state.settings['FB_Compostela'])
                if st.form_submit_button("Save All Settings"):
                    st.session_state.settings.update({"Store Name": sn, "Address": ad, "DTI": dti, "BIR": bir, "Phone": ph, "Email": em, "FB_Montevista": fm, "FB_Compostela": fc})
                    save_all(); st.success("Branding Saved!"); st.rerun()
