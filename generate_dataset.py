import os
import sys
import qrcode
from PIL import Image, ImageDraw, ImageFont, ImageFilter

sys.stdout.reconfigure(encoding='utf-8')

# Ensure dataset directory exists
DATASET_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "dataset"))
os.makedirs(DATASET_DIR, exist_ok=True)

# -----------------------------------------------------------------------------
# Verhoeff Checksum Generator
# -----------------------------------------------------------------------------
VERHOEFF_D = [
    [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
    [1, 2, 3, 4, 0, 6, 7, 8, 9, 5],
    [2, 3, 4, 0, 1, 7, 8, 9, 5, 6],
    [3, 4, 0, 1, 2, 8, 9, 5, 6, 7],
    [4, 0, 1, 2, 3, 9, 5, 6, 7, 8],
    [5, 9, 8, 7, 6, 0, 4, 3, 2, 1],
    [6, 5, 9, 8, 7, 1, 0, 4, 3, 2],
    [7, 6, 5, 9, 8, 2, 1, 0, 4, 3],
    [8, 7, 6, 5, 9, 3, 2, 1, 0, 4],
    [9, 8, 7, 6, 5, 4, 3, 2, 1, 0]
]
VERHOEFF_P = [
    [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
    [1, 5, 7, 6, 2, 8, 3, 0, 9, 4],
    [5, 8, 0, 3, 7, 9, 6, 1, 4, 2],
    [8, 9, 1, 6, 0, 4, 3, 5, 2, 7],
    [9, 4, 5, 3, 1, 2, 6, 8, 7, 0],
    [4, 2, 8, 6, 5, 7, 3, 9, 0, 1],
    [2, 7, 9, 3, 8, 0, 6, 4, 1, 5],
    [7, 0, 4, 6, 9, 1, 3, 2, 5, 8]
]
VERHOEFF_INV = [0, 4, 3, 2, 1, 5, 6, 7, 8, 9]

def make_valid_aadhaar(prefix_11: str) -> str:
    c = 0
    digits = [int(x) for x in prefix_11]
    for i, digit in enumerate(reversed(digits)):
        c = VERHOEFF_D[c][VERHOEFF_P[(i + 1) % 8][digit]]
    return prefix_11 + str(VERHOEFF_INV[c])


# -----------------------------------------------------------------------------
# SPECIMEN 1: Genuine Aadhaar Card (100% Compliant)
# -----------------------------------------------------------------------------
def build_genuine_aadhaar():
    uid_raw = make_valid_aadhaar("98234561789")  # 9823 4561 7894
    uid_formatted = f"{uid_raw[:4]} {uid_raw[4:8]} {uid_raw[8:]}"
    name = "Ananya Sharma"
    dob = "14/08/1998"
    gender = "FEMALE"

    # 1. Canvas
    img = Image.new("RGB", (960, 600), "#FAF9F6")
    draw = ImageDraw.Draw(img)

    # Header bar
    draw.rectangle([(0, 0), (960, 90)], fill="#872929")
    draw.rectangle([(0, 90), (960, 96)], fill="#F2A900")

    # Titles
    draw.text((40, 25), "भारत सरकार", fill="#FFFFFF")
    draw.text((40, 52), "GOVERNMENT OF INDIA", fill="#FFFFFF")
    draw.text((680, 40), "UNIQUE IDENTIFICATION AUTHORITY OF INDIA", fill="#FFFFFF")

    # Profile placeholder
    draw.rectangle([(50, 140), (220, 360)], fill="#E0DCD3", outline="#74796E", width=2)
    draw.ellipse([(95, 175), (175, 255)], fill="#B5ADA4")
    draw.ellipse([(70, 275), (200, 390)], fill="#8E857B")

    # Demographic visual fields
    draw.text((250, 160), "Name / नाम :", fill="#555555")
    draw.text((370, 158), name, fill="#1A1A1A")

    draw.text((250, 205), "DOB / जन्म तिथि :", fill="#555555")
    draw.text((390, 203), dob, fill="#1A1A1A")

    draw.text((250, 250), "Gender / लिंग :", fill="#555555")
    draw.text((380, 248), gender, fill="#1A1A1A")

    # Aadhaar Number
    draw.text((270, 420), uid_formatted, fill="#990000")
    draw.text((290, 480), "मेरा आधार, मेरी पहचान", fill="#555555")

    # Official XML QR Code
    qr_payload = f'<PrintLetterBarcodeData uid="{uid_raw}" name="{name}" gender="F" yob="1998" dob="{dob}" co="D/O Rajesh Sharma" dist="Hyderabad" state="Telangana" pc="500081"/>'
    qr_img = qrcode.make(qr_payload).resize((220, 220))
    img.paste(qr_img, (680, 150))

    # Border
    draw.rectangle([(0, 0), (959, 599)], outline="#990000", width=3)

    out_path = os.path.join(DATASET_DIR, "specimen_genuine_aadhaar.png")
    img.save(out_path, "PNG")
    print(f"[OK] Generated: {out_path} (UID: {uid_formatted}, Status: AUTHENTIC)")


# -----------------------------------------------------------------------------
# SPECIMEN 2: Tampered Aadhaar Card (Photoshop / Tampering Vector)
# -----------------------------------------------------------------------------
def build_tampered_aadhaar():
    # Base from genuine card
    uid_valid = make_valid_aadhaar("98234561789")
    img = Image.new("RGB", (960, 600), "#FAF9F6")
    draw = ImageDraw.Draw(img)

    # Header
    draw.rectangle([(0, 0), (960, 90)], fill="#872929")
    draw.rectangle([(0, 90), (960, 96)], fill="#F2A900")
    draw.text((40, 25), "भारत सरकार", fill="#FFFFFF")
    draw.text((40, 52), "GOVERNMENT OF INDIA", fill="#FFFFFF")

    # Profile placeholder
    draw.rectangle([(50, 140), (220, 360)], fill="#D0C8B8", outline="#74796E", width=2)
    draw.ellipse([(95, 175), (175, 255)], fill="#7A6855")

    # Tampering Attack 1: Altered visual text ("Vikram Malhotra" instead of "Ananya Sharma")
    draw.text((250, 160), "Name / नाम :", fill="#555555")
    # Paste a slightly mismatched white patch over the name (simulates digital paste/splice)
    draw.rectangle([(365, 150), (580, 185)], fill="#FFFFFF", outline="#FFB3BA", width=1)
    draw.text((370, 158), "Vikram Malhotra", fill="#000080")

    draw.text((250, 205), "DOB / जन्म तिथि :", fill="#555555")
    draw.text((390, 203), "01/01/1990", fill="#1A1A1A")  # Conflicting DOB

    draw.text((250, 250), "Gender / लिंग :", fill="#555555")
    draw.text((380, 248), "MALE", fill="#1A1A1A")

    # Tampering Attack 2: Broken Verhoeff Check Digit (changed last digit 4 -> 7)
    corrupted_uid = uid_valid[:-1] + "7"
    corrupted_formatted = f"{corrupted_uid[:4]} {corrupted_uid[4:8]} {corrupted_uid[8:]}"
    draw.text((270, 420), corrupted_formatted, fill="#990000")

    # The QR barcode is the UNALTERED original for Ananya Sharma
    # This creates a fatal cross-modal mismatch (Name: Vikram vs Ananya, Gender: M vs F, UID corrupted)
    qr_payload = f'<PrintLetterBarcodeData uid="{uid_valid}" name="Ananya Sharma" gender="F" dob="14/08/1998"/>'
    qr_img = qrcode.make(qr_payload).resize((220, 220))
    img.paste(qr_img, (680, 150))

    # Border
    draw.rectangle([(0, 0), (959, 599)], outline="#990000", width=3)

    out_path = os.path.join(DATASET_DIR, "specimen_tampered_aadhaar.png")
    img.save(out_path, "PNG")
    print(f"[OK] Generated: {out_path} (UID: {corrupted_formatted}, Status: TAMPERED FORGERY)")


# -----------------------------------------------------------------------------
# SPECIMEN 3: Genuine PAN Card (CBDT Compliant)
# -----------------------------------------------------------------------------
def build_genuine_pan():
    pan = "ABCPS1234F"  # 4th letter 'P' (Person/Individual), 5th letter 'S' (Sharma)
    name = "ARUN KUMAR SHARMA"
    fname = "RAMESH SHARMA"
    dob = "12/04/1988"

    img = Image.new("RGB", (960, 600), "#EBF2F7")
    draw = ImageDraw.Draw(img)

    # Top Header
    draw.rectangle([(0, 0), (960, 95)], fill="#003366")
    draw.text((40, 20), "आयकर विभाग / INCOME TAX DEPARTMENT", fill="#FFFFFF")
    draw.text((40, 55), "भारत सरकार / GOVT. OF INDIA", fill="#FFFFFF")

    # Permanent Account Number Card banner
    draw.rectangle([(0, 95), (960, 125)], fill="#006699")
    draw.text((340, 102), "Permanent Account Number Card", fill="#FFFFFF")

    # Photo Box
    draw.rectangle([(60, 160), (220, 360)], fill="#DCE5EB", outline="#003366", width=2)
    draw.ellipse([(100, 190), (180, 270)], fill="#7F94A3")

    # Fields
    draw.text((250, 160), "Name :", fill="#444444")
    draw.text((250, 185), name, fill="#111111")

    draw.text((250, 225), "Father's Name :", fill="#444444")
    draw.text((250, 250), fname, fill="#111111")

    draw.text((250, 290), "Date of Birth :", fill="#444444")
    draw.text((250, 315), dob, fill="#111111")

    draw.text((250, 370), "Permanent Account Number :", fill="#003366")
    draw.text((250, 400), pan, fill="#B30000")

    # Valid CBDT QR Code
    qr_payload = f"PAN:{pan};Name:{name};Father:{fname};DOB:{dob};Cat:Individual"
    qr_img = qrcode.make(qr_payload).resize((220, 220))
    img.paste(qr_img, (680, 170))

    # Border
    draw.rectangle([(0, 0), (959, 599)], outline="#003366", width=3)

    out_path = os.path.join(DATASET_DIR, "specimen_genuine_pan.png")
    img.save(out_path, "PNG")
    print(f"[OK] Generated: {out_path} (PAN: {pan}, Status: AUTHENTIC)")


# -----------------------------------------------------------------------------
# SPECIMEN 4: Fraudulent PAN Card (Syntax Anomaly & Impossible Date)
# -----------------------------------------------------------------------------
def build_tampered_pan():
    pan_fraud = "AB99X1234F"  # Invalid syntax: numbers in alphabetic block, 'X' unknown entity
    name = "VIKRAM SINGH"
    fname = "SURESH SINGH"
    dob_invalid = "31/02/1985"  # Impossible calendar date

    img = Image.new("RGB", (960, 600), "#EBF2F7")
    draw = ImageDraw.Draw(img)

    # Top Header
    draw.rectangle([(0, 0), (960, 95)], fill="#003366")
    draw.text((40, 20), "आयकर विभाग / INCOME TAX DEPARTMENT", fill="#FFFFFF")
    draw.text((40, 55), "भारत सरकार / GOVT. OF INDIA", fill="#FFFFFF")

    # Photo Box
    draw.rectangle([(60, 160), (220, 360)], fill="#DCE5EB", outline="#003366", width=2)
    draw.ellipse([(100, 190), (180, 270)], fill="#996666")

    # Digital patch artifact over name
    draw.rectangle([(245, 175), (500, 210)], fill="#FFFFFF", outline="#E57373", width=1)
    draw.text((250, 185), name, fill="#880000")

    draw.text((250, 225), "Father's Name :", fill="#444444")
    draw.text((250, 250), fname, fill="#111111")

    # Impossible Date
    draw.text((250, 290), "Date of Birth :", fill="#444444")
    draw.text((250, 315), dob_invalid, fill="#B30000")

    # Fraudulent PAN Syntax
    draw.text((250, 370), "Permanent Account Number :", fill="#003366")
    draw.text((250, 400), pan_fraud, fill="#B30000")

    # QR Code encodes completely different taxpayer
    qr_payload = f"PAN:XYZPA9999Z;Name:RAJESH GUPTA;DOB:15/05/1975"
    qr_img = qrcode.make(qr_payload).resize((220, 220))
    img.paste(qr_img, (680, 170))

    # Border
    draw.rectangle([(0, 0), (959, 599)], outline="#003366", width=3)

    out_path = os.path.join(DATASET_DIR, "specimen_tampered_pan.png")
    img.save(out_path, "PNG")
    print(f"[OK] Generated: {out_path} (PAN: {pan_fraud}, Status: SYNTAX FRAUD)")


# -----------------------------------------------------------------------------
# SPECIMEN 5: Genuine Republic of India Passport (ICAO 9303 Compliant)
# -----------------------------------------------------------------------------
def build_genuine_passport():
    name = "SHARMA RAHUL"
    pass_no = "M8923481"
    dob = "12/04/1995"
    exp = "12/04/2030"
    
    img = Image.new("RGB", (960, 650), "#F5EFE6")
    draw = ImageDraw.Draw(img)

    # Passport Header
    draw.rectangle([(0, 0), (960, 90)], fill="#1E293B")
    draw.text((40, 25), "पासपोर्ट / PASSPORT", fill="#FFFFFF")
    draw.text((40, 55), "भारत गणराज्य / REPUBLIC OF INDIA", fill="#FFFFFF")

    # Photo Box
    draw.rectangle([(50, 130), (230, 360)], fill="#E2E8F0", outline="#475569", width=2)
    draw.ellipse([(95, 160), (185, 250)], fill="#94A3B8")
    draw.ellipse([(70, 270), (210, 380)], fill="#64748B")

    # Visual Text
    draw.text((270, 130), "Type / प्रकार :", fill="#64748B")
    draw.text((370, 130), "P", fill="#0F172A")

    draw.text((500, 130), "Country Code :", fill="#64748B")
    draw.text((620, 130), "IND", fill="#0F172A")

    draw.text((270, 170), "Passport No. / पासपोर्ट नं. :", fill="#64748B")
    draw.text((470, 168), pass_no, fill="#B91C1C")

    draw.text((270, 210), "Given Name(s) / नाम :", fill="#64748B")
    draw.text((450, 208), name, fill="#0F172A")

    draw.text((270, 250), "Nationality / राष्ट्रीयता :", fill="#64748B")
    draw.text((450, 248), "INDIAN", fill="#0F172A")

    draw.text((270, 290), "Date of Birth / जन्म तिथि :", fill="#64748B")
    draw.text((470, 288), dob, fill="#0F172A")

    draw.text((270, 330), "Date of Expiry / समाप्ति तिथि :", fill="#64748B")
    draw.text((490, 328), exp, fill="#0F172A")

    # Machine Readable Zone (MRZ 2 lines according to ICAO 9303)
    draw.rectangle([(20, 480), (940, 620)], fill="#FFFFFF", outline="#CBD5E1", width=2)
    mrz_line1 = "P<INDSHARMA<<RAHUL<<<<<<<<<<<<<<<<<<<<<<<<<<"
    mrz_line2 = "M8923481<3IND9504121M3004124<<<<<<<<<<<<<<0"
    draw.text((40, 510), mrz_line1, fill="#0F172A")
    draw.text((40, 560), mrz_line2, fill="#0F172A")

    # Outer border
    draw.rectangle([(0, 0), (959, 649)], outline="#1E293B", width=3)

    out_path = os.path.join(DATASET_DIR, "specimen_genuine_passport.png")
    img.save(out_path, "PNG")
    print(f"[OK] Generated: {out_path} (Passport: {pass_no}, Status: ICAO COMPLIANT)")


# -----------------------------------------------------------------------------
# SPECIMEN 6: Degraded / Blurred Card (Tests Optical Quality Gate)
# -----------------------------------------------------------------------------
def build_blurred_specimen():
    base_path = os.path.join(DATASET_DIR, "specimen_genuine_aadhaar.png")
    if not os.path.exists(base_path):
        build_genuine_aadhaar()
    
    img = Image.open(base_path)
    # Apply heavy Gaussian blur to push Laplacian variance blur score below 15.0
    blurred = img.filter(ImageFilter.GaussianBlur(radius=7.5))
    
    out_path = os.path.join(DATASET_DIR, "specimen_blurred_document.png")
    blurred.save(out_path, "PNG")
    print(f"[OK] Generated: {out_path} (Status: INTENTIONAL QUALITY GATE FAILURE)")


if __name__ == "__main__":
    print("====================================================")
    print("      VERIDOC BENCHMARK DATASET GENERATOR           ")
    print("====================================================")
    build_genuine_aadhaar()
    build_tampered_aadhaar()
    build_genuine_pan()
    build_tampered_pan()
    build_genuine_passport()
    build_blurred_specimen()
    print("====================================================")
    print("All 6 benchmark specimens successfully generated in:")
    print(DATASET_DIR)
    print("====================================================")
