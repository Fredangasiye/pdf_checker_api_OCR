import streamlit as st
import requests
from pdf2image import convert_from_bytes
from PIL import Image
import io
import base64

OCR_API_KEY = "helloworld"  # Free public key for testing

st.set_page_config(page_title="Beith PDF OCR Checker")
st.title("📄 Beith PDF OCR Checker (API-based)")

uploaded_pdf = st.file_uploader("Upload a PDF", type=["pdf"])

if uploaded_pdf:
    st.success(f"Uploaded: {uploaded_pdf.name}")
    images = convert_from_bytes(uploaded_pdf.read())

    extracted_text = ""

    for i, img in enumerate(images):
        st.image(img, caption=f"Page {i+1}", use_column_width=True)

        buffered = io.BytesIO()
        img.save(buffered, format="JPEG")
        img_base64 = base64.b64encode(buffered.getvalue()).decode()

        with st.spinner(f"Extracting text from page {i+1}..."):
            response = requests.post(
                "https://api.ocr.space/parse/image",
                data={
                    "base64Image": f"data:image/jpeg;base64,{img_base64}",
                    "language": "eng",
                    "isOverlayRequired": False,
                    "apikey": OCR_API_KEY,
                },
            )

            result = response.json()
            if result.get("IsErroredOnProcessing"):
                st.error(f"Error on page {i+1}: {result.get('ErrorMessage')}")
            else:
                page_text = result["ParsedResults"][0]["ParsedText"]
                extracted_text += f"\n\n--- Page {i+1} ---\n{page_text}"

    st.subheader("📝 Extracted Text:")
    st.text_area("Text from PDF:", extracted_text, height=400)

    st.download_button(
        "📥 Download Extracted Text",
        extracted_text,
        file_name="extracted_text.txt"
    )
