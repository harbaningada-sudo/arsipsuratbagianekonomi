import streamlit as st
import pandas as pd
import json
import gspread
from google.oauth2.service_account import Credentials
import requests
import base64

# ==========================================
# 1. PENGATURAN LOGIN ADMIN
# ==========================================
# Silakan ganti username dan password di bawah ini
ADMIN_USERS = {
    "admin1": "password123",
    "admin2": "ngadabisa"
}

# ==========================================
# 2. KONFIGURASI LINK & DATABASE
# ==========================================
# GANTI link di bawah ini dengan URL Web App dari Google Apps Script kamu yang terbaru!
APPS_SCRIPT_URL = "https://script.google.com/macros/s/AKfycbwvyAuXxveS8w0w6wFMffeptDvldRB_NIdnYd1-rf-sl0U23n6ZcDQdgjWD33Jo0eEXfw/exec"
SHEET_NAME = "Database_Arsip_Surat"

# Konfigurasi Tampilan Web
st.set_page_config(page_title="Arsip Digital Perekonomian Ngada", page_icon="📁", layout="wide")

# Fungsi Koneksi ke Google Sheets
@st.cache_resource
def get_gspread_client():
    try:
        key_dict = json.loads(st.secrets["google_key"])
        scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds = Credentials.from_service_account_info(key_dict, scopes=scopes)
        return gspread.authorize(creds)
    except Exception as e:
        st.error(f"Gagal memuat Google Secrets: {e}")
        return None

gc = get_gspread_client()

# Inisialisasi Status Login
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False

# --- SIDEBAR & NAVIGASI ---
with st.sidebar:
    st.title("📁 Menu Utama")
    st.markdown("---")
    
    if not st.session_state["logged_in"]:
        st.subheader("🔐 Login Admin")
        user = st.text_input("Username")
        pw = st.text_input("Password", type="password")
        if st.button("Masuk"):
            if user in ADMIN_USERS and ADMIN_USERS[user] == pw:
                st.session_state["logged_in"] = True
                st.session_state["user_now"] = user
                st.rerun()
            else:
                st.error("Login Gagal!")
        
        st.markdown("---")
        menu = st.radio("Navigasi:", ["🗂️ Lihat Data Arsip"])
    else:
        st.success(f"Aktif: {st.session_state['user_now']}")
        menu = st.radio("Navigasi:", ["🗂️ Lihat Data Arsip", "📥 Upload Surat Baru"])
        if st.button("Log Out"):
            st.session_state["logged_in"] = False
            st.rerun()

    st.markdown("---")
    st.caption("Sistem Informasi Persuratan - Kab. Ngada")

# ==========================================
# 3. HALAMAN LIHAT DATA (Bisa dilihat siapa saja)
# ==========================================
if menu == "🗂️ Lihat Data Arsip":
    st.title("Daftar Arsip Surat Digital")
    try:
        sh = gc.open(SHEET_NAME)
        worksheet = sh.sheet1
        data = worksheet.get_all_records()
        
        if data:
            df = pd.DataFrame(data)
            
            # Kolom Pencarian
            search_query = st.text_input("🔍 Cari Nomor Surat, Perihal, atau Tanggal")
            if search_query:
                df = df[df.astype(str).apply(lambda x: x.str.contains(search_query, case=False)).any(axis=1)]
            
            # Tampilkan Tabel
            st.dataframe(
                df, 
                use_container_width=True, 
                hide_index=True,
                column_config={
                    "Link Drive": st.column_config.LinkColumn("📂 Buka File PDF")
                }
            )
        else:
            st.info("Database masih kosong. Silakan upload surat pertama.")
    except Exception as e:
        st.error(f"Koneksi Database Terputus: {e}")

# ==========================================
# 4. HALAMAN UPLOAD (Hanya untuk Admin)
# ==========================================
elif menu == "📥 Upload Surat Baru" and st.session_state["logged_in"]:
    st.title("Input Arsip Surat Baru")
    
    with st.form("form_upload", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            no_surat = st.text_input("Nomor Surat*")
            tgl_surat = st.date_input("Tanggal Surat")
        with col2:
            jenis = st.selectbox("Jenis Surat", ["Surat Masuk", "Surat Keluar"])
            file_surat = st.file_uploader("Pilih File PDF*", type=["pdf"])
        
        perihal = st.text_area("Perihal / Ringkasan Isi Surat")
        submit = st.form_submit_button("🚀 Simpan ke Database & Drive")

    if submit:
        if no_surat and file_surat:
            with st.spinner("Sedang mengamankan file ke Google Drive..."):
                try:
                    # 1. Kirim ke Jembatan Apps Script
                    file_content = base64.b64encode(file_surat.read()).decode()
                    payload = {
                        "fileData": file_content,
                        "fileName": file_surat.name,
                        "mimeType": "application/pdf"
                    }
                    
                    response = requests.post(APPS_SCRIPT_URL, data=payload)
                    file_url = response.text

                    # 2. Cek apakah hasil upload adalah link valid
                    if "https://" in file_url:
                        sh = gc.open(SHEET_NAME)
                        row = [no_surat, tgl_surat.strftime("%Y-%m-%d"), jenis, perihal, file_url]
                        sh.sheet1.append_row(row)
                        
                        st.success(f"SUKSES! Surat {no_surat} berhasil diarsipkan.")
                        st.balloons()
                    else:
                        st.error(f"Gagal Simpan: {file_url}. Periksa izin DriveApp di Google Script!")
                except Exception as e:
                    st.error(f"Terjadi Kesalahan: {e}")
        else:
            st.warning("Nomor Surat dan File PDF tidak boleh kosong!")
