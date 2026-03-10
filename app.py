import streamlit as st
import pandas as pd
import json
import gspread
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
import io

# Konfigurasi Halaman
st.set_page_config(page_title="Arsip Surat Perekonomian", page_icon="📁", layout="wide")

# Menggunakan ID Folder yang sudah kamu buat
DRIVE_FOLDER_ID = "1OI_fs7FsMvPV0fL91lIkLgIheYc_BzXC"
SHEET_NAME = "Database_Arsip_Surat" 

# Fungsi untuk mengkoneksikan Python dengan Google API
@st.cache_resource
def get_google_services():
    # Mengambil kunci rahasia dari Streamlit Secrets
    key_dict = json.loads(st.secrets["google_key"])
    
    # Izin akses ke Drive & Sheets
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    
    creds = Credentials.from_service_account_info(key_dict, scopes=scopes)
    gc = gspread.authorize(creds)
    drive_service = build('drive', 'v3', credentials=creds)
    
    return gc, drive_service

try:
    gc, drive_service = get_google_services()
except Exception as e:
    st.error(f"Gagal terhubung ke Google. Cek kembali isi Secrets. Error: {e}")
    st.stop()

# Sidebar Navigasi
with st.sidebar:
    st.title("📁 Menu Arsip")
    st.markdown("---")
    menu = st.radio("Pilih Halaman:", ["📥 Upload Surat Baru", "🗂️ Lihat Data Arsip"])
    st.markdown("---")
    st.caption("Sistem Informasi Persuratan")

# Halaman Upload Surat
if menu == "📥 Upload Surat Baru":
    st.title("Form Upload Surat Baru")
    st.markdown("Silakan isi detail surat dan unggah file PDF.")
    
    with st.container():
        col1, col2 = st.columns(2)
        
        with col1:
            no_surat = st.text_input("Nomor Surat*")
            tgl_surat = st.date_input("Tanggal Surat")
            
        with col2:
            jenis = st.selectbox("Jenis Surat", ["Surat Masuk", "Surat Keluar"])
            file_surat = st.file_uploader("Upload File Surat (Format .pdf)*", type=["pdf"])
            
        perihal = st.text_area("Perihal / Isi Ringkas Surat")

    # Tombol Simpan
    if st.button("💾 Simpan Arsip Permanen", use_container_width=True):
        if file_surat is not None and no_surat != "":
            with st.spinner("Sedang mengunggah ke Google Drive & Sheets..."):
                try:
                    # 1. Upload file PDF ke Google Drive
                    file_metadata = {
                        'name': file_surat.name,
                        'parents': [DRIVE_FOLDER_ID]
                    }
                    media = MediaIoBaseUpload(io.BytesIO(file_surat.getbuffer()), mimetype='application/pdf', resumable=True)
                    
                    uploaded_file = drive_service.files().create(
                        body=file_metadata, 
                        media_body=media, 
                        fields='id, webViewLink'
                    ).execute()
                    
                    file_url = uploaded_file.get('webViewLink')

                    # 2. Simpan Data ke Google Sheets
                    sh = gc.open(SHEET_NAME)
                    worksheet = sh.sheet1
                    
                    tgl_str = tgl_surat.strftime("%Y-%m-%d")
                    row_data = [no_surat, tgl_str, jenis, perihal, file_url]
                    worksheet.append_row(row_data)

                    st.success(f"Berhasil bro! Surat nomor {no_surat} telah diamankan ke Drive & Sheets.")
                except Exception as e:
                    st.error(f"Terjadi kesalahan saat menyimpan: {e}")
        else:
            st.error("Gagal: Nomor Surat wajib diisi dan File PDF wajib diunggah!")

# Halaman Lihat Arsip
elif menu == "🗂️ Lihat Data Arsip":
    st.title("Data Arsip Persuratan")
    
    try:
        sh = gc.open(SHEET_NAME)
        worksheet = sh.sheet1
        data = worksheet.get_all_records()
        
        if not data:
            st.info("Belum ada data surat yang tersimpan di Google Sheets.")
        else:
            df = pd.DataFrame(data)
            
            # Fitur Pencarian
            cari = st.text_input("🔍 Cari arsip berdasarkan Nomor Surat atau Perihal:")
            
            if cari:
                df = df[df['Nomor Surat'].astype(str).str.contains(cari, case=False, na=False) | 
                        df['Perihal'].astype(str).str.contains(cari, case=False, na=False)]
                st.markdown(f"**Ditemukan {len(df)} surat**")

            # Ubah link drive agar bisa langsung diklik
            st.dataframe(
                df, 
                use_container_width=True, 
                hide_index=True,
                column_config={
                    "Link Drive": st.column_config.LinkColumn("Link File (Klik untuk buka)")
                }
            )
            
    except Exception as e:
        st.error(f"Gagal mengambil data dari Google Sheets. Pastikan nama filenya benar 'Database_Arsip_Surat'. Error: {e}")
