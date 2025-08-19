import streamlit as st
import google.generativeai as genai
import docx
import PyPDF2
import json

# ---------- Helpers ----------
def extract_text_from_file(f):
    t = f.type
    if t == "application/pdf":
        r = PyPDF2.PdfReader(f)
        return "\n".join([p.extract_text() for p in r.pages if p.extract_text()])
    elif t in ("application/vnd.openxmlformats-officedocument.wordprocessingml.document",
               "application/msword"):
        d = docx.Document(f)
        return "\n".join(p.text for p in d.paragraphs)
    elif t.startswith("text/"):
        return f.read().decode("utf-8")
    return None

def call_gemini(key, prompt, model="gemini-1.5-flash"):
    genai.configure(api_key=key)
    llm = genai.GenerativeModel(model)
    resp = llm.generate_content(prompt)
    return resp.text if hasattr(resp,"text") else str(resp)

# ---------- JD prompts ----------
def build_create_prompt(data):
    generic = f"Our client is a leading organisation in the {data['industry']} sector."
    return f"""
Create a professional Job Description using the details below.
Do NOT mention real company names – use generic references only.

Job Title: {data['job_title']}
Department: {data['department']}
Industry: {data['industry']}
Location: {data['location']}
Work Setup: {data['work_setup']}
Must-Have Skills: {data['must_have_skills']}
Total Experience: {data['total_experience']}
Educational Qualification: {data['education']}
Company Info: {generic}

Return the full JD in plain text.
"""

def build_parse_prompt(jd_text):
    return f"""
You are an expert recruiter assistant.

Parse the following job description and output a JSON dictionary with **exactly** these 3 keys:

1. "search_criteria" — object with:
   "boolean_string" (string),
   "mandatory" (array of strings),
   "preferred" (array of strings)

2. "screening_questions" — object with:
   "domain_expertise" (array of objects {{question, answer}}),
   "product_tech" (array of objects {{question, answer}}),
   "cross_functional" (array of objects {{question, answer}}),
   "fitment" (array of objects {{question, answer}})

3. "source_mapping" — object with:
   "companies" (array of strings),
   "roles" (array of strings),
   "linkedin_filters" (object {{title, skills, location, experience}})

⚠️ IMPORTANT:
Return **valid JSON ONLY**. No markdown, no commentary, no backticks.
If a value is missing, output an empty array or empty string.

JD:
{jd_text}
"""

# ---------- Streamlit ----------
st.set_page_config("Recruiter AI", layout="wide")
st.title("🤖 Recruiter AI — JD Creation & Parsing")

api_key = st.text_input("Enter your Gemini API Key:", type="password")
if not api_key:
    st.stop()

choice = st.radio("Do you already have a Job Description?", ["No (Create one)", "Yes (Parse existing)"])

# =========== CREATE ============
if choice.startswith("No"):
    st.subheader("📝 Fill details to generate a Job Description")
    col1, col2 = st.columns(2)
    job_title   = col1.text_input("Job Title*")
    department  = col2.text_input("Department / Function*")
    industry    = col1.text_input("Industry*")
    location    = col2.text_input("Location*")
    work_setup  = col1.selectbox("Work Setup*", ["Remote","Hybrid","Onsite"])
    must_have   = col2.text_area("Must-Have Skills*")
    exp         = col1.text_input("Total Experience Required*")
    edu         = col2.text_input("Educational Qualification*")

    if st.button("🚀 Generate JD"):
        if not all([job_title,department,industry,location,work_setup,must_have,exp,edu]):
            st.error("All fields marked * are required.")
        else:
            with st.spinner("Generating JD..."):
                data = {
                  "job_title":job_title,"department":department,"industry":industry,
                  "location":location,"work_setup":work_setup,
                  "must_have_skills":must_have,"total_experience":exp,"education":edu
                }
                jd = call_gemini(api_key, build_create_prompt(data))
                st.session_state.generated_jd = jd
                st.success("✅ Job Description created!")

    if "generated_jd" in st.session_state:
        st.markdown("### 📄 Generated JD")
        st.text_area("JD Preview", st.session_state.generated_jd, height=300)
        if st.button("📥 Parse This JD"):
            st.session_state.to_parse = st.session_state.generated_jd
            st.rerun()

# =========== PARSE ============
else:
    st.subheader("📤 Upload and Parse an existing JD")
    file = st.file_uploader("Upload PDF/DOCX/TXT", type=["pdf","docx","txt"])
    if file:
        text = extract_text_from_file(file)
        if text and st.button("🔍 Parse JD"):
            st.session_state.to_parse = text
            st.rerun()

# ========= When user wants to parse =========
if "to_parse" in st.session_state:
    prompt = build_parse_prompt(st.session_state.to_parse)
    st.session_state.last_prompt = prompt

    with st.spinner("Parsing JD..."):
        raw = call_gemini(api_key, prompt)

    # try parse JSON
    try:
        parsed = json.loads(raw)
        st.session_state.parsed_sections = parsed
        st.success("Parsed ✅")
    except Exception:
        st.error("❌ Model did not return valid JSON.")
        if st.button("🔁 Try Again"):
            raw_retry = call_gemini(api_key, st.session_state.last_prompt)
            try:
                parsed = json.loads(raw_retry)
                st.session_state.parsed_sections = parsed
                st.rerun()
            except:
                st.error("Still not valid. Try again.")
        st.stop()

# ====== Display & Download Sections ======
if "parsed_sections" in st.session_state:
    data = st.session_state.parsed_sections
    st.subheader("✅ Parsed Sections")
    st.json(data)

    # ---------------------------------------------
    # Helper to build PDF in-memory and return bytes
    # ---------------------------------------------
    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas
    import io

    def build_pdf(title, content_str):
        buf = io.BytesIO()
        c = canvas.Canvas(buf, pagesize=letter)
        textobject = c.beginText(40, 750)
        textobject.setFont("Helvetica", 10)
        textobject.textLine(title)
        textobject.textLine("-" * len(title))
        for line in content_str.split("\n"):
            textobject.textLine(line)
        c.drawText(textobject)
        c.showPage()
        c.save()
        buf.seek(0)
        return buf.getvalue()

    # ---------------------------------------------
    # Build + Download buttons
    # ---------------------------------------------
    # 1) Search Criteria
    sc = data['search_criteria']
    sc_text = f"Boolean String: {sc['boolean_string']}\n\nMandatory:\n" + \
              "\n".join(sc['mandatory']) + \
              "\n\nPreferred:\n" + "\n".join(sc['preferred'])

    # 2) Screening Questions
    sq = data['screening_questions']
    sq_lines = []
    for key, arr in sq.items():
        sq_lines.append(f"\n*** {key.replace('_',' ').title()} ***")
        for qa in arr:
            sq_lines.append(f"Q: {qa['question']}")
            sq_lines.append(f"A: {qa['answer']}")
    sq_text = "\n".join(sq_lines)

    # 3) Source Mapping
    sm = data['source_mapping']
    sm_text = "Companies:\n" + "\n".join(sm['companies']) + \
              "\n\nRoles:\n" + "\n".join(sm['roles']) + \
              "\n\nLinkedIn Filters:\n" + \
              f"Title: {sm['linkedin_filters']['title']}\n" + \
              f"Skills: {', '.join(sm['linkedin_filters']['skills'])}\n" + \
              f"Location: {sm['linkedin_filters']['location']}\n" + \
              f"Experience: {sm['linkedin_filters']['experience']}"

    # Buttons
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("📄 Download Search Criteria (PDF)"):
            pdf_bytes = build_pdf("Search Criteria", sc_text)
            st.download_button("⬇️ Save PDF", pdf_bytes, file_name="search_criteria.pdf")
    with col2:
        if st.button("📄 Download Screening Questions (PDF)"):
            pdf_bytes = build_pdf("Screening Questions", sq_text)
            st.download_button("⬇️ Save PDF", pdf_bytes, file_name="screening_questions.pdf")
    with col3:
        if st.button("📄 Download Source Mapping (PDF)"):
            pdf_bytes = build_pdf("Source Mapping", sm_text)
            st.download_button("⬇️ Save PDF", pdf_bytes, file_name="source_mapping.pdf")

