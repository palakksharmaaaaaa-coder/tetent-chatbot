import os
import re
import json
import streamlit as st
import google.generativeai as genai
from dotenv import load_dotenv
from faker import Faker

# -------------------
# Load Environment Variables
# -------------------
load_dotenv()
# Support for both naming conventions
api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY") or st.secrets.get("GOOGLE_API_KEY")

if api_key:
    genai.configure(api_key=api_key)
else:
    st.error("API key nahi mili. Please check your Secrets or .env file.")
    st.stop()

generation_config = {
    "temperature": 0.7,
    "top_p": 0.95,
    "top_k": 40,
    "max_output_tokens": 1024,
}

# -------------------
# Helper Functions
# -------------------
def parse_questions(text):
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    cleaned = []
    for line in lines:
        line = re.sub(r'^\d+[\.\)]\s*', '', line)
        line = re.sub(r'^[-•]\s*', '', line)
        if line.endswith("?"):
            cleaned.append(line)
    return cleaned[:5]

# -------------------
# Streamlit App UI
# -------------------
st.set_page_config(page_title="TalentScout Hiring Assistant", layout="centered")

st.title("🧑‍💻 TalentScout Chatbot")
st.markdown("**AI-powered recruitment assistant for technical interview questions.**")

# Session State Initialization
if "questions" not in st.session_state:
    st.session_state.questions = []
if "candidate_details" not in st.session_state:
    st.session_state.candidate_details = {}

# --- Step 1: Candidate Details ---
with st.expander("Candidate Information", expanded=not st.session_state.questions):
    name = st.text_input("Full Name")
    email = st.text_input("Email Address")
    experience = st.slider("Years of Experience", 0, 20, 1)
    position = st.text_input("Desired Position")
    tech_stack = st.text_area("Tech Stack (e.g., Python, React)")
    
    if st.button("Generate Questions"):
        if name and email and tech_stack:
            with st.spinner("Generating questions..."):
                try:
                    # Model name fixed to gemini-1.5-flash
                    model = genai.GenerativeModel('gemini-2.0-flash')
                    prompt = f"Generate exactly 5 technical interview questions for a {position} with {experience} years experience. Tech stack: {tech_stack}. Only output the questions."
                    response = model.generate_content(prompt)
                    st.session_state.questions = parse_questions(response.text)
                    st.session_state.candidate_details = {"name": name, "position": position, "tech_stack": tech_stack}
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")
        else:
            st.warning("Please fill required fields.")

# --- Step 2: Assessment ---
if st.session_state.questions:
    st.divider()
    st.header("📝 Technical Assessment")
    
    with st.form("interview_form"):
        user_answers = {}
        for i, q in enumerate(st.session_state.questions):
            st.write(f"**Q{i+1}:** {q}")
            user_answers[f"Q{i+1}"] = st.text_area(f"Your Answer {i+1}", key=f"ans_{i}")
        
        submitted = st.form_submit_button("Submit & Get Result 🏁")

    if submitted:
        with st.spinner("Evaluating..."):
            try:
                # Evaluation logic
                eval_model = genai.GenerativeModel("gemini-1.5-flash")
                eval_prompt = f"""
                Evaluate these answers for a {st.session_state.candidate_details['position']} role.
                Answers: {user_answers}
                Verdict must be either 'SELECTED FOR NEXT ROUND' or 'REJECTED'.
                """
                eval_res = eval_model.generate_content(eval_prompt)
                
                st.subheader("🎓 Evaluation Report")
                st.markdown(eval_res.text)
                
                if "SELECTED" in eval_res.text.upper():
                    st.balloons()
                    st.success("Selected!")
                else:
                    st.error("Not selected.")
                    
                # Save to file
                with open("responses.json", "a") as f:
                    json.dump({"details": st.session_state.candidate_details, "answers": user_answers}, f)
                    f.write("\n")
                    
            except Exception as e:
                st.error(f"Evaluation Error: {e}")
