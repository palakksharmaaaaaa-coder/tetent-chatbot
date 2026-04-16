import os
import re
import json
import streamlit as st
import google.generativeai as genai
import os
from dotenv import load_dotenv
from faker import Faker
from typing import Union
from dotenv import load_dotenv
import streamlit as st
import google.generativeai as genai

# -------------------
# Load Environment Variables
# -------------------
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

generation_config: dict[str, Union[int, float, str, None]] = {
    "temperature": 1,
    "top_p": 0.95,
    "top_k": 40,
    "max_output_tokens": 8192,
    "response_mime_type": "text/plain",
}

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
else:
    st.error("Gemini API key not found. Please ensure it's set in the .env file.")
    st.stop()

# -------------------
# Helper: Clean Gemini Output
# -------------------
def parse_questions(text):
    """Cleans the raw Gemini output, removes intro lines, and limits to 5."""
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    cleaned = []
    for line in lines:
        # Remove numbering/bullets
        line = re.sub(r'^\d+[\.\)]\s*', '', line)
        line = re.sub(r'^[-•]\s*', '', line)
        # Only keep lines ending with a question mark
        if line.endswith("?"):
            cleaned.append(line)
    return cleaned[:5]

# -------------------
# Streamlit App UI
# -------------------
st.set_page_config(page_title="TalentScout Hiring Assistant", layout="centered")

st.title("🧑‍💻 TalentScout Chatbot")
st.markdown("**Your AI-powered recruitment assistant for generating tailored technical interview questions instantly.**")

if "candidate_details" not in st.session_state:
    st.session_state.candidate_details = {}
if "questions" not in st.session_state:
    st.session_state.questions = []
if "answers" not in st.session_state:
    st.session_state.answers = {}

# -------------------
# Candidate Details
# -------------------
st.subheader("Candidate Information")
name = st.text_input("Full Name")
email = st.text_input("Email Address")
phone = st.text_input("Phone Number")
experience = st.slider("Years of Experience", 0, 20, 1)
position = st.text_input("Desired Position")
location = st.text_input("Current Location")
tech_stack = st.text_area("Tech Stack (e.g., Python, Django, React)")

# -------------------
# Submit to Generate Questions
# -------------------
if st.button("Submit"):
    if not (name and email and tech_stack):
        st.error("Please fill in all required fields.")
    else:
        st.success("Information saved! Generating technical questions...")

        st.session_state.candidate_details = {
            "name": name,
            "email": email,
            "phone": phone,
            "experience": experience,
            "position": position,
            "location": location,
            "tech_stack": tech_stack
        }

        try:
            model = genai.GenerativeModel(
                model_name="gemini-2.5-flash",
                generation_config=generation_config,
                system_instruction="Generate exactly 5 concise, role-specific technical interview questions based only on the given tech stack."
            )

            # Always start chat session first
            chat_session = model.start_chat()

            # Ask Gemini for exactly 5 numbered questions
            response = chat_session.send_message(
                f"List exactly 5 technical interview questions for the following tech stack: {tech_stack}. "
                "Number them from 1 to 5, each on a separate line, ending with a question mark, and without any extra explanation."
            )

            raw_output = response.text.strip()

            # Parse into clean questions
            questions_list = parse_questions(raw_output)

            # Backup method if less than 5 were parsed
            if len(questions_list) < 5:
                possible_qs = [q.strip() + "?" for q in raw_output.split("?") if q.strip()]
                questions_list = possible_qs[:5]

            st.session_state.questions = questions_list

        except Exception as e:
            st.error(f"An error occurred during question generation: {e}")

# -------------------
# Show Questions + Answer Boxes
# -------------------
if st.session_state.questions:
    st.divider()
    st.header("📝 Technical Assessment")
    st.info("Please provide detailed answers to be selected.")

    # We use a form to "lock" the data until the button is pressed
    with st.form("interview_form"):
        user_answers = {}
        
        for i, q in enumerate(st.session_state.questions):
            st.write(f"**Question {i+1}:** {q}")
            # The key is unique so Streamlit remembers each answer
            user_answers[f"Q{i+1}"] = st.text_area(f"Your Answer {i+1}", key=f"input_ans_{i}")
        
        # This is the ONLY button inside the form
        submit_button = st.form_submit_button("Submit & Get Result 🏁")

    if submit_button:
        # Check if user actually wrote something
        if not any(user_answers.values()):
            st.warning("Please answer the questions before submitting!")
        else:
            # 1. Prepare data for saving
            result_data = {
                "candidate": st.session_state.candidate_details,
                "interview": user_answers
            }

            try:
                # 2. Save to JSON
                with open("candidate_responses.json", "a", encoding="utf-8") as f:
                    json.dump(result_data, f, indent=4)
                    f.write("\n")
                st.success("✅ Responses saved to database!")

                # 3. AI Evaluation with Gemini 2.5 Flash
                with st.spinner("🤖 Senior HR is reviewing your answers..."):
                    eval_model = genai.GenerativeModel("gemini-3.1-flash-lite-preview")
                    
                    eval_prompt = f"""
                    You are a Senior Technical Recruiter. Evaluate the candidate: {st.session_state.candidate_details.get('name', 'User')}.
                    Role: {st.session_state.candidate_details.get('position', 'Developer')}
                    
                    Technical Answers:
                    {user_answers}
                    
                    Instructions:
                    1. Provide a 'Technical Score' out of 10.
                    2. Give a brief 'Expert Feedback'.
                    3. Final Verdict: Use exactly "SELECTED FOR NEXT ROUND" or "REJECTED".
                    """
                    
                    eval_res = eval_model.generate_content(eval_prompt)
                    
                    # Display the Result
                    st.divider()
                    st.subheader("🎓 Interview Evaluation Report")
                    st.markdown(eval_res.text)
                    
                    # Celebrate if selected
                    if "SELECTED" in eval_res.text.upper():
                        st.balloons()
                        st.success("Congratulations! You've made it to the next round.")
                    else:
                        st.error("Better luck next time.")

            except Exception as e:
                st.error(f"Error during processing: {e}")
    # -------------------
    # Save Responses Button
    # -------------------
    if st.button("Save Responses & Get Result"):
        # 1. Sabse pehle current answers ko collect karna
        # Dhyan dein: ye lines 'if' ke andar indented honi chahiye
        current_answers = {
            f"Q{i+1}": st.session_state.get(f"ans_{i}", "No Answer Provided") 
            for i in range(len(st.session_state.questions))
        }
        
        all_data = {
            "candidate_details": st.session_state.candidate_details,
            "answers": current_answers
        }

        try:
            # 2. File mein save karne ka logic
            with open("candidate_responses.json", "a", encoding="utf-8") as f:
                json.dump(all_data, f, ensure_ascii=False, indent=4)
                f.write("\n")
            st.success("✅ Responses saved successfully!")

            # 3. AI Evaluation ka part
            with st.spinner("🤖 AI is analyzing your performance..."):
                # Sahi model name: gemini-2.5-flash
                eval_model = genai.GenerativeModel("gemini-2.5-flash")
                
                eval_prompt = f"""
                You are a Senior Technical Interviewer. 
                Evaluate the following answers for the role: {st.session_state.candidate_details.get('position', 'Developer')}.
                
                Candidate Skills: {st.session_state.candidate_details.get('tech_stack', 'N/A')}
                
                Questions & Answers to Review:
                {current_answers}
                
                Instructions:
                - If the technical logic is mostly correct, be supportive and select them.
                - Clearly state the 'Final Verdict' at the end: "SELECTED FOR NEXT ROUND" or "REJECTED".
                - Give a 2-line feedback summary.
                """
                
                eval_response = eval_model.generate_content(eval_prompt)
                
                # Result screen par dikhana
                st.divider()
                st.subheader("📊 Interview Evaluation Report")
                st.markdown(eval_response.text)
                
                # Celebration balloons agar selection ho jaye
                if "SELECTED" in eval_response.text.upper():
                    st.balloons()
                
        except Exception as e:
            st.error(f"❌ Something went wrong: {e}")
