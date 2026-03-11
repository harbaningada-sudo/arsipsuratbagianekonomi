import streamlit as st
import pandas as pd
import json
import gspread
from google.oauth2.service_account import Credentials
import requests
import base64

# Konfigurasi Halaman
st.set_page_config(page_title="Arsip Surat Perekonomian", page_icon="📁", layout="wide")

# ==========================================
# PENGATURAN LOGIN (Ganti sesuai keinginan bro)
# ==========================================
ADMIN_USERS = {
    "admin1": "password123", # Ganti admin1 & passwordnya
    "admin2": "ngadabisa"    # Ganti admin2 & passwordnya
}

# KONFIGURASI LINK
APPS_SCRIPT_URL = "https://script.google.com/macros/s/AKfycbwvyAuXxveS8w0w6wFMffeptDvldRB_NIdnYd1-rf-sl0U23n6ZcDQdgjWD33Jo0eEXfw/exec"
SHEET_NAME = "Database_Arsip_Surat"

@st.cache_resource
def get_gspread_client():
    key_dict = json.loads(st.secrets["google_key"])
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_info(key_dict, scopes=scopes)
    return gspread.authorize(creds)

try:
    gc = get_gspread_client()
except Exception as e:
    st.error(f"Gagal terhubung ke Google: {e}")
    st.stop()

# Fungsi Login
def login():
    st.sidebar.title("🔐 Login Admin")
    user = st.sidebar.text_input("Username")
    pw = st.sidebar.text_input("Password", type="password")
    if st.sidebar.button("Masuk"):
        if user in ADMIN_USERS and ADMIN_USERS[user] == pw:
            st.session_state["logged_in"] = True
            st.session_state["user_now"] = user
            st.rerun()
        else:
            st.sidebar.error("Username atau Password Salah!")

if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False

# Sidebar Navigasi
st.sidebar.title("📁 Menu Arsip")
st.sidebar.markdown("---")

if not st.session_state["logged_in"]:
    menu = st.sidebar.radio("Pilih Halaman:", ["🗂️ Lihat Data Arsip"])
    login()
else:
    st.sidebar.success(f"Login sebagai: {st.session_state['user_now']}")
    menu = st.sidebar.radio("Pilih Halaman:", ["🗂️ Lihat Data Arsip", "📥 Upload Surat Baru"])
    if st.sidebar.button("Logout"):
        st.session_state["logged_in"] = False
        st.rerun()

st.sidebar.markdown("---")
st.sidebar.caption("Sistem Informasi Persuratan - Bagian Perekonomian")

# HALAMAN LIHAT DATA (Bisa dilihat siapa saja/umum)
if menu == "🗂️ Lihat Data Arsip":
    st.title("Data Arsip Persuratan")
    try:
        sh = gc.open(SHEET_NAME)
        data = sh.sheet1.get_all_records()
        if data:
            df = pd.DataFrame(data)
            cari = st.text_input("🔍 Cari berdasarkan Nomor Surat atau Perihal")
            if cari:
                df = df[df.astype(str).apply(lambda x: x.str.contains(cari, case=False)).any(axis=1)]
            
            st.dataframe(
                df, use_container_width=True, hide_index=True,
                column_config={"Link Drive": st.column_config.LinkColumn("Buka File PDF")}
            )
        else:
            st.info("Belum ada data surat.")
    except Exception as e:
        st.error(f"Gagal memuat data: {e}")

# HALAMAN UPLOAD (Hanya muncul kalau sudah login)
elif menu == "📥 Upload Surat Baru" and st.session_state["logged_in"]:
    st.title("Form Upload Surat Baru (Khusus Admin)")
    
    col1, col2 = st.columns(2)
    with col1:
        no_surat = st.text_input("Nomor Surat*")
        tgl_surat = st.date_input("Tanggal Surat")
    with col2:
        jenis = st.selectbox("Jenis Surat", ["Surat Masuk", "Surat Keluar"])
        file_surat = st.file_uploader("Upload File PDF*", type=["pdf"])
    
    perihal = st.text_area("Perihal / Isi Ringkas Surat")

    if st.button("💾 Simpan Arsip Permanen", use_container_width=True):
        if file_surat and no_surat:
            with st.spinner("Sedang memproses..."):
                try:
                    file_content = base64.b64encode(file_surat.read()).decode()
                    payload = {"fileData": file_content, "fileName": file_surat.name, "mimeType": "application/pdf"}
                    response = requests.post(APPS_SCRIPT_URL, data=payload)
                    file_url = response.text

                    if "https://" in file_url:
                        sh = gc.open(SHEET_NAME)
                        row_data = [no_surat, tgl_surat.strftime("%Y-%m-%d"), jenis, perihal, file_url]
                        sh.sheet1.append_row(row_data)
                        st.success(f"Berhasil! Tersimpan oleh {st.session_state['user_now']}")
                        st.balloons()
                    else:
                        st.error(f"Gagal Upload: {file_url}")
                except Exception as e:
                    st.error(f"Error: {e}")
        else:
            st.warning("Data belum lengkap!")
