import streamlit as st
import pandas as pd
import json
import gspread
from google.oauth2.service_account import Credentials
import requests
import base64
import time

# ==========================================
# KONFIGURASI
# ==========================================
ADMIN_USERS = {
    "admin1": "password123",
    "admin2": "ngadabisa"
}

# GANTI DENGAN URL APPS SCRIPT DEPLOYMENT KAMU
APPS_SCRIPT_URL = st.secrets.get("apps_script_url", "https://script.google.com/macros/s/AKfycbxs0Wp-aH1-awpwcHKz_8goz7sBZF4Xr7ZnJ3kTjYdMXY9czlCa_Oj5RUIMM6EbZ0w6/exec")
SHEET_NAME = "Database_Arsip_Surat"

# Batas ukuran file PDF (dalam MB)
MAX_FILE_SIZE_MB = 10

# ==========================================
# KONFIGURASI HALAMAN
# ==========================================
st.set_page_config(
    page_title="Arsip Digital - Kab. Ngada",
    page_icon="📁",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==========================================
# CSS KUSTOM
# ==========================================
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(135deg, #1a3c6e, #2563a8);
        color: white;
        padding: 1.5rem;
        border-radius: 10px;
        margin-bottom: 1.5rem;
        text-align: center;
    }
    .main-header h1 { margin: 0; font-size: 1.8rem; }
    .main-header p  { margin: 0.3rem 0 0; opacity: 0.85; font-size: 0.95rem; }

    .info-box {
        background: #e8f4fd;
        border-left: 4px solid #2563a8;
        padding: 0.8rem 1rem;
        border-radius: 5px;
        margin-bottom: 1rem;
    }
    .success-box {
        background: #e8f8e8;
        border-left: 4px solid #28a745;
        padding: 0.8rem 1rem;
        border-radius: 5px;
    }
    .warning-box {
        background: #fff8e1;
        border-left: 4px solid #ffc107;
        padding: 0.8rem 1rem;
        border-radius: 5px;
    }
    .stDataFrame { border-radius: 8px; overflow: hidden; }
</style>
""", unsafe_allow_html=True)

# ==========================================
# KONEKSI GOOGLE SHEETS
# ==========================================
@st.cache_resource(show_spinner=False)
def get_gspread_client():
    try:
        key_dict = json.loads(st.secrets["google_key"])
        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]
        creds = Credentials.from_service_account_info(key_dict, scopes=scopes)
        return gspread.authorize(creds)
    except KeyError:
        st.error("❌ Secret 'google_key' tidak ditemukan. Tambahkan di Settings > Secrets.")
        return None
    except Exception as e:
        st.error(f"❌ Gagal koneksi Google: {e}")
        return None

gc = get_gspread_client()

# ==========================================
# FUNGSI HELPER
# ==========================================
def get_worksheet():
    """Buka worksheet, buat header jika kosong."""
    try:
        sh = gc.open(SHEET_NAME)
        ws = sh.sheet1
        # Pastikan header ada
        existing = ws.get_all_values()
        if not existing or existing[0] != ["No Surat", "Tanggal", "Jenis", "Perihal", "Pengirim/Tujuan", "Link Drive", "Diupload Oleh", "Waktu Upload"]:
            if not existing:
                ws.append_row(["No Surat", "Tanggal", "Jenis", "Perihal", "Pengirim/Tujuan", "Link Drive", "Diupload Oleh", "Waktu Upload"])
        return ws
    except gspread.exceptions.SpreadsheetNotFound:
        # Buat spreadsheet baru jika belum ada
        sh = gc.create(SHEET_NAME)
        sh.share(None, perm_type="anyone", role="reader")
        ws = sh.sheet1
        ws.append_row(["No Surat", "Tanggal", "Jenis", "Perihal", "Pengirim/Tujuan", "Link Drive", "Diupload Oleh", "Waktu Upload"])
        st.info(f"📋 Spreadsheet '{SHEET_NAME}' baru dibuat otomatis.")
        return ws
    except Exception as e:
        st.error(f"❌ Gagal buka worksheet: {e}")
        return None


def upload_ke_drive(file_bytes: bytes, file_name: str) -> str:
    """
    Kirim file ke Google Drive via Apps Script.
    Mendukung file besar dengan chunking base64.
    Return: URL file di Drive, atau string error.
    """
    if APPS_SCRIPT_URL == "ISI_URL_APPS_SCRIPT_DISINI":
        return "ERROR: URL Apps Script belum diisi di secrets.toml atau kode."

    # Validasi ukuran file
    size_mb = len(file_bytes) / (1024 * 1024)
    if size_mb > MAX_FILE_SIZE_MB:
        return f"ERROR: File terlalu besar ({size_mb:.1f} MB). Maksimal {MAX_FILE_SIZE_MB} MB."

    try:
        # Encode base64
        file_b64 = base64.b64encode(file_bytes).decode("utf-8")

        payload = {
            "fileData": file_b64,
            "fileName": file_name,
            "mimeType": "application/pdf"
        }

        # Kirim dengan timeout lebih panjang (scan PDF bisa besar)
        response = requests.post(
            APPS_SCRIPT_URL,
            json=payload,          # Pakai JSON, bukan form-data
            timeout=120            # 2 menit timeout
        )

        if response.status_code != 200:
            return f"ERROR: Server Apps Script merespons status {response.status_code}: {response.text[:200]}"

        result = response.text.strip()

        # Validasi respons harus berupa link Google Drive
        if result.startswith("https://"):
            return result
        elif result.startswith("ERROR"):
            return result
        else:
            return f"ERROR: Respons tidak valid dari Apps Script: {result[:200]}"

    except requests.exceptions.Timeout:
        return "ERROR: Timeout — upload terlalu lama. Coba file yang lebih kecil atau kompres PDF-nya."
    except requests.exceptions.ConnectionError:
        return "ERROR: Tidak bisa terhubung ke Apps Script. Cek URL deployment."
    except Exception as e:
        return f"ERROR: {str(e)}"


def load_data() -> pd.DataFrame:
    """Muat data dari Google Sheets."""
    ws = get_worksheet()
    if ws is None:
        return pd.DataFrame()
    try:
        records = ws.get_all_records()
        return pd.DataFrame(records) if records else pd.DataFrame()
    except Exception as e:
        st.error(f"❌ Gagal memuat data: {e}")
        return pd.DataFrame()


# ==========================================
# SESSION STATE
# ==========================================
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False
if "user_now" not in st.session_state:
    st.session_state["user_now"] = ""

# ==========================================
# SIDEBAR
# ==========================================
with st.sidebar:
    st.markdown("## 📁 Arsip Digital Ngada")
    st.markdown("---")

    if not st.session_state["logged_in"]:
        st.subheader("🔐 Login Admin")
        username_input = st.text_input("Username", key="login_user")
        password_input = st.text_input("Password", type="password", key="login_pw")

        if st.button("Masuk", use_container_width=True, type="primary"):
            if username_input in ADMIN_USERS and ADMIN_USERS[username_input] == password_input:
                st.session_state["logged_in"] = True
                st.session_state["user_now"] = username_input
                st.rerun()
            else:
                st.error("❌ Username atau password salah!")

        st.markdown("---")
        menu = "🗂️ Lihat Data Arsip"
        st.info("💡 Login sebagai admin untuk upload surat.")

    else:
        st.success(f"✅ Login sebagai: **{st.session_state['user_now']}**")
        st.markdown("---")
        menu = st.radio(
            "Menu:",
            ["🗂️ Lihat Data Arsip", "📥 Upload Surat Baru", "📊 Statistik"],
            key="menu_nav"
        )
        st.markdown("---")
        if st.button("🚪 Keluar", use_container_width=True):
            st.session_state["logged_in"] = False
            st.session_state["user_now"] = ""
            st.rerun()

    st.markdown("---")
    st.caption("Sistem Informasi Persuratan\nKabupaten Ngada © 2025")


# ==========================================
# HALAMAN: LIHAT DATA ARSIP
# ==========================================
if menu == "🗂️ Lihat Data Arsip":
    st.markdown("""
    <div class='main-header'>
        <h1>📂 Arsip Surat Digital</h1>
        <p>Kabupaten Ngada — Sistem Manajemen Persuratan</p>
    </div>
    """, unsafe_allow_html=True)

    if gc is None:
        st.error("Koneksi Google gagal. Periksa konfigurasi secrets.")
        st.stop()

    with st.spinner("Memuat data arsip..."):
        df = load_data()

    if df.empty:
        st.markdown("<div class='info-box'>📭 Belum ada data arsip. Silakan upload surat terlebih dahulu.</div>", unsafe_allow_html=True)
    else:
        # Filter & Pencarian
        col_search, col_filter1, col_filter2 = st.columns([3, 1.5, 1.5])
        with col_search:
            search = st.text_input("🔍 Cari nomor surat, perihal, atau pengirim...", placeholder="Ketik kata kunci...")
        with col_filter1:
            jenis_filter = st.selectbox("Jenis Surat", ["Semua", "Surat Masuk", "Surat Keluar"])
        with col_filter2:
            if "Tanggal" in df.columns and not df["Tanggal"].empty:
                tahun_list = ["Semua"] + sorted(df["Tanggal"].astype(str).str[:4].unique().tolist(), reverse=True)
                tahun_filter = st.selectbox("Tahun", tahun_list)
            else:
                tahun_filter = "Semua"

        # Terapkan filter
        df_filtered = df.copy()
        if search:
            mask = df_filtered.astype(str).apply(
                lambda col: col.str.contains(search, case=False, na=False)
            ).any(axis=1)
            df_filtered = df_filtered[mask]
        if jenis_filter != "Semua" and "Jenis" in df_filtered.columns:
            df_filtered = df_filtered[df_filtered["Jenis"] == jenis_filter]
        if tahun_filter != "Semua" and "Tanggal" in df_filtered.columns:
            df_filtered = df_filtered[df_filtered["Tanggal"].astype(str).str.startswith(tahun_filter)]

        # Info jumlah
        st.markdown(f"**Menampilkan {len(df_filtered)} dari {len(df)} data**")

        # Tampilkan tabel
        col_config = {}
        if "Link Drive" in df_filtered.columns:
            col_config["Link Drive"] = st.column_config.LinkColumn("📂 Buka PDF", display_text="Buka ↗")

        st.dataframe(
            df_filtered,
            use_container_width=True,
            hide_index=True,
            column_config=col_config,
            height=450
        )

        # Tombol export
        csv = df_filtered.to_csv(index=False).encode("utf-8")
        st.download_button(
            "⬇️ Ekspor ke CSV",
            data=csv,
            file_name=f"arsip_surat_{time.strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )


# ==========================================
# HALAMAN: UPLOAD SURAT BARU
# ==========================================
elif menu == "📥 Upload Surat Baru" and st.session_state["logged_in"]:
    st.markdown("""
    <div class='main-header'>
        <h1>📥 Upload Surat Baru</h1>
        <p>Tambah arsip surat ke database & Google Drive</p>
    </div>
    """, unsafe_allow_html=True)

    # Cek konfigurasi Apps Script
    if APPS_SCRIPT_URL == "ISI_URL_APPS_SCRIPT_DISINI":
        st.markdown("""
        <div class='warning-box'>
        ⚠️ <strong>Apps Script URL belum dikonfigurasi!</strong><br>
        Tambahkan <code>apps_script_url</code> di <strong>Settings → Secrets</strong> Streamlit Cloud,
        atau isi langsung di kode. Lihat panduan di bawah.
        </div>
        """, unsafe_allow_html=True)

        with st.expander("📖 Cara Setup Apps Script (klik untuk buka)"):
            st.markdown("""
**Langkah 1 — Buat Apps Script:**
1. Buka [script.google.com](https://script.google.com)
2. Klik **New Project**
3. Ganti semua kode dengan kode di bawah ini:

```javascript
function doPost(e) {
  try {
    var params = JSON.parse(e.postData.contents);
    var fileData   = params.fileData;
    var fileName   = params.fileName;
    var mimeType   = params.mimeType || "application/pdf";

    // Ganti ID_FOLDER_DRIVE dengan ID folder tujuan di Google Drive
    var folderId = "ID_FOLDER_DRIVE";
    var folder   = DriveApp.getFolderById(folderId);
    
    var decoded  = Utilities.base64Decode(fileData);
    var blob     = Utilities.newBlob(decoded, mimeType, fileName);
    var file     = folder.createFile(blob);
    
    file.setSharing(DriveApp.Access.ANYONE_WITH_LINK, DriveApp.Permission.VIEW);
    
    var fileUrl = "https://drive.google.com/file/d/" + file.getId() + "/view";
    return ContentService.createTextOutput(fileUrl);
    
  } catch(err) {
    return ContentService.createTextOutput("ERROR: " + err.toString());
  }
}
```

**Langkah 2 — Deploy:**
1. Klik **Deploy → New Deployment**
2. Type: **Web App**
3. Execute as: **Me**
4. Who has access: **Anyone** ← PENTING!
5. Klik **Deploy**, copy URL-nya

**Langkah 3 — Tambahkan ke Streamlit Secrets:**
```toml
apps_script_url = "https://script.google.com/macros/s/XXXX/exec"
google_key = '{"type":"service_account",...}'
```
            """)

    # Form Upload
    with st.form("form_upload_surat", clear_on_submit=True):
        st.subheader("📝 Detail Surat")
        col1, col2 = st.columns(2)

        with col1:
            no_surat      = st.text_input("Nomor Surat *", placeholder="Contoh: 001/DPA/V/2025")
            tgl_surat     = st.date_input("Tanggal Surat *")
            jenis         = st.selectbox("Jenis Surat *", ["Surat Masuk", "Surat Keluar"])

        with col2:
            pengirim_tujuan = st.text_input(
                "Pengirim / Tujuan *",
                placeholder="Surat Masuk: nama pengirim | Surat Keluar: nama tujuan"
            )
            file_pdf = st.file_uploader(
                f"Upload File PDF * (maks. {MAX_FILE_SIZE_MB} MB)",
                type=["pdf"],
                help="PDF hasil scan atau digital. Pastikan ukuran file tidak melebihi batas."
            )

        perihal = st.text_area(
            "Perihal / Ringkasan Surat *",
            placeholder="Tuliskan perihal atau ringkasan isi surat...",
            height=100
        )

        st.markdown("---")
        submitted = st.form_submit_button("🚀 Simpan ke Database & Drive", use_container_width=True, type="primary")

    # Proses Submit
    if submitted:
        errors = []
        if not no_surat.strip():
            errors.append("Nomor Surat wajib diisi.")
        if not pengirim_tujuan.strip():
            errors.append("Pengirim/Tujuan wajib diisi.")
        if not perihal.strip():
            errors.append("Perihal surat wajib diisi.")
        if file_pdf is None:
            errors.append("File PDF wajib dilampirkan.")

        if errors:
            for err in errors:
                st.warning(f"⚠️ {err}")
        else:
            file_bytes = file_pdf.read()
            size_mb = len(file_bytes) / (1024 * 1024)

            if size_mb > MAX_FILE_SIZE_MB:
                st.error(f"❌ File terlalu besar: {size_mb:.1f} MB. Maksimal {MAX_FILE_SIZE_MB} MB. Kompres PDF-nya terlebih dahulu.")
            else:
                progress_bar = st.progress(0, text="Memulai proses...")

                # Step 1: Upload ke Drive
                progress_bar.progress(20, text="📤 Mengupload PDF ke Google Drive...")
                link_pdf = upload_ke_drive(file_bytes, file_pdf.name)

                if link_pdf.startswith("ERROR"):
                    progress_bar.empty()
                    st.error(f"❌ Gagal upload ke Drive:\n\n{link_pdf}")
                    st.markdown("""
                    <div class='warning-box'>
                    💡 <strong>Tips debugging:</strong><br>
                    • Pastikan URL Apps Script sudah benar dan di-deploy ulang jika ada perubahan<br>
                    • Pastikan <em>Who has access: Anyone</em> saat deploy<br>
                    • Coba buka URL Apps Script di browser untuk cek apakah aktif<br>
                    • Cek ID folder Google Drive sudah benar di kode Apps Script
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    # Step 2: Simpan ke Sheets
                    progress_bar.progress(70, text="📊 Menyimpan ke Google Sheets...")
                    ws = get_worksheet()
                    if ws:
                        baris_baru = [
                            no_surat.strip(),
                            tgl_surat.strftime("%Y-%m-%d"),
                            jenis,
                            perihal.strip(),
                            pengirim_tujuan.strip(),
                            link_pdf,
                            st.session_state["user_now"],
                            time.strftime("%Y-%m-%d %H:%M:%S")
                        ]
                        try:
                            ws.append_row(baris_baru)
                            progress_bar.progress(100, text="✅ Selesai!")
                            time.sleep(0.5)
                            progress_bar.empty()
                            st.success(f"✅ **Berhasil!** Surat **{no_surat}** sudah tersimpan di database dan Google Drive.")
                            st.markdown(f"📂 [Klik di sini untuk membuka PDF]({link_pdf})")
                            st.balloons()
                        except Exception as e:
                            progress_bar.empty()
                            st.error(f"❌ PDF berhasil diupload ke Drive, tapi gagal simpan ke Sheets: {e}")
                    else:
                        progress_bar.empty()
                        st.error("❌ Gagal membuka Google Sheets.")


# ==========================================
# HALAMAN: STATISTIK
# ==========================================
elif menu == "📊 Statistik" and st.session_state["logged_in"]:
    st.markdown("""
    <div class='main-header'>
        <h1>📊 Statistik Arsip</h1>
        <p>Ringkasan data persuratan</p>
    </div>
    """, unsafe_allow_html=True)

    with st.spinner("Memuat data..."):
        df = load_data()

    if df.empty:
        st.info("Belum ada data untuk ditampilkan.")
    else:
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Surat", len(df))
        with col2:
            masuk = len(df[df["Jenis"] == "Surat Masuk"]) if "Jenis" in df.columns else 0
            st.metric("Surat Masuk", masuk)
        with col3:
            keluar = len(df[df["Jenis"] == "Surat Keluar"]) if "Jenis" in df.columns else 0
            st.metric("Surat Keluar", keluar)

        if "Jenis" in df.columns:
            st.subheader("Distribusi Jenis Surat")
            jenis_count = df["Jenis"].value_counts()
            st.bar_chart(jenis_count)

        if "Tanggal" in df.columns:
            st.subheader("Surat per Bulan")
            df_temp = df.copy()
            df_temp["Bulan"] = pd.to_datetime(df_temp["Tanggal"], errors="coerce").dt.to_period("M").astype(str)
            bulan_count = df_temp["Bulan"].value_counts().sort_index()
            st.bar_chart(bulan_count)
