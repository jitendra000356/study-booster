import streamlit as st
import csv
import os
import time
from datetime import datetime

# ==========================================
# PAGE CONFIGURATION & PROFESSIONAL CSS
# ==========================================
st.set_page_config(page_title="Study Booster Quiz", page_icon="🎓", layout="wide")

# Professional Styling
st.markdown("""
    <style>
    .stApp { background-color: #f0f2f6; }
    .css-1d391kg { padding-top: 1rem; }
    /* Button Styling */
    div.stButton > button:first-child { border-radius: 5px; font-weight: bold; }
    </style>
""", unsafe_allow_html=True)

CSV_FOLDER = 'saved_csvs'
if not os.path.exists(CSV_FOLDER):
    os.makedirs(CSV_FOLDER)

SECRET_PASSCODE = "PROQUIZ2026"
ALLOWED_USERS = {"Jiten (Admin)": "admin123", "Rahul": "rahul2026"}

# ==========================================
# SESSION STATE (Memory)
# ==========================================
if 'auth' not in st.session_state:
    st.session_state.auth = False
    st.session_state.current_user = ""
    st.session_state.questions = []
    st.session_state.current_q = 0
    st.session_state.user_answers = {}
    st.session_state.quiz_completed = False
    st.session_state.quiz_ready = False # File loaded check
    st.session_state.topic = ""

# ==========================================
# AUTHENTICATION
# ==========================================
if not st.session_state.auth:
    # Logo Placeholder
    st.markdown("<h1 style='text-align: center;'>🎓 Study Booster</h1>", unsafe_allow_html=True)
    pwd = st.text_input("Enter Passcode:", type="password")
    if st.button("Login"):
        if pwd == SECRET_PASSCODE:
            st.session_state.auth = True
            st.session_state.current_user = "Jiten (Admin)"
            st.rerun()
    st.stop()

# Logo visible only after login
try:
    st.image("logo.png", width=150) # Ensure logo.png is in the same folder
except:
    st.markdown("## 🎓 Study Booster")

# ==========================================
# FUNCTIONS
# ==========================================
def load_csv(file_path, file_name):
    # (Same loading logic as before...)
    st.session_state.questions = []
    with open(file_path, 'r', encoding='utf-8-sig', errors='ignore') as f:
        reader = csv.DictReader(f)
        for row in reader:
            st.session_state.questions.append({'q': row['Question'], 'options': [row['Option1'], row['Option2'], row['Option3'], row['Option4'], row['Option5']], 'ans': int(row['Answer']) - 1})
    st.session_state.topic = os.path.splitext(file_name)[0]
    st.session_state.quiz_ready = True
    st.session_state.quiz_completed = False
    st.session_state.current_q = 0
    st.session_state.user_answers = {}

# ==========================================
# SIDEBAR
# ==========================================
st.sidebar.title(f"👤 {st.session_state.current_user}")
menu = st.sidebar.radio("Navigation", ["Dashboard", "Start Test", "Manage CSVs"])

# ==========================================
# DASHBOARD
# ==========================================
if menu == "Dashboard":
    st.title("Admin Dashboard")
    if "Admin" in st.session_state.current_user:
        uploaded_file = st.file_uploader("Upload new Quiz", type=['csv'])
        if uploaded_file:
            with open(os.path.join(CSV_FOLDER, uploaded_file.name), "wb") as f:
                f.write(uploaded_file.getbuffer())
    
    st.subheader("Select Quiz File")
    files = [f for f in os.listdir(CSV_FOLDER) if f.endswith('.csv')]
    for file in files:
        if st.button(f"Load Quiz: {file}"):
            load_csv(os.path.join(CSV_FOLDER, file), file)
            st.success(f"{file} loaded! Now go to 'Start Test'.")

# ==========================================
# START TEST (Quiz Logic)
# ==========================================
elif menu == "Start Test":
    # DISABLING LOGIC: If not ready, button disabled
    if not st.button("Start Test", disabled=not st.session_state.quiz_ready, type="primary"):
        if not st.session_state.quiz_ready:
            st.warning("Pehle Dashboard se File Load Quiz button dabayein.")
    else:
        st.session_state.quiz_ready = True # Logic to enter quiz mode
        st.rerun()

    # The actual Quiz Interface
    if st.session_state.quiz_ready and not st.session_state.quiz_completed:
        q_idx = st.session_state.current_q
        total_q = len(st.session_state.questions)
        q_data = st.session_state.questions[q_idx]

        # TOP ROW: Submit Button (Right Aligned)
        col1, col2 = st.columns([4, 1])
        with col2:
            is_last = (q_idx == total_q - 1)
            btn_text = "Final Submit 🚀" if is_last else "Next Question ➡️"
            if st.button(btn_text, type="primary"):
                if st.session_state.get('last_selected_opt'):
                    st.session_state.user_answers[q_idx] = st.session_state.last_selected_opt
                    if is_last:
                        st.session_state.quiz_completed = True
                    else:
                        st.session_state.current_q += 1
                    st.rerun()
                else:
                    st.error("Pehle answer select karein!")

        st.markdown(f"### Q{q_idx + 1}: {q_data['q']}")
        st.session_state.last_selected_opt = st.radio("Options:", q_data['options'], index=None)

# ==========================================
# RESULT LOGIC
# ==========================================
if st.session_state.quiz_completed:
    st.header("Results")
    score = sum(1 for i, q in enumerate(st.session_state.questions) if st.session_state.user_answers.get(i) == q['options'][q['ans']])
    st.metric("Score", f"{score}/{len(st.session_state.questions)}")
    if st.button("Restart"):
        st.session_state.quiz_completed = False
        st.session_state.quiz_ready = False
        st.rerun()

elif menu == "Manage CSVs":
    # ... (Delete logic same as before) ...
    pass
