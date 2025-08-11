import streamlit as st
import google.generativeai as genai
import docx
import PyPDF2
import io

# ================================
# Helper Functions
# ================================

def extract_text_from_file(uploaded_file):
    """Extracts text from PDF, DOCX, or TXT file."""
    file_type = uploaded_file.type

    if file_type == "application/pdf":
        reader = PyPDF2.PdfReader(uploaded_file)
        return "\n".join([page.extract_text() for page in reader.pages if page.extract_text()])

    elif file_type in ["application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                       "application/msword"]:
        doc = docx.Document(uploaded_file)
        return "\n".join([para.text for para in doc.paragraphs])

    elif file_type.startswith("text/"):
        return uploaded_file.read().decode("utf-8")

    else:
        return None


def create_jd_prompt(data):
    """Creates the AI prompt for JD creation."""
    return f"""
    Create a detailed Job Description based on the following details:
    Job Title: {data['job_title']}
    Department/Function: {data['department']}
    Industry: {data['industry']}
    Location: {data['location']}
    Work Setup: {data['work_setup']}
    Must-Have Skills: {data['must_have_skills']}
    Total Experience Required: {data['total_experience']}
    Educational Qualification: {data['education']}
    Company Name: {data['company_name']}
    About the Company: {data['about_company']}
    Provide a professional, well-structured JD.
    """


def refine_jd_prompt(jd_text):
    """Creates the AI prompt for JD refinement."""
    return f"""
    Refine and structure the following Job Description.
    Add missing key responsibilities, deliverables, KPIs, and any relevant details.

    Job Description to refine:
    {jd_text}
    """


def call_gemini(api_key, prompt):
    """Calls the Gemini API with the given prompt."""
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-1.5-flash")
    response = model.generate_content(prompt)
    return response.text if hasattr(response, "text") else str(response)


# ================================
# Streamlit UI
# ================================

st.set_page_config(page_title="Recruiter AI - JD Creator & Refiner", page_icon="🤖", layout="wide")
st.title("🤖 Recruiter AI – JD Creator & Refiner")

# Step 1: Ask for API Key
api_key = st.text_input("🔑 Enter your Gemini API Key:", type="password")
if not api_key:
    st.warning("Please enter your Gemini API Key to proceed.")
    st.stop()

# Step 2: Ask if they have a JD
have_jd = st.radio("📄 Do you already have a Job Description?", ["Yes", "No"])

# ================================
# If user has a JD → Refinement flow
# ================================
if have_jd == "Yes":
    uploaded_file = st.file_uploader("📤 Upload your JD file (PDF, DOCX, TXT)", type=["pdf", "docx", "txt"])
    if uploaded_file:
        jd_text = extract_text_from_file(uploaded_file)
        if jd_text:
            if st.button("✨ Refine JD"):
                with st.spinner("Refining your JD..."):
                    refined_jd = call_gemini(api_key, refine_jd_prompt(jd_text))
                    st.subheader("📜 Refined Job Description")
                    st.write(refined_jd)
        else:
            st.error("Could not extract text from the uploaded file.")

# ================================
# If user does not have a JD → Creation flow
# ================================
else:
    st.subheader("📝 Fill in the essential details to create a JD")
    job_title = st.text_input("Job Title*")
    department = st.text_input("Department / Function*")
    industry = st.text_input("Industry*")
    location = st.text_input("Location*")
    work_setup = st.selectbox("Work Setup*", ["Remote", "Hybrid", "Onsite"])
    must_have_skills = st.text_area("Must-Have Skills*")
    total_experience = st.text_input("Total Experience Required*")
    education = st.text_input("Educational Qualification*")
    company_name = st.text_input("Company Name*")
    about_company = st.text_area("About the Company*")

    if st.button("🚀 Generate JD"):
        if not all([job_title, department, industry, location, work_setup,
                    must_have_skills, total_experience, education,
                    company_name, about_company]):
            st.error("Please fill all required fields (*) before generating.")
        else:
            with st.spinner("Generating your JD..."):
                jd_data = {
                    "job_title": job_title,
                    "department": department,
                    "industry": industry,
                    "location": location,
                    "work_setup": work_setup,
                    "must_have_skills": must_have_skills,
                    "total_experience": total_experience,
                    "education": education,
                    "company_name": company_name,
                    "about_company": about_company
                }
                created_jd = call_gemini(api_key, create_jd_prompt(jd_data))
                st.subheader("📜 Generated Job Description")
                st.write(created_jd)

                st.subheader("✨ Refined Version")
                refined_jd = call_gemini(api_key, refine_jd_prompt(created_jd))
                st.write(refined_jd)
