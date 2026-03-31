import streamlit as st
import pandas as pd
import json
import gspread
from google.oauth2.service_account import Credentials
import requests
import base64

# ==========================================
# 1. PENGATURAN LOGIN (SILAKAN GANTI DI SINI)
# ==========================================
ADMIN_USERS = {
    "admin1": "password123",  # Ganti username & password sesukamu
    "admin2": "ngadabisa"     # Contoh admin kedua
}

# ==========================================
# 2. KONFIGURASI LINK (JANGAN ADA YANG TYPO)
# ==========================================
# Link Jembatan Apps Script milik bro
APPS_SCRIPT_URL = "https://script.google.com/macros/s/AKfycbwvyAuXxveS8w0w6wFMffeptDvldRB_NIdnYd1-rf-sl0U23n6ZcDQdgjWD33Jo0eEXfw/exec"
# Nama file Google Sheets bro
SHEET_NAME = "Database_Arsip_Surat"

# Konfigurasi Halaman Web
st.set_page_config(page_title="Arsip Surat Perekonomian", page_icon="📁", layout="wide")

# Fungsi koneksi ke Google Sheets (Database)
@st.cache_resource
def get_gspread_client():
    try:
        key_dict = json.loads(st.secrets["google_key"])
        scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds = Credentials.from_service_account_info(key_dict, scopes=scopes)
        return gspread.authorize(creds)
    except Exception as e:
        st.error(f"Gagal memuat kunci rahasia: {e}")
        return None

gc = get_gspread_client()

# --- LOGIKA LOGIN ---
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False

def login_form():
    with st.sidebar:
        st.title("🔐 Login Admin")
        user = st.text_input("Username", key="user_input")
        pw = st.text_input("Password", type="password", key="pw_input")
        if st.button("Masuk"):
            if user in ADMIN_USERS and ADMIN_USERS[user] == pw:
                st.session_state["logged_in"] = True
                st.session_state["user_now"] = user
                st.rerun()
            else:
                st.error("Username/Password Salah!")

# --- SIDEBAR NAVIGASI ---
with st.sidebar:
    st.title("📁 Menu Arsip")
    st.markdown("---")
    
    if not st.session_state["logged_in"]:
        menu = st.radio("Pilih Halaman:", ["🗂️ Lihat Data Arsip"])
        login_form()
    else:
        st.success(f"Login: {st.session_state['user_now']}")
        menu = st.radio("Pilih Halaman:", ["🗂️ Lihat Data Arsip", "📥 Upload Surat Baru"])
        if st.button("Logout"):
            st.session_state["logged_in"] = False
            st.rerun()
            
    st.markdown("---")
    st.caption("Sistem Informasi Persuratan - Bagian Perekonomian & SDA")

# ==========================================
# 3. HALAMAN LIHAT DATA (PUBLIK)
# ==========================================
if menu == "🗂️ Lihat Data Arsip":
    st.title("Data Arsip Persuratan")
    try:
        sh = gc.open(SHEET_NAME)
        data = sh.sheet1.get_all_records()
        if data:
            df = pd.DataFrame(data)
            cari = st.text_input("🔍 Cari Nomor Surat atau Perihal")
            if cari:
                df = df[df.astype(str).apply(lambda x: x.str.contains(cari, case=False)).any(axis=1)]
            
            st.dataframe(
                df, use_container_width=True, hide_index=True,
                column_config={"Link Drive": st.column_config.LinkColumn("Buka File PDF")}
            )
        else:
            st.info("Bel_um ada data surat yang tersimpan.")
    except Exception as e:
        st.error(f"Gagal memuat database: {e}")

# ==========================================
# 4. HALAMAN UPLOAD (KHUSUS ADMIN)
# ==========================================
elif menu == "📥 Upload Surat Baru" and st.session_state["logged_in"]:
    st.title("Form Upload Surat Baru")
    st.markdown("Silakan isi data surat dan unggah file PDF.")
    
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
            with st.spinner("Sedang mengunggah... mohon tunggu..."):
                try:
                    # Proses kirim file ke Jembatan Apps Script
                    file_content = base64.b64encode(file_surat.read()).decode()
                    payload = {
                        "fileData": file_content,
                        "fileName": file_surat.name,
                        "mimeType": "application/pdf"
                    }
                    
                    # Request ke Apps Script
                    response = requests.post(APPS_SCRIPT_URL, data=payload)
                    file_url = response.text

                    if "https://" in file_url:
                        # Catat ke Google Sheets jika upload sukses
                        sh = gc.open(SHEET_NAME)
                        row = [no_surat, tgl_surat.strftime("%Y-%m-%d"), jenis, perihal, file_url]
                        sh.sheet1.append_row(row)
                        
                        st.success(f"Berhasil! Surat {no_surat} telah tersimpan.")
                        st.balloons()
                    else:
                        st.error(f"Gagal Upload: {file_url}. Pastikan izin Google Drive sudah aktif.")
                except Exception as e:
                    st.error(f"Terjadi kesalahan teknis: {e}")
        else:
            st.warning("Mohon isi Nomor Surat dan Upload File PDF!")
