import streamlit as st
import google.generativeai as genai
import os
from utils.prompt_templates import build_prompt
from PyPDF2 import PdfReader
import docx

st.set_page_config(page_title="Recruiter Agent AI", layout="wide")

st.title("🤖 Recruiter Assistant - JD Generator & Parser")
api_key = st.text_input("🔑 Enter your **Google Gemini API Key**", type="password")

if api_key:
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-1.5-flash")

    st.markdown("### 🔍 Do you already have a Job Description (JD)?")
    has_jd = st.radio("Select an option:", ["Yes", "No"])

    jd_text = ""

    # ✅ CASE 1: User has a JD
    if has_jd == "Yes":
        uploaded_file = st.file_uploader("📄 Upload JD (txt/pdf/docx)", type=["txt", "pdf", "docx"])
        if uploaded_file:
            ext = uploaded_file.name.split(".")[-1]
            if ext == "txt":
                jd_text = uploaded_file.read().decode("utf-8")
            elif ext == "pdf":
                reader = PdfReader(uploaded_file)
                jd_text = "\n".join([p.extract_text() for p in reader.pages if p.extract_text()])
            elif ext == "docx":
                doc = docx.Document(uploaded_file)
                jd_text = "\n".join([para.text for para in doc.paragraphs])
    else:
        st.markdown("### 🧠 Let me help you create a JD.")
        role = st.text_input("👔 Job Title:")
        skills = st.text_area("🛠️ Required Skills:")
        exp = st.text_input("📅 Experience Range:")
        location = st.text_input("📍 Preferred Location:")
        if st.button("Generate JD"):
            prompt = f"Create a clear and structured JD for a {role} role requiring {skills}. Experience: {exp}, Location: {location}."
            response = model.generate_content(prompt)
            jd_text = response.text
            st.success("✅ JD Generated")
            st.markdown(jd_text)

    # 🔄 JD Refinement + Parsing
    if jd_text:
        st.markdown("### ✨ Final Output:")
        if st.button("🔎 Refine + Parse JD"):
            prompt = build_prompt(jd_text)
            try:
                response = model.generate_content(prompt)
                final_output = response.text
                st.markdown(final_output)
                st.download_button("📥 Download Markdown", final_output, "JD_Output.md")
            except Exception as e:
                st.error(f"❌ Error: {e}")
