"""
=============================================================
 SISTEM FILTER FOTO BUKTI PEMBAYARAN GOPAY
 Memfilter foto bukti pembayaran berdasarkan kriteria:
 1. Penerima = GoPay (e-wallet)
 2. Teks mengandung "PB MPKMB DRAMAGA"
=============================================================
"""

import os
import sys
import shutil
import time
import cv2
import numpy as np
from PIL import Image
from pyzbar.pyzbar import decode as decode_qr
import easyocr

# ===================== KONFIGURASI =====================

# Kata kunci untuk mendeteksi GoPay sebagai penerima (exact phrases)
GOPAY_RECEIVER_KEYWORDS = [
    "ditransfer ke gopay", "penerima gopay", "penerima: gopay",
    "ke gopay", "tujuan gopay", "tujuan: gopay", "transfer ke gopay"
]

# Kata kunci untuk GoPay secara umum
GOPAY_GENERAL = ["gopay", "go-pay", "go pay", "g0pay"]

# Kata kunci indikasi pengirim GoPay (harus dihindari jika ingin mencari penerima GoPay)
GOPAY_SENDER_KEYWORDS = [
    "pengirim gopay", "dari gopay", "dari: gopay", 
    "metode pembayaran gopay", "sumber dana gopay"
]

# Kata kunci untuk mendeteksi PB MPKMB DRAMAGA
MPKMB_KEYWORDS = [
    "pb mpkmb", "mpkmb dramaga", "pb mpkmb dramaga",
    "pb mpkmb, dramaga", "mpkmb, dramaga",
    "pbmpkmb", "mpkmbdramaga",
]

# Ekstensi file gambar yang didukung
SUPPORTED_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif', '.webp'}

# ===================== FUNGSI PREPROCESSING =====================

def preprocess_image(image):
    """
    Preprocessing gambar untuk meningkatkan akurasi OCR.
    Menghasilkan beberapa versi preprocessed image.
    """
    results = []

    # 1. Grayscale original
    if len(image.shape) == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image.copy()
    results.append(gray)

    # 2. Adaptive threshold (baik untuk teks pada background yang tidak rata)
    adaptive = cv2.adaptiveThreshold(
        gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY, 11, 2
    )
    results.append(adaptive)

    # 3. OTSU threshold (baik untuk teks kontras tinggi)
    _, otsu = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    results.append(otsu)

    # 4. Contrast enhancement (CLAHE)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(gray)
    results.append(enhanced)

    return results


def resize_if_needed(image, max_dimension=1600):
    """
    Resize gambar jika terlalu besar untuk mempercepat proses OCR.
    """
    h, w = image.shape[:2]
    if max(h, w) > max_dimension:
        scale = max_dimension / max(h, w)
        new_w = int(w * scale)
        new_h = int(h * scale)
        image = cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_AREA)
    return image


# ===================== FUNGSI DETEKSI =====================

def extract_text_ocr(reader, image):
    """
    Ekstraksi teks dari gambar menggunakan EasyOCR.
    Mencoba beberapa versi preprocessed image untuk hasil terbaik.
    """
    all_texts = []

    # Resize untuk mempercepat processing
    image = resize_if_needed(image)

    # Dapatkan versi preprocessed
    preprocessed_images = preprocess_image(image)

    # OCR pada gambar original (grayscale)
    try:
        results = reader.readtext(preprocessed_images[0], detail=0, paragraph=True)
        all_texts.extend(results)
    except Exception as e:
        pass

    # Jika hasil kurang, coba versi enhanced contrast
    if len(all_texts) < 3:
        try:
            results = reader.readtext(preprocessed_images[3], detail=0, paragraph=True)
            all_texts.extend(results)
        except Exception:
            pass

    return all_texts


def decode_qr_codes(image):
    """
    Decode semua QR code yang ditemukan pada gambar.
    Mengembalikan list string data dari QR code.
    """
    qr_data = []

    # Resize untuk processing
    image = resize_if_needed(image)

    # Dapatkan versi preprocessed
    preprocessed_images = preprocess_image(image)

    for preprocessed in preprocessed_images:
        try:
            decoded_objects = decode_qr(preprocessed)
            for obj in decoded_objects:
                try:
                    data = obj.data.decode('utf-8')
                    qr_data.append(data)
                except (UnicodeDecodeError, AttributeError):
                    try:
                        data = obj.data.decode('latin-1')
                        qr_data.append(data)
                    except Exception:
                        pass
        except Exception:
            pass

    return list(set(qr_data))


def check_gopay_recipient(texts, qr_data):
    """
    Cek apakah penerima pembayaran adalah GoPay.
    Memastikan GoPay sebagai penerima, bukan pengirim.
    Mencari di hasil OCR dan QR code data.
    """
    # Gabungkan semua teks menjadi satu string lowercase
    combined_text = " ".join(texts).lower()
    combined_qr = " ".join(qr_data).lower()
    all_text = combined_text + " " + combined_qr
    
    # Hapus spasi ganda yang mungkin terjadi
    cleaned_text = " ".join(all_text.split())

    # 1. Cek dari frase exact match yang menunjukkan tujuan
    for keyword in GOPAY_RECEIVER_KEYWORDS:
        if keyword in cleaned_text:
            return True, keyword

    # 2. Jika ada kata Gopay, cek konteks lebih lanjut
    is_gopay_present = any(g in cleaned_text for g in GOPAY_GENERAL)
    if is_gopay_present:
        is_sender = any(s in cleaned_text for s in GOPAY_SENDER_KEYWORDS)
        
        # Jika bukan pengirim explisit yang mengandung kata gopay, 
        # kita cek apakah ada indikator penerima di teks
        has_receiver_context = any(r in cleaned_text for r in ["penerima", "ditransfer ke", "tujuan"])
        has_sender_context = any(r in cleaned_text for r in ["pengirim", "dari", "sumber dana"])
        
        if has_receiver_context and not is_sender:
            return True, "gopay (terdeteksi sebagai penerima secara konteks)"

    return False, None


def check_mpkmb_text(texts, qr_data):
    """
    Cek apakah teks "PB MPKMB DRAMAGA" ada di bukti pembayaran.
    Mencari di hasil OCR dan QR code data.
    """
    # Gabungkan semua teks
    combined_text = " ".join(texts).lower()
    combined_qr = " ".join(qr_data).lower()
    all_text = combined_text + " " + combined_qr

    # Hapus karakter spesial untuk fuzzy matching
    cleaned_text = all_text.replace(",", " ").replace(".", " ").replace("-", " ")
    # Normalisasi spasi berlebih
    cleaned_text = " ".join(cleaned_text.split())

    for keyword in MPKMB_KEYWORDS:
        if keyword in cleaned_text:
            return True, keyword

    return False, None


# ===================== FUNGSI UTAMA =====================

def scan_images(input_folder):
    """
    Scan folder dan kembalikan daftar file gambar yang valid.
    """
    images = []
    for filename in os.listdir(input_folder):
        ext = os.path.splitext(filename)[1].lower()
        if ext in SUPPORTED_EXTENSIONS:
            images.append(os.path.join(input_folder, filename))
    return sorted(images)


def process_single_image(reader, image_path):
    """
    Proses satu gambar dan cek apakah memenuhi kedua kriteria.
    Returns: (is_match, gopay_found, mpkmb_found, details)
    """
    try:
        # Baca gambar
        image = cv2.imread(image_path)
        if image is None:
            return False, False, False, "Gagal membaca gambar"

        # Ekstraksi teks OCR
        texts = extract_text_ocr(reader, image)

        # Decode QR codes
        qr_data = decode_qr_codes(image)

        # Cek kriteria 1: GoPay sebagai penerima
        gopay_found, gopay_keyword = check_gopay_recipient(texts, qr_data)

        # Cek kriteria 2: PB MPKMB DRAMAGA
        mpkmb_found, mpkmb_keyword = check_mpkmb_text(texts, qr_data)

        # Detail hasil
        details = {
            "ocr_texts": texts,
            "qr_data": qr_data,
            "gopay_keyword": gopay_keyword,
            "mpkmb_keyword": mpkmb_keyword,
        }

        # Gambar lolos jika SALAH SATU kriteria terpenuhi (GoPay ATAU MPKMB)
        is_match = gopay_found or mpkmb_found

        return is_match, gopay_found, mpkmb_found, details

    except Exception as e:
        return False, False, False, f"Error: {str(e)}"


def filter_images(input_folder, output_folder):
    """
    Fungsi utama: filter seluruh gambar di folder input.
    Salin gambar yang lolos ke folder output.
    """
    print("=" * 60)
    print("  SISTEM FILTER BUKTI PEMBAYARAN GOPAY")
    print("  Kriteria: GoPay + PB MPKMB DRAMAGA")
    print("=" * 60)
    print()

    # Validasi folder input
    if not os.path.isdir(input_folder):
        print(f"[ERROR] Folder input tidak ditemukan: {input_folder}")
        sys.exit(1)

    # Buat folder output jika belum ada
    os.makedirs(output_folder, exist_ok=True)

    # Scan gambar
    print(f"[INFO] Scanning folder: {input_folder}")
    image_files = scan_images(input_folder)
    total_images = len(image_files)

    if total_images == 0:
        print("[ERROR] Tidak ada file gambar yang ditemukan di folder input!")
        sys.exit(1)

    print(f"[INFO] Ditemukan {total_images} gambar")
    print(f"[INFO] Folder output: {output_folder}")
    print()

    # Inisialisasi EasyOCR Reader (CPU mode)
    print("[INFO] Memuat model OCR (mungkin butuh waktu saat pertama kali)...")
    reader = easyocr.Reader(['id', 'en'], gpu=False, verbose=False)
    print("[INFO] Model OCR siap!")
    print()

    # Proses setiap gambar
    matched_files = []
    gopay_only = []
    mpkmb_only = []
    failed_files = []

    start_time = time.time()

    for idx, image_path in enumerate(image_files, 1):
        filename = os.path.basename(image_path)
        progress = f"[{idx}/{total_images}]"

        print(f"{progress} Memproses: {filename}...", end=" ", flush=True)

        img_start = time.time()
        is_match, gopay_found, mpkmb_found, details = process_single_image(reader, image_path)
        img_time = time.time() - img_start

        if is_match:
            # Salin ke folder output
            dest_path = os.path.join(output_folder, filename)
            # Hindari overwrite jika nama file sama
            if os.path.exists(dest_path):
                name, ext = os.path.splitext(filename)
                dest_path = os.path.join(output_folder, f"{name}_{idx}{ext}")
            shutil.copy2(image_path, dest_path)
            matched_files.append(filename)
            print(f"✅ COCOK! (GoPay: '{details['gopay_keyword']}', "
                  f"MPKMB: '{details['mpkmb_keyword']}') [{img_time:.1f}s]")
        elif gopay_found and not mpkmb_found:
            gopay_only.append(filename)
            print(f"⚠️  GoPay ditemukan, MPKMB tidak ditemukan [{img_time:.1f}s]")
        elif mpkmb_found and not gopay_found:
            mpkmb_only.append(filename)
            print(f"⚠️  MPKMB ditemukan, GoPay tidak ditemukan [{img_time:.1f}s]")
        elif isinstance(details, str) and details.startswith("Error"):
            failed_files.append((filename, details))
            print(f"❌ {details} [{img_time:.1f}s]")
        else:
            print(f"❌ Tidak cocok [{img_time:.1f}s]")

    # Statistik akhir
    elapsed = time.time() - start_time
    minutes = int(elapsed // 60)
    seconds = int(elapsed % 60)

    print()
    print("=" * 60)
    print("  HASIL FILTER")
    print("=" * 60)
    print(f"  Total gambar diproses  : {total_images}")
    print(f"  ✅ Lolos filter (cocok) : {len(matched_files)}")
    print(f"  ⚠️  Hanya GoPay         : {len(gopay_only)}")
    print(f"  ⚠️  Hanya MPKMB         : {len(mpkmb_only)}")
    print(f"  ❌ Tidak cocok          : {total_images - len(matched_files) - len(gopay_only) - len(mpkmb_only) - len(failed_files)}")
    print(f"  ❌ Error                : {len(failed_files)}")
    print(f"  Waktu total            : {minutes}m {seconds}s")
    print(f"  Output disimpan di     : {output_folder}")
    print("=" * 60)

    if matched_files:
        print()
        print("  Daftar file yang lolos filter:")
        for i, f in enumerate(matched_files, 1):
            print(f"    {i}. {f}")

    if gopay_only:
        print()
        print("  File dengan GoPay tapi tanpa MPKMB (mungkin perlu dicek manual):")
        for i, f in enumerate(gopay_only, 1):
            print(f"    {i}. {f}")

    if mpkmb_only:
        print()
        print("  File dengan MPKMB tapi tanpa GoPay (mungkin perlu dicek manual):")
        for i, f in enumerate(mpkmb_only, 1):
            print(f"    {i}. {f}")

    if failed_files:
        print()
        print("  File yang gagal diproses:")
        for i, (f, err) in enumerate(failed_files, 1):
            print(f"    {i}. {f} - {err}")

    print()
    print("Selesai! 🎉")

    return matched_files


# ===================== ENTRY POINT =====================

if __name__ == "__main__":
    print()

    if len(sys.argv) >= 2:
        INPUT_FOLDER = sys.argv[1]
    else:
        INPUT_FOLDER = input("Masukkan path folder foto input: ").strip().strip('"')

    if len(sys.argv) >= 3:
        OUTPUT_FOLDER = sys.argv[2]
    else:
        default_output = os.path.join(os.path.dirname(INPUT_FOLDER), "output_gopay_mpkmb")
        user_output = input(f"Masukkan path folder output (Enter untuk default '{default_output}'): ").strip().strip('"')
        OUTPUT_FOLDER = user_output if user_output else default_output

    print()
    filter_images(INPUT_FOLDER, OUTPUT_FOLDER)
