import streamlit as st
import pandas as pd
import os
import base64
from barcode import Code128
from barcode.writer import ImageWriter
from io import BytesIO
from streamlit_qrcode_scanner import qrcode_scanner
from PIL import Image, ImageDraw, ImageFont

# --- FILE PATHS ---
DB_FILE = "inventory.csv"
AUTH_FILE = "credentials.csv"
SETTINGS_FILE = "settings.csv"
LOGO_FILE = "logo.jpg"

st.set_page_config(page_title="Yadin's Baligya Barato", layout="wide", page_icon="₱")

# --- CUSTOM CSS ---
st.markdown("""
    <style>
    /* Horizontal Scrolling Container */
    .scrolling-wrapper {
        display: flex;
        flex-wrap: nowrap;
        overflow-x: auto;
        padding-bottom: 20px;
        gap: 20px;
    }
    .scrolling-wrapper::-webkit-scrollbar {
        height: 8px;
    }
    .scrolling-wrapper::-webkit-scrollbar-thumb {
        background-color: #cccccc;
        border-radius: 10px;
    }

    /* The Slide Card */
    .slide-card {
        flex: 0 0 auto;
        width: 250px;
        background: white;
        border-radius: 15px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        padding: 15px;
        text-align: center;
        transition: transform 0.3s;
        border: 1px solid #f0f0f0;
    }
    .slide-card:hover { transform: scale(1.03); }
    .slide-card img {
        border-radius: 10px;
        object-fit: cover;
        height: 150px;
        width: 100%;
        margin-bottom: 10px;
    }

    /* Stock Badge */
    .stock-badge {
        position: absolute; 
        top: 10px; 
        right: 10px; 
        background: rgba(255,255,255,0.95); 
        padding: 4px 8px; 
        border-radius: 5px;
        font-size: 0.8em;
        font-weight: bold;
        box-shadow: 0 2px 5px rgba(0,0,0,0.2);
    }

    /* Facebook Links */
    .fb-link {
        text-decoration: none;
        color: #1877F2;
        font-weight: bold;
        font-size: 1em;
        margin-right: 20px;
        display: inline-block;
        padding: 8px 12px;
        background-color: #f0f2f5;
        border-radius: 8px;
        margin-bottom: 10px;
    }
    .fb-link:hover { 
        background-color: #e4e6eb;
        text-decoration: none;
    }

    .stButton>button { width: 100%; border-radius: 8px; font-weight: bold; }
    </style>
""", unsafe_allow_html=True)

# --- INITIALIZATION ---
if os.path.exists(DB_FILE):
    st.session_state.inventory = pd.read_csv(DB_FILE, dtype={'Barcode': str})
    if 'Description' not in st.session_state.inventory.columns:
        st.session_state.inventory['Description'] = ""
else:
    st.session_state.inventory = pd.DataFrame(
        columns=["Barcode", "Name", "Category", "Price", "Quantity", "Min_Threshold", "Image_Data", "Description"])

if os.path.exists(SETTINGS_FILE):
    st.session_state.settings = pd.read_csv(SETTINGS_FILE).iloc[0].to_dict()
else:
    st.session_state.settings = {
        "Store Name": "Yadin's Baligya Barato",
        "DTI": "Pending",
        "BIR": "Pending",
        "Address": "Philippines",
        "Phone": "",
        "Email": "",
        "FB_Montevista": "https://www.facebook.com/yadin.s.baligya.barato",
        "FB_Compostela": "https://www.facebook.com/yadin.s.baligya.barato.nabunturan"
    }

if 'selected_product_barcode' not in st.session_state:
    st.session_state.selected_product_barcode = None

# --- FUNCTIONS ---
def save_all():
    st.session_state.inventory.to_csv(DB_FILE, index=False)
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

def display_header():
    c_logo, c_text = st.columns([1, 5])
    with c_logo:
        if os.path.exists(LOGO_FILE): st.image(LOGO_FILE, width=130)
    with c_text:
        st.title(st.session_state.settings.get("Store Name", "My Store"))
        addr = st.session_state.settings.get("Address", "")
        dti = st.session_state.settings.get("DTI", "")
        bir = st.session_state.settings.get("BIR", "")
        ph = st.session_state.settings.get("Phone", "")
        em = st.session_state.settings.get("Email", "")
        info = f"📍 {addr}"
        if dti: info += f" | DTI: {dti}"
        if bir: info += f" | BIR: {bir}"
        if ph: info += f" | 📞 {ph}"
        if em: info += f" | ✉️ {em}"
        st.caption(info)
        fb1 = st.session_state.settings.get("FB_Montevista", "")
        fb2 = st.session_state.settings.get("FB_Compostela", "")
        links_html = ""
        if fb1: links_html += f'<a class="fb-link" href="{fb1}" target="_blank">🔵 Montevista Branch</a>'
        if fb2: links_html += f'<a class="fb-link" href="{fb2}" target="_blank">🔵 Compostela Branch</a>'
        if links_html: st.markdown(links_html, unsafe_allow_html=True)
    st.divider()

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
            st.write(f"**Category:** {item['Category']}")
            st.write(f"**Stock:** {item['Quantity']} units")
            qty = int(item['Quantity'])
            threshold = int(item['Min_Threshold']) if pd.notnull(item['Min_Threshold']) else 5
            if qty == 0: st.error("🔴 Product Not Available")
            elif qty <= threshold: st.warning(f"⚠️ Low Stock: Only {qty} left!")
            else: st.success(f"✅ In Stock")
            if pd.notnull(item['Description']) and item['Description'] != "":
                st.write("---")
                st.write("**Description:**")
                st.write(item['Description'])
            st.caption(f"Barcode ID: {item['Barcode']}")
    else:
        with st.container(border=True):
            c1, c2 = st.columns([1, 2])
            with c1:
                img = item['Image_Data']
                if pd.notnull(img) and img != "": st.image(base64.b64decode(img), use_container_width=True)
                else: st.image(LOGO_FILE) if os.path.exists(LOGO_FILE) else st.write("No Image")
            with c2:
                st.header(item['Name'])
                st.caption(item['Category'])
                st.metric("Price", f"₱{item['Price']:,.2f}")
                if st.button("View Details", key=f"btn_{item['Barcode']}"):
                    st.session_state.selected_product_barcode = item['Barcode']
                    st.rerun()

# --- ACCOUNT MANAGEMENT ---
def update_credentials(new_user, new_pass, new_email):
    creds = pd.DataFrame([{"user": new_user, "pass": new_pass, "email": new_email}])
    creds.to_csv(AUTH_FILE, index=False)
    st.success("Credentials Updated! Please login again.")
    st.session_state.authenticated = False
    st.rerun()

def recover_password(email_input):
    if os.path.exists(AUTH_FILE):
        creds = pd.read_csv(AUTH_FILE)
        if "email" in creds.columns:
            if email_input == str(creds.iloc[0]['email']): st.info(f"Your Password is: {creds.iloc[0]['pass']}")
            else: st.error("Email does not match our records.")
        else: st.error("No recovery email set.")
    else: st.error("No account found.")

# --- AUTH ---
def check_auth():
    if "authenticated" not in st.session_state: st.session_state.authenticated = False
    if st.session_state.authenticated:
        with st.sidebar:
            st.divider()
            st.write("👤 **Admin Account**")
            with st.expander("Manage Credentials"):
                with st.form("update_creds"):
                    nu, np, ne = st.text_input("User"), st.text_input("Pass", type="password"), st.text_input("Email")
                    if st.form_submit_button("Update"):
                        if nu and np and ne: update_credentials(nu, np, ne)
            if st.button("Logout"): st.session_state.authenticated = False; st.rerun()
        return True
    with st.sidebar:
        if not os.path.exists(AUTH_FILE):
            st.title("🆕 Create Account")
            u, p, e = st.text_input("User"), st.text_input("Pass", type="password"), st.text_input("Email")
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
        else: st.error("Product not found."); st.session_state.selected_product_barcode = None
    else:
        st.subheader("🔥 Store Gallery")
        if not st.session_state.inventory.empty:
            cards_html = ""
            for _, row in st.session_state.inventory.iterrows():
                if pd.notnull(row['Image_Data']) and row['Image_Data'] != "": img_src = f"data:image/png;base64,{row['Image_Data']}"
                elif os.path.exists(LOGO_FILE):
                    with open(LOGO_FILE, "rb") as f: b64_logo = base64.b64encode(f.read()).decode()
                    img_src = f"data:image/jpg;base64,{b64_logo}"
                else: img_src = "https://via.placeholder.com/150"
                qty = int(row['Quantity'])
                status_html = '<span style="color:red;">🔴 SOLD OUT</span>' if qty == 0 else (f'<span style="color:orange;">⚠️ Low: {qty}</span>' if qty <= 5 else "")
                cards_html += f'<div class="slide-card"><div style="position:relative;"><img src="{img_src}">{"<div class=\"stock-badge\">" + status_html + "</div>" if status_html else ""}</div><h4 style="margin:5px 0; color:#333;">{row["Name"]}</h4><p style="color: #e63946; font-weight: bold; font-size: 1.1em; margin:0;">₱{row["Price"]:,.2f}</p></div>'
            st.markdown(f'<div class="scrolling-wrapper">{cards_html}</div>', unsafe_allow_html=True)
        else: st.info("No products yet.")
        st.divider()
        c1, c2 = st.columns(2)
        with c1: st.write("📷 **Scan**"); scanned = qrcode_scanner(key='scanner')
        with c2: st.write("🔍 **Search**"); search = st.text_input("Product Name...")
        if scanned:
            match = st.session_state.inventory[st.session_state.inventory['Barcode'] == str(scanned)]
            if not match.empty: st.session_state.selected_product_barcode = str(scanned); st.rerun()
            else: st.error("Not Found")
        elif search:
            matches = st.session_state.inventory[st.session_state.inventory['Name'].str.contains(search, case=False, na=False)]
            for _, row in matches.iterrows(): show_product_card(row)
        else:
            st.subheader("All Items")
            for _, row in st.session_state.inventory.iterrows(): show_product_card(row)

elif nav == "Admin Portal":
    if check_auth():
        display_header()
        t1, t2, t3, t4, t5 = st.tabs(["📋 List", "➕ Add", "✏️ Edit", "🏷️ Label", "⚙️ Settings"])
        with t1: st.dataframe(st.session_state.inventory.drop(columns=['Image_Data']), use_container_width=True)
        with t2:
            with st.form("add_form"):
                c1, c2 = st.columns(2)
                b, n, p, q = c1.text_input("Barcode"), c1.text_input("Name"), c2.number_input("Price", 0.0), c2.number_input("Stock", step=1)
                cat, desc, img = c1.text_input("Category", "General"), c1.text_area("Description"), st.file_uploader("Image")
                if st.form_submit_button("Save"):
                    if b in st.session_state.inventory['Barcode'].values: st.error("Barcode exists!")
                    else:
                        new_row = pd.DataFrame([{"Barcode": b, "Name": n, "Category": cat, "Price": p, "Quantity": q, "Min_Threshold": 5, "Image_Data": process_image(img), "Description": desc}])
                        st.session_state.inventory = pd.concat([st.session_state.inventory, new_row], ignore_index=True); save_all(); st.success("Added!")
        with t3:
            if not st.session_state.inventory.empty:
                target = st.selectbox("Select Product", st.session_state.inventory['Name'].unique())
                idx = st.session_state.inventory[st.session_state.inventory['Name'] == target].index[0]
                item = st.session_state.inventory.loc[idx]
                with st.form("edit_form"):
                    en, eb, ep, eq = st.text_input("Name", item['Name']), st.text_input("Barcode", item['Barcode']), st.number_input("Price", value=float(item['Price'])), st.number_input("Stock", value=int(item['Quantity']))
                    ec, ed, ei = st.text_input("Category", item['Category']), st.text_area("Description", item['Description']), st.file_uploader("New Photo")
                    c_s, c_d = st.columns(2)
                    if c_s.form_submit_button("💾 Save"):
                        st.session_state.inventory.loc[idx] = [eb, en, ec, ep, eq, 5, process_image(ei) if ei else item['Image_Data'], ed]
                        save_all(); st.success("Updated!"); st.rerun()
                    if c_d.form_submit_button("🗑️ Delete"):
                        st.session_state.inventory = st.session_state.inventory.drop(idx); save_all(); st.warning("Deleted!"); st.rerun()
        with t4:
            if not st.session_state.inventory.empty:
                l_target = st.selectbox("Product for Label", st.session_state.inventory['Name'].unique())
                l_item = st.session_state.inventory[st.session_state.inventory['Name'] == l_target].iloc[0]
                w, h = st.slider("Width", 200, 500, 300), st.slider("Height", 200, 500, 250)
                l_img = generate_custom_label(l_item['Barcode'], l_item['Name'], w, h)
                st.image(l_img); buf = BytesIO(); l_img.save(buf, "PNG")
                st.download_button("🖨️ Download", buf.getvalue(), "label.png")
        with t5:
            st.subheader("💾 System Backup")
            backup_csv = st.session_state.inventory.to_csv(index=False).encode('utf-8')
            st.download_button(label="📥 Download Inventory Backup (CSV)", data=backup_csv, file_name="inventory_backup.csv", mime="text/csv")
            st.divider()
            st.write("### 🖼️ Change Logo")
            new_logo = st.file_uploader("Upload Logo", type=['jpg', 'png'])
            if new_logo and st.button("Update Logo"):
                with open(LOGO_FILE, "wb") as f: f.write(new_logo.getbuffer())
                st.rerun()
            with st.form("settings_form"):
                sn, dt, br, ad = st.text_input("Store Name", st.session_state.settings['Store Name']), st.text_input("DTI", st.session_state.settings['DTI']), st.text_input("BIR", st.session_state.settings['BIR']), st.text_input("Address", st.session_state.settings['Address'])
                ph, em, fm, fc = st.text_input("Phone", st.session_state.settings['Phone']), st.text_input("Email", st.session_state.settings['Email']), st.text_input("Montevista FB", st.session_state.settings['FB_Montevista']), st.text_input("Compostela FB", st.session_state.settings['FB_Compostela'])
                if st.form_submit_button("Save All Settings"):
                    st.session_state.settings.update({"Store Name": sn, "DTI": dt, "BIR": br, "Address": ad, "Phone": ph, "Email": em, "FB_Montevista": fm, "FB_Compostela": fc})
                    save_all(); st.success("Settings Saved!"); st.rerun()
