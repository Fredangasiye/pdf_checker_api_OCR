import streamlit as st
import requests

OCR_API_KEY = "helloworld"  # Free test key from OCR.Space

st.set_page_config(page_title="Beith PDF OCR Checker")
st.title("📄 Beith PDF OCR Checker (API-based, no poppler)")

uploaded_pdf = st.file_uploader("Upload a PDF", type=["pdf"])

if uploaded_pdf:
    st.success(f"Uploaded: {uploaded_pdf.name}")

    with st.spinner("Extracting text from PDF..."):
        response = requests.post(
            "https://api.ocr.space/parse/image",
            files={"file": uploaded_pdf},
            data={
                "language": "eng",
                "isOverlayRequired": False,
                "isCreateSearchablePdf": False,
                "apikey": OCR_API_KEY,
            },
        )

        result = response.json()

        if result.get("IsErroredOnProcessing"):
            st.error(f"Error: {result.get('ErrorMessage')}")
        else:
            extracted_text = result["ParsedResults"][0]["ParsedText"]
            st.subheader("📝 Extracted Text:")
            st.text_area("Text from PDF:", extracted_text, height=400)

            st.download_button(
                "📥 Download Extracted Text",
                extracted_text,
                file_name="extracted_text.txt"
            )
