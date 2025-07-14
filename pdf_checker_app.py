import streamlit as st
import pdfplumber
import requests
import re

# List of known materials for matching
MATERIAL_KEYWORDS = [
    "CORRUGATED", "MESH COATED", "PVC BLACK WHITE MATTE", "MAGNETIC PRINT", "CORREX",
    "TEAR RESISTANT SATIN", "VINYL POLYMERIC", "FABRIC FRONTLIT", "VINYL WHITE GLOSS",
    "VINYL ONE WAY VISION", "FOAM PVC", "ACRYLIC XT CLEAR", "VINYL CAST", "WALLPAPER",
    "STYRENE", "FABRIWALL", "FABRIC BACKLIT", "FILM BACKLIT", "HI Q", "CHROMADECK",
    "VINYL FROSTED", "WOOD (MDF)", "PE BLACK WHITE", "PP SILICONE WINDOW FILM",
    "VINYL EASYDOT", "TRANSFER PAPER", "APET CLEAR", "VINYL WALL OUTDOOR", "KRAFTBOARD",
    "BIE-VINYL", "MAGNETIC FERRIS PAPER", "VINYL- WINDOW- FLUX", "HI-Q Titan Gloss",
    "PVC BACKLIT", "MESH COATED (Large perforation)", "WALLPAPER- FINE SAND TEXTURED",
    "B-SILKYSMOOTH WALLCOVERING", "B-WALLCOVERING-CANVAS PREMIUM", "WALLPAPER- (B TEX)",
    "VINYL POLYMERIC B/ O WHITE GLOSS", "FABRIC WHITE BLACK", "FABRIC BACKLIT (LED)",
    "FABRIC TEXTILE BACKLIT (LED)", "TEAR RESISTANT SATIN PREMIUM", "MAGNETIC PRINT 0.6MM"
]

def extract_text_layer(uploaded_pdf):
    with pdfplumber.open(uploaded_pdf) as pdf:
        return "\n".join([p.extract_text() or "" for p in pdf.pages])

def extract_text_via_ocr_api(uploaded_pdf):
    OCR_API_KEY = "helloworld"  # Replace with a real key if needed
    uploaded_pdf.seek(0)
    response = requests.post(
        "https://api.ocr.space/parse/image",
        files={"file": uploaded_pdf},
        data={
            "language": "eng",
            "isOverlayRequired": False,
            "apikey": OCR_API_KEY,
        },
    )
    result = response.json()
    if result.get("IsErroredOnProcessing"):
        return ""
    return result["ParsedResults"][0]["ParsedText"]

def normalize_size_for_scale(size_mm, scale_percent):
    return (size_mm[0] * scale_percent / 100, size_mm[1] * scale_percent / 100)

def fuzzy_match_material(text):
    text_lower = text.lower()
    for material in MATERIAL_KEYWORDS:
        keywords = material.lower().split()
        if all(kw in text_lower for kw in keywords[:2]):
            return material
    return None

def parse_header(header_line):
    size_matches = re.findall(r"(\d{2,5})\s*[xX]\s*(\d{2,5})", header_line)
    selected_size = None
    if size_matches:
        selected_size = max(size_matches, key=lambda s: int(s[0]) * int(s[1]))

    bleed_match = re.search(r"(\d{1,3})mm(?:\s*BLEED)?", header_line, re.IGNORECASE)
    material_match = fuzzy_match_material(header_line)

    return {
        "size": (int(selected_size[0]), int(selected_size[1])) if selected_size else (None, None),
        "bleed": bleed_match.group(1) + "mm" if bleed_match else "Not found",
        "material": material_match or "Not found"
    }

def parse_bottom_section(full_text):
    clean_text = "\n".join(
        line for line in full_text.splitlines()
        if not re.match(r"(PDF Version|ICC Profile|Sizes|Overprints|Transparancies)", line, re.IGNORECASE)
    )
    size_match = re.search(r"Finished Size:\s*(\d+\.?\d*)\s*[xX]\s*(\d+\.?\d*)mm", clean_text)
    bleed_match = re.search(r"Bleed\s*\(\+(\d+(\.\d+)?)\):\s*(\d+\.?\d*)\s*[xX]\s*(\d+\.?\d*)mm", clean_text)
    scale_match = re.search(r"(\d+(\.\d+)?)%", clean_text)
    material_match = fuzzy_match_material(clean_text)
    colourspace_match = re.search(r"Colourspace\s*:\s*(\w+)", clean_text, re.IGNORECASE)

    width = float(size_match.group(1)) if size_match else None
    height = float(size_match.group(2)) if size_match else None
    declared_scale = float(scale_match.group(1)) if scale_match else None

    return {
        "size": (width, height),
        "bleed_raw": float(bleed_match.group(1)) if bleed_match else None,
        "material": material_match or "Not found",
        "colourspace": colourspace_match.group(1).upper() if colourspace_match else "Not found",
        "declared_scale": declared_scale
    }

# ------------------- Streamlit App -----------------------

st.title("📄 Batch PDF Print Checker (Cloud-Ready OCR)")

uploaded_pdfs = st.file_uploader("Upload your PDF files", type=["pdf"], accept_multiple_files=True)

if uploaded_pdfs:
    for uploaded_pdf in uploaded_pdfs:
        st.divider()
        st.header(f"Checking: {uploaded_pdf.name}")

        header_details = parse_header(uploaded_pdf.name)

        # Try extracting text layer first
        text_layer = extract_text_layer(uploaded_pdf)

        if not text_layer.strip():
            st.warning("No text layer detected, applying OCR (via OCR.Space API)...")
            full_text = extract_text_via_ocr_api(uploaded_pdf)
        else:
            full_text = text_layer

        bottom_details = parse_bottom_section(full_text)

        filename_size = header_details['size']
        extracted_size = bottom_details['size']

        inferred_scale = None
        if filename_size and extracted_size and extracted_size[0] and extracted_size[1]:
            width_ratio = filename_size[0] / extracted_size[0]
            height_ratio = filename_size[1] / extracted_size[1]
            alt_width_ratio = filename_size[1] / extracted_size[0]
            alt_height_ratio = filename_size[0] / extracted_size[1]

            if abs(width_ratio - height_ratio) < 0.1:
                inferred_scale = width_ratio * 100
            elif abs(alt_width_ratio - alt_height_ratio) < 0.1:
                inferred_scale = alt_width_ratio * 100

        final_scale = inferred_scale or (bottom_details['declared_scale'] if bottom_details['declared_scale'] else 100)

        if bottom_details['declared_scale'] and inferred_scale:
            if abs(bottom_details['declared_scale'] - inferred_scale) < 1:
                final_scale = bottom_details['declared_scale']

        normalized_size = normalize_size_for_scale(extracted_size, final_scale) if extracted_size else (None, None)
        bleed_scaled = bottom_details['bleed_raw'] * final_scale / 100 if bottom_details['bleed_raw'] else None

        st.write(f"**Filename Size:** {filename_size[0]} x {filename_size[1]} mm")
        st.write(f"**Document Size:** {extracted_size[0]} x {extracted_size[1]} mm")
        st.write(f"**Detected Scale:** {int(final_scale)}%")

        if not bottom_details['declared_scale'] and inferred_scale:
            st.warning(f"⚠️ Scale not explicitly provided in document, scale assumed to be {int(inferred_scale)}% based on size comparison.")

        if header_details['bleed'] == "Not found":
            st.info("ℹ️ No bleed information found in filename.")

        st.write(f"**Normalized Document Size:** {int(normalized_size[0])} x {int(normalized_size[1])} mm")
        st.write(f"**Bleed:** {bleed_scaled:.1f}mm" if bleed_scaled is not None else "**Bleed:** Not found")
        st.write(f"**Material:** {bottom_details['material']}")
        st.write(f"**Colourspace:** {bottom_details['colourspace']}")

        size_match = (int(normalized_size[0]), int(normalized_size[1])) == filename_size or (int(normalized_size[1]), int(normalized_size[0])) == filename_size
        bleed_match = abs(bleed_scaled - float(header_details['bleed'].replace('mm',''))) < 0.5 if bleed_scaled and header_details['bleed'] != "Not found" else False
        material_match = header_details['material'] != "Not found" and bottom_details['material'] != "Not found" and header_details['material'].lower() in bottom_details['material'].lower()

        st.subheader("Validation Results")
        if size_match:
            st.success("✅ Size matches after scale adjustment.")
        else:
            st.error("⚠️ Size mismatch after scale adjustment.")

        if bleed_match:
            st.success("✅ Bleed matches after scaling.")
        elif header_details['bleed'] == "Not found":
            st.info("ℹ️ Bleed not provided in filename, skipped bleed comparison.")
        else:
            st.error("⚠️ Bleed mismatch.")

        if material_match:
            st.success("✅ Material matches.")
        else:
            st.warning("⚠️ Material not found or mismatch.")

        colour_normalised = bottom_details['colourspace'].replace("DEVICE", "").upper()
        if colour_normalised != "CMYK":
            readable_colour = "RGB" if colour_normalised == "RGB" else colour_normalised
            st.warning(f"⚠️ Colourspace is {readable_colour}, consider converting to CMYK in Illustrator or Photoshop.\n\n**Illustrator:** Edit → Convert to Profile → Select CMYK\n**Photoshop:** Image → Mode → CMYK")
        else:
            st.success("✅ Colourspace is CMYK.")

st.caption("This app runs fully on Streamlit Cloud, using OCR.Space for non-text PDFs.")
