import streamlit as st
import pandas as pd
import os

# Konfigurasi Halaman (Harus di paling atas)
st.set_page_config(page_title="Arsip Surat Perekonomian", page_icon="📁", layout="wide")

# Membuat folder dan file database jika belum ada
if not os.path.exists("arsip_surat"):
    os.makedirs("arsip_surat")

DB_FILE = "database_surat.csv"
if not os.path.exists(DB_FILE):
    df = pd.DataFrame(columns=["Nomor Surat", "Tanggal Surat", "Jenis", "Perihal", "Nama File"])
    df.to_csv(DB_FILE, index=False)

# Sidebar untuk Navigasi yang lebih rapi
with st.sidebar:
    st.title("📁 Menu Arsip")
    st.markdown("---")
    menu = st.radio("Pilih Halaman:", ["📥 Upload Surat Baru", "🗂️ Lihat Data Arsip"])
    st.markdown("---")
    st.caption("Sistem Informasi Persuratan")

# Halaman Upload Surat
if menu == "📥 Upload Surat Baru":
    st.title("Form Upload Surat Baru")
    st.markdown("Silakan isi detail surat dan unggah file PDF pada form di bawah ini.")
    
    # Menggunakan container dan kolom agar form tidak terlalu memanjang ke bawah
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
    if st.button("💾 Simpan Arsip ke Database", use_container_width=True):
        if file_surat is not None and no_surat != "":
            # Simpan file
            file_path = os.path.join("arsip_surat", file_surat.name)
            with open(file_path, "wb") as f:
                f.write(file_surat.getbuffer())

            # Simpan ke CSV
            df = pd.read_csv(DB_FILE)
            data_baru = pd.DataFrame({
                "Nomor Surat": [no_surat],
                "Tanggal Surat": [tgl_surat],
                "Jenis": [jenis],
                "Perihal": [perihal],
                "Nama File": [file_surat.name]
            })
            df = pd.concat([df, data_baru], ignore_index=True)
            df.to_csv(DB_FILE, index=False)

            st.success(f"Berhasil! Surat nomor {no_surat} telah diarsipkan.")
        else:
            st.error("Gagal: Nomor Surat wajib diisi dan File PDF wajib diunggah!")

# Halaman Lihat Arsip
elif menu == "🗂️ Lihat Data Arsip":
    st.title("Data Arsip Persuratan")
    
    df = pd.read_csv(DB_FILE)
    
    if df.empty:
        st.info("Belum ada data surat yang tersimpan di sistem.")
    else:
        # Fitur Pencarian
        cari = st.text_input("🔍 Cari arsip berdasarkan Nomor Surat atau Perihal:")
        
        if cari:
            # Filter data berdasarkan ketikan user (huruf kecil/besar tidak masalah)
            df = df[df['Nomor Surat'].str.contains(cari, case=False, na=False) | 
                    df['Perihal'].str.contains(cari, case=False, na=False)]
            st.markdown(f"**Ditemukan {len(df)} surat**")

        # Menampilkan tabel yang lebih rapi
        st.dataframe(df, use_container_width=True, hide_index=True)