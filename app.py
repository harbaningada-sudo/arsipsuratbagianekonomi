import streamlit as st
import pandas as pd
import json
import gspread
from google.oauth2.service_account import Credentials
import requests
import base64

# ==========================================
# 1. KONFIGURASI LOGIN & LINK
# ==========================================
# Username dan Password untuk Admin
ADMIN_USERS = {
    "admin1": "password123",
    "admin2": "ngadabisa"
}

# MASUKKAN URL APPS SCRIPT YANG BARU DI SINI!
APPS_SCRIPT_URL = "ISI_DENGAN_URL_DEPLOYMENT_KAMU_YANG_BARU"
SHEET_NAME = "Database_Arsip_Surat"

# Konfigurasi Tampilan
st.set_page_config(page_title="Arsip Digital Ekonomi Ngada", page_icon="📁", layout="wide")

# Fungsi Koneksi Google Sheets
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

# Inisialisasi Login
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False

# --- SIDEBAR NAVIGASI ---
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
                st.error("Username/Password Salah!")
        
        st.markdown("---")
        menu = st.radio("Navigasi:", ["🗂️ Lihat Data Arsip"])
    else:
        st.success(f"Aktif: {st.session_state['user_now']}")
        menu = st.radio("Navigasi:", ["🗂️ Lihat Data Arsip", "📥 Upload Surat Baru"])
        if st.button("Keluar (Log Out)"):
            st.session_state["logged_in"] = False
            st.rerun()

    st.markdown("---")
    st.caption("Sistem Informasi Persuratan - Kab. Ngada")

# ==========================================
# 2. HALAMAN LIHAT DATA
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
            search = st.text_input("🔍 Cari Nomor Surat atau Perihal")
            if search:
                df = df[df.astype(str).apply(lambda x: x.str.contains(search, case=False)).any(axis=1)]
            
            # Tampilkan Tabel
            st.dataframe(
                df, 
                use_container_width=True, 
                hide_index=True,
                column_config={
                    "Link Drive": st.column_config.LinkColumn("📂 Buka PDF")
                }
            )
        else:
            st.info("Belum ada data arsip.")
    except Exception as e:
        st.error(f"Gagal memuat database: {e}")

# ==========================================
# 3. HALAMAN UPLOAD (Hanya Admin)
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
            file_pdf = st.file_uploader("Pilih File PDF*", type=["pdf"])
        
        perihal = st.text_area("Perihal / Ringkasan Surat")
        submit = st.form_submit_button("🚀 Simpan ke Database & Drive")

    if submit:
        if no_surat and file_pdf:
            with st.spinner("Sedang memproses... Tunggu sampai selesai!"):
                try:
                    # Proses kirim ke Apps Script
                    file_content = base64.b64encode(file_pdf.read()).decode()
                    payload = {
                        "fileData": file_content,
                        "fileName": file_pdf.name,
                        "mimeType": "application/pdf"
                    }
                    
                    # Kirim data ke Jembatan Google
                    res = requests.post(APPS_SCRIPT_URL, data=payload)
                    link_pdf = res.text

                    # Cek hasil (Harus berupa link HTTPS)
                    if "https://" in link_pdf:
                        sh = gc.open(SHEET_NAME)
                        baris_baru = [no_surat, tgl_surat.strftime("%Y-%m-%d"), jenis, perihal, link_pdf]
                        sh.sheet1.append_row(baris_baru)
                        
                        st.success(f"BERHASIL! Surat {no_surat} sudah tersimpan.")
                        st.balloons()
                    else:
                        st.error(f"Gagal Simpan: {link_pdf}. Pastikan izin 'Anyone' sudah aktif di Script!")
                except Exception as e:
                    st.error(f"Terjadi Gangguan: {e}")
        else:
            st.warning("Mohon isi Nomor Surat dan lampirkan PDF-nya!")
