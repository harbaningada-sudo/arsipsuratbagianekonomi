import streamlit as st
import pandas as pd
import json
import gspread
from google.oauth2.service_account import Credentials
import requests
import base64

# Konfigurasi Halaman
st.set_page_config(page_title="Arsip Surat Perekonomian", page_icon="📁", layout="wide")

# KONFIGURASI LINK (Sudah pakai link jembatan milik bro)
APPS_SCRIPT_URL = "https://script.google.com/macros/s/AKfycbwvyAuXxveS8w0w6wFMffeptDvldRB_NIdnYd1-rf-sl0U23n6ZcDQdgjWD33Jo0eEXfw/exec"
SHEET_NAME = "Database_Arsip_Surat"

@st.cache_resource
def get_gspread_client():
    # Mengambil kunci dari Secrets Streamlit
    key_dict = json.loads(st.secrets["google_key"])
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_info(key_dict, scopes=scopes)
    return gspread.authorize(creds)

try:
    gc = get_gspread_client()
except Exception as e:
    st.error(f"Gagal terhubung ke Google Sheets: {e}")
    st.stop()

# Sidebar Navigasi
with st.sidebar:
    st.title("📁 Menu Arsip")
    st.markdown("---")
    menu = st.radio("Pilih Halaman:", ["📥 Upload Surat Baru", "🗂️ Lihat Data Arsip"])
    st.markdown("---")
    st.caption("Sistem Informasi Persuratan - Bagian Perekonomian")

# HALAMAN UPLOAD
if menu == "📥 Upload Surat Baru":
    st.title("Form Upload Surat Baru")
    st.markdown("Isi data surat dan unggah file PDF untuk disimpan otomatis ke Google Drive.")
    
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
            with st.spinner("Sedang memproses upload ke Drive & Sheets..."):
                try:
                    # 1. Kirim file ke Jembatan Apps Script
                    file_content = base64.b64encode(file_surat.read()).decode()
                    payload = {
                        "fileData": file_content,
                        "fileName": file_surat.name,
                        "mimeType": "application/pdf"
                    }
                    
                    # Mengirim data ke URL Jembatan bro
                    response = requests.post(APPS_SCRIPT_URL, data=payload)
                    file_url = response.text

                    if "https://" in file_url:
                        # 2. Jika upload sukses, catat linknya ke Google Sheets
                        sh = gc.open(SHEET_NAME)
                        worksheet = sh.sheet1
                        
                        # Data yang akan dimasukkan ke baris baru
                        row_data = [
                            no_surat, 
                            tgl_surat.strftime("%Y-%m-%d"), 
                            jenis, 
                            perihal, 
                            file_url
                        ]
                        worksheet.append_row(row_data)
                        
                        st.success(f"Berhasil bro! Surat nomor {no_surat} telah diamankan ke Drive & Sheets.")
                        st.balloons()
                    else:
                        st.error(f"Gagal Upload ke Drive: {file_url}")
                except Exception as e:
                    st.error(f"Terjadi kesalahan teknis: {e}")
        else:
            st.warning("Gagal: Nomor Surat dan File PDF wajib diisi!")

# HALAMAN LIHAT DATA
elif menu == "🗂️ Lihat Data Arsip":
    st.title("Data Arsip Persuratan")
    try:
        sh = gc.open(SHEET_NAME)
        worksheet = sh.sheet1
        data = worksheet.get_all_records()
        
        if data:
            df = pd.DataFrame(data)
            
            # Fitur Pencarian sederhana
            cari = st.text_input("🔍 Cari berdasarkan Nomor Surat atau Perihal")
            if cari:
                df = df[df.astype(str).apply(lambda x: x.str.contains(cari, case=False)).any(axis=1)]
            
            # Tampilkan Tabel dengan Link yang bisa diklik
            st.dataframe(
                df, 
                use_container_width=True, 
                hide_index=True,
                column_config={
                    "Link Drive": st.column_config.LinkColumn("Buka File PDF")
                }
            )
        else:
            st.info("Belum ada data surat yang tersimpan.")
    except Exception as e:
        st.error(f"Gagal memuat data dari database: {e}")
