import streamlit as st
import re
import pytesseract
import fitz  # PyMuPDF
from PIL import Image

# OCR function: convert PDF page to image, run pytesseract
def extract_text_from_pdf_ocr(uploaded_pdf):
    full_text = ""
    with fitz.open(stream=uploaded_pdf.read(), filetype="pdf") as pdf:
        for page_num in range(len(pdf)):
            page = pdf.load_page(page_num)
            pix = page.get_pixmap(dpi=300)
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            text = pytesseract.image_to_string(img)
            full_text += text + "\n"
    return full_text

# Function to parse details from header (filename)
def parse_header(header_line):
    size_match = re.search(r"(\d{3,4})\s*x\s*(\d{3,4})", header_line)
    bleed_match = re.search(r"(\d{1,2})mm\s*BLEED", header_line, re.IGNORECASE)
    material_match = re.search(r"(FABRIC TEXT BACKLIT|VINYL|MESH|PAPER|CANVAS)", header_line, re.IGNORECASE)

    return {
        "size": size_match.group(0) if size_match else "Not found",
        "bleed": bleed_match.group(1) + "mm" if bleed_match else "Not found",
        "material": material_match.group(1).strip().upper() if material_match else "Not found"
    }

# Function to parse details from extracted text
def parse_bottom_section(full_text):
    size_match = re.search(r"Finished Size:\s*(\d+\.\d+)\s*x\s*(\d+\.\d+)mm", full_text)
    bleed_match = re.search(r"Bleed\s*\(\+\d+(\.\d+)?\):\s*(\d+\.\d+)\s*x\s*(\d+\.\d+)mm", full_text)
    material_match = re.search(r"FABRIC TEXT BACKLIT|VINYL|MESH|PAPER|CANVAS", full_text, re.IGNORECASE)

    return {
        "size": f"{int(float(size_match.group(1))*10)} x {int(float(size_match.group(2))*10)}" if size_match else "Not found",
        "bleed": "25mm" if bleed_match else "Not found",
        "material": material_match.group(0).strip().upper() if material_match else "Not found"
    }

# Streamlit app UI
st.title("🔍 PDF Checker (OCR Enabled)")
st.write("Upload a PDF with a descriptive filename and printed details. This app will extract and compare both.")

uploaded_pdf = st.file_uploader("Upload your PDF file here", type=["pdf"])

if uploaded_pdf is not None:
    file_name_header = uploaded_pdf.name.replace(".pdf", "")
    st.subheader("📁 Filename Header:")
    st.code(file_name_header)

    header_details = parse_header(file_name_header)

    uploaded_pdf.seek(0)
    full_text = extract_text_from_pdf_ocr(uploaded_pdf)

    st.subheader("🧾 Extracted OCR Text:")
    st.text(full_text[:1000])

    bottom_details = parse_bottom_section(full_text)

    # Show parsed details
    st.subheader("Parsed Details:")
    col1, col2 = st.columns(2)
    with col1:
        st.write("**From Filename:**")
        st.write(header_details)
    with col2:
        st.write("**From OCR Text:**")
        st.write(bottom_details)

    # Compare and display result
    st.subheader("Comparison Result:")
    size_match = header_details["size"] == bottom_details["size"]
    bleed_match = header_details["bleed"] == bottom_details["bleed"]
    material_match = header_details["material"] == bottom_details["material"]

    if size_match and bleed_match and material_match:
        st.success("✅ All fields match! File looks good.")
    else:
        st.error("⚠️ Mismatch found!")
        if not size_match:
            st.warning(f"Size mismatch: Header = {header_details['size']} | OCR = {bottom_details['size']}")
        if not bleed_match:
            st.warning(f"Bleed mismatch: Header = {header_details['bleed']} | OCR = {bottom_details['bleed']}")
        if not material_match:
            st.warning(f"Material mismatch: Header = {header_details['material']} | OCR = {bottom_details['material']}")
