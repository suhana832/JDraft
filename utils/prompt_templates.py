def build_prompt(jd_text):
    return f"""
You are an expert technical recruiter assistant.

Given the following job description (JD), generate output in structured markdown format with the following 3 sections:

---

### 1. ✅ Search Criteria
- Boolean Keyword String  
- Mandatory Skills/Experience  
- Preferred Skills/Experience  

---

### 2. 🧠 10 Screening Questions and Answers  
Divide into:
- Domain Expertise  
- Product/Tech Depth  
- Cross-functional/Partner Management  
- Fitment & Motivation  

---

### 3. 🗺️ Source Mapping
- Top companies (India, Chennai preferred)  
- Job titles  
- LinkedIn filters (title, skill, location, experience)

---

JD:
{jd_text}
"""
