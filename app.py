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
    .slide-card { flex: 0 0 auto; width: 250px; background: white; border-radius: 15px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); padding: 15px; text-align: center; transition: transform 0.3s; border: 1px solid #f0f0f0; position: relative; }
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

# --- MASTER FUNCTIONS ---
def save_all(manual=False):
    """Saves to local CSV AND Auto-Saves to Google Sheets."""
    st.session_state.inventory.to_csv(DB_FILE, index=False)
    pd.DataFrame([st.session_state.settings]).to_csv(SETTINGS_FILE, index=False)
    try:
        conn.update(worksheet="Inventory", data=st.session_state.inventory)
        settings_df = pd.DataFrame([st.session_state.settings])
        conn.update(worksheet="Settings", data=settings_df)
        if os.path.exists(AUTH_FILE):
            admin_df = pd.read_csv(AUTH_FILE)
            conn.update(worksheet="Admin", data=admin_df)
        if manual: st.success("✅ Manual Cloud Sync Complete!")
        else: st.toast("🚀 Auto-Saved to Cloud!")
    except Exception as e: st.error(f"Cloud Sync Failed: {e}")

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

def generate_custom_label(barcode_val, product_name, width, height):
    rv = BytesIO()
    Code128(str(barcode_val), writer=ImageWriter()).write(rv)
    barcode_img = Image.open(rv)
    label = Image.new('RGB', (width, height), color=(255, 255, 255))
    draw = ImageDraw.Draw(label)
    draw.rectangle([(0, 0), (width - 1, height - 1)], outline="black", width=2)
    if os.path.exists(LOGO_FILE):
        logo_size = 60
        logo = Image.open(LOGO_FILE).resize((logo_size, logo_size))
        label.paste(logo, ((width - logo_size) // 2, 15))
    try: font = ImageFont.truetype("arial.ttf", 20)
    except: font = ImageFont.load_default()
    draw.text((max(10, (width - (len(product_name[:20]) * 10)) // 2), 85), product_name[:20], fill="black", font=font)
    label.paste(barcode_img.resize((width - 40, 80)), (20, 115))
    return label

# --- INITIALIZATION ---
if 'inventory' not in st.session_state:
    try:
        df = conn.read(worksheet="Inventory", ttl=0)
        df['Barcode'] = df['Barcode'].astype(str)
        # Ensure columns exist and handle missing image data as empty string
        for col in ["Barcode", "Name", "Category", "Price", "Quantity", "Min_Threshold", "Image_Data", "Description"]:
            if col not in df.columns: df[col] = ""
        df['Image_Data'] = df['Image_Data'].fillna("")
        st.session_state.inventory = df
        settings_df = conn.read(worksheet="Settings", ttl=0)
        if not settings_df.empty: st.session_state.settings = settings_df.iloc[0].to_dict()
        admin_df = conn.read(worksheet="Admin", ttl=0)
        if not admin_df.empty: admin_df.to_csv(AUTH_FILE, index=False)
    except:
        if os.path.exists(DB_FILE): 
            st.session_state.inventory = pd.read_csv(DB_FILE, dtype={'Barcode': str}).fillna("")
        else: 
            st.session_state.inventory = pd.DataFrame(columns=["Barcode", "Name", "Category", "Price", "Quantity", "Min_Threshold", "Image_Data", "Description"])
        
        if os.path.exists(SETTINGS_FILE): st.session_state.settings = pd.read_csv(SETTINGS_FILE).iloc[0].to_dict()
        else: st.session_state.settings = {"Store Name": "Yadin's Baligya Barato", "Address": "Philippines", "DTI": "Pending", "BIR": "Pending", "FB_Montevista": "", "FB_Compostela": ""}

if 'selected_product_barcode' not in st.session_state:
    st.session_state.selected_product_barcode = None

# --- UI COMPONENTS ---
def display_header():
    c_logo, c_text = st.columns([1, 5])
    if os.path.exists(LOGO_FILE): c_logo.image(LOGO_FILE, width=130)
    with c_text:
        st.title(st.session_state.settings.get("Store Name", "My Store"))
        addr, dti, bir = st.session_state.settings.get("Address", ""), st.session_state.settings.get("DTI", ""), st.session_state.settings.get("BIR", "")
        ph, em = st.session_state.settings.get("Phone", ""), st.session_state.settings.get("Email", "")
        info = f"📍 {addr}"
        if dti: info += f" | DTI: {dti}"
        if bir: info += f" | BIR: {bir}"
        if ph: info += f" | 📞 {ph}"
        st.caption(info)
        fb1, fb2 = st.session_state.settings.get("FB_Montevista", ""), st.session_state.settings.get("FB_Compostela", "")
        links_html = ""
        if fb1: links_html += f'<a class="fb-link" href="{fb1}" target="_blank">🔵 Montevista Branch</a>'
        if fb2: links_html += f'<a class="fb-link" href="{fb2}" target="_blank">🔵 Compostela Branch</a>'
        st.markdown(links_html, unsafe_allow_html=True)
    st.divider()

def show_product_card(item, detailed=False):
    if detailed:
        st.button("⬅️ Back to Shop", on_click=lambda: st.session_state.update(selected_product_barcode=None))
        col1, col2 = st.columns([1, 1])
        with col1:
            img = item['Image_Data']
            if pd.notnull(img) and str(img).strip() != "": 
                try: st.image(base64.b64decode(img), use_container_width=True)
                except: st.write("Invalid Image Data")
            else: st.image(LOGO_FILE) if os.path.exists(LOGO_FILE) else st.write("No Image")
        with col2:
            st.title(item['Name'])
            st.header(f"₱{float(item['Price']):,.2f}")
            st.write(f"**Category:** {item['Category']}")
            qty = int(item['Quantity'])
            if qty == 0: st.error("🔴 SOLD OUT")
            elif qty <= 5: st.warning(f"⚠️ Low Stock: Only {qty} left!")
            else: st.success(f"✅ In Stock: {qty} units")
            st.write("**Description:**")
            st.write(item['Description'] if item['Description'] else "No description available.")
            st.caption(f"Barcode ID: {item['Barcode']}")
    else:
        with st.container(border=True):
            c1, c2 = st.columns([1, 2])
            with c1:
                img = item['Image_Data']
                if pd.notnull(img) and str(img).strip() != "": 
                    try: st.image(base64.b64decode(img), use_container_width=True)
                    except: st.write("No Image")
                else: st.write("No Image")
            with c2:
                st.subheader(item['Name'])
                st.write(f"₱{float(item['Price']):,.2f}")
                if st.button("View Details", key=f"btn_{item['Barcode']}"):
                    st.session_state.selected_product_barcode = item['Barcode']; st.rerun()

# --- AUTH ---
def check_auth():
    if "authenticated" not in st.session_state: st.session_state.authenticated = False
    if st.session_state.authenticated:
        with st.sidebar:
            st.write("👤 Admin Mode")
            if st.button("Logout"): st.session_state.authenticated = False; st.rerun()
        return True
    with st.sidebar:
        if not os.path.exists(AUTH_FILE):
            u, p, e = st.text_input("User"), st.text_input("Pass", type="password"), st.text_input("Recovery Email")
            if st.button("Register"): pd.DataFrame([{"user": u, "pass": p, "email": e}]).to_csv(AUTH_FILE, index=False); save_all(); st.rerun()
        else:
            u_in, p_in = st.text_input("User"), st.text_input("Pass", type="password")
            if st.button("Login"):
                creds = pd.read_csv(AUTH_FILE)
                if u_in == str(creds.iloc[0]['user']) and p_in == str(creds.iloc[0]['pass']): st.session_state.authenticated = True; st.rerun()
                else: st.error("Invalid Login")
            with st.expander("Forgot Password?"):
                rec = st.text_input("Recovery Email")
                if st.button("Recover"):
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
        if not st.session_state.inventory.empty:
            cards_html = ""
            for _, row in st.session_state.inventory.iterrows():
                img_src = f"data:image/png;base64,{row['Image_Data']}" if pd.notnull(row['Image_Data']) and str(row['Image_Data']).strip() != "" else "https://via.placeholder.com/150"
                qty = int(row['Quantity'])
                status = '<span style="color:red;">🔴 SOLD OUT</span>' if qty == 0 else (f'<span style="color:orange;">⚠️ Low: {qty}</span>' if qty <= 5 else "")
                cards_html += f'<div class="slide-card"><div style="position:relative;"><img src="{img_src}">{"<div class=\"stock-badge\">" + status + "</div>" if status else ""}</div><h4>{row["Name"]}</h4><p style="color:#e63946; font-weight:bold;">₱{float(row["Price"]):,.2f}</p></div>'
            st.markdown(f'<div class="scrolling-wrapper">{cards_html}</div>', unsafe_allow_html=True)
        
        c1, c2 = st.columns(2)
        with c1: st.write("📷 Scan QR"); scanned = qrcode_scanner(key='scanner')
        with c2: search = st.text_input("🔍 Search Name")
        if scanned: st.session_state.selected_product_barcode = str(scanned); st.rerun()
        
        items = st.session_state.inventory if not search else st.session_state.inventory[st.session_state.inventory['Name'].str.contains(search, case=False)]
        for _, row in items.iterrows(): show_product_card(row)

elif nav == "Admin Portal":
    if check_auth():
        display_header()
        if st.button("🔄 Force Cloud Sync"): save_all(manual=True)
        t1, t2, t3, t4, t5 = st.tabs(["📋 List", "➕ Add", "✏️ Edit", "🏷️ Label", "⚙️ Settings"])
        
        with t1:
            if 'Image_Data' in st.session_state.inventory.columns:
                st.dataframe(st.session_state.inventory.drop(columns=['Image_Data']), use_container_width=True)
            else:
                st.dataframe(st.session_state.inventory, use_container_width=True)
                
        with t2:
            with st.form("add"):
                b, n, p, q = st.text_input("Barcode"), st.text_input("Name"), st.number_input("Price", 0.0), st.number_input("Stock", 0)
                cat, desc, img = st.text_input("Category", "General"), st.text_area("Description"), st.file_uploader("Image")
                if st.form_submit_button("Save"):
                    new_row = pd.DataFrame([{"Barcode": b, "Name": n, "Category": cat, "Price": p, "Quantity": q, "Min_Threshold": 5, "Image_Data": process_image(img), "Description": desc}])
                    st.session_state.inventory = pd.concat([st.session_state.inventory, new_row], ignore_index=True); save_all(); st.rerun()
        with t3:
            if not st.session_state.inventory.empty:
                target = st.selectbox("Select Product to Edit", st.session_state.inventory['Name'].unique())
                idx = st.session_state.inventory[st.session_state.inventory['Name'] == target].index[0]
                item = st.session_state.inventory.loc[idx]
                with st.form("edit"):
                    en, eb, ep, eq = st.text_input("Name", item['Name']), st.text_input("Barcode", item['Barcode']), st.number_input("Price", value=float(item['Price'])), st.number_input("Stock", value=int(item['Quantity']))
                    ec, ed, ei = st.text_input("Category", item['Category']), st.text_area("Description", item['Description']), st.file_uploader("Change Photo")
                    
                    c_upd, c_del = st.columns(2)
                    if c_upd.form_submit_button("💾 Update"):
                        new_img = process_image(ei) if ei else item['Image_Data']
                        st.session_state.inventory.loc[idx] = [eb, en, ec, ep, eq, 5, new_img, ed]
                        save_all(); st.rerun()
                    
                    delete_trigger = c_del.form_submit_button("🗑️ Delete Product")
                    if delete_trigger:
                        st.session_state.confirm_delete = idx
                
                if "confirm_delete" in st.session_state and st.session_state.confirm_delete == idx:
                    st.error(f"⚠️ Are you sure you want to delete '{item['Name']}'?")
                    cd1, cd2 = st.columns(2)
                    if cd1.button("🔥 YES, DELETE"):
                        st.session_state.inventory = st.session_state.inventory.drop(idx)
                        del st.session_state.confirm_delete
                        save_all(); st.rerun()
                    if cd2.button("❌ CANCEL"):
                        del st.session_state.confirm_delete
                        st.rerun()

        with t4:
            if not st.session_state.inventory.empty:
                l_target = st.selectbox("Product for Label", st.session_state.inventory['Name'].unique())
                l_item = st.session_state.inventory[st.session_state.inventory['Name'] == l_target].iloc[0]
                l_img = generate_custom_label(l_item['Barcode'], l_item['Name'], 300, 200)
                st.image(l_img)
                buf = BytesIO(); l_img.save(buf, "PNG")
                st.download_button("📥 Download Label", buf.getvalue(), f"label_{l_item['Barcode']}.png")
        with t5:
            st.subheader("💾 Master Export & Backup")
            col_a, col_b = st.columns(2)
            with col_a:
                csv_data = st.session_state.inventory.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="📥 Download Full Inventory Backup (CSV)",
                    data=csv_data,
                    file_name=f"inventory_backup_{pd.Timestamp.now().strftime('%Y%m%d_%H%M')}.csv",
                    mime='text/csv',
                    help="Click here to save a full copy of your inventory, including all image data, to your computer."
                )
            with col_b:
                uploaded_backup = st.file_uploader("Restore from Backup", type=['csv'])
                if uploaded_backup and st.button("🔥 Confirm Restore"):
                    new_data = pd.read_csv(uploaded_backup, dtype={'Barcode': str}).fillna("")
                    for col in ["Barcode", "Name", "Category", "Price", "Quantity", "Min_Threshold", "Image_Data", "Description"]:
                        if col not in new_data.columns: new_data[col] = "" 
                    st.session_state.inventory = new_data
                    save_all(); st.rerun()
                
            st.divider()
            st.subheader("🎨 Branding & Logo")
            new_logo = st.file_uploader("Update Logo", type=['jpg', 'png'])
            if new_logo and st.button("Save Logo"):
                with open(LOGO_FILE, "wb") as f: f.write(new_logo.getbuffer())
                st.success("Logo Updated!"); st.rerun()
            with st.form("branding"):
                sn, ad, dt, br, ph, em, fm, fc = st.text_input("Store Name", st.session_state.settings.get('Store Name','')), st.text_input("Address", st.session_state.settings.get('Address','')), st.text_input("DTI", st.session_state.settings.get('DTI','')), st.text_input("BIR", st.session_state.settings.get('BIR','')), st.text_input("Phone", st.session_state.settings.get('Phone','')), st.text_input("Email", st.session_state.settings.get('Email','')), st.text_input("Montevista FB", st.session_state.settings.get('FB_Montevista','')), st.text_input("Compostela FB", st.session_state.settings.get('FB_Compostela',''))
                if st.form_submit_button("💾 Save All Store Details & Sync"):
                    st.session_state.settings.update({"Store Name": sn, "Address": ad, "DTI": dt, "BIR": br, "Phone": ph, "Email": em, "FB_Montevista": fm, "FB_Compostela": fc})
                    save_all(manual=True) # This triggers both CSV and Google Sheets save
                    st.rerun()
