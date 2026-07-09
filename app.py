import streamlit as st
import csv
import os
import time
from datetime import datetime

# ==========================================
# PAGE CONFIGURATION & CSS (Visibility Fix)
# ==========================================
st.set_page_config(page_title="Study Booster Quiz", page_icon="🎓", layout="wide")

# Professional Theme Styling
st.markdown("""
    <style>
    /* Light Grey Background */
    .stApp { background-color: #f4f7f6; }
    
    /* Dark Text Everywhere for Visibility */
    div, p, h1, h2, h3, h4, label, .stMetric, .stMarkdown { 
        color: #2c3e50 !important; 
    }
    
    /* Button Styling */
    div.stButton > button { border-radius: 8px; font-weight: bold; }
    </style>
""", unsafe_allow_html=True)

CSV_FOLDER = 'saved_csvs'
if not os.path.exists(CSV_FOLDER): os.makedirs(CSV_FOLDER)

# Configuration
SECRET_PASSCODE = "PROQUIZ2026" 
ALLOWED_USERS = {
    "Jiten (Admin)": "admin123",
    "Rahul": "rahul2026",
    "Amit": "amit999"
}

# ==========================================
# SESSION STATE
# ==========================================
if 'auth' not in st.session_state:
    st.session_state.update({
        'auth': False, 'current_user': "", 'questions': [], 'current_q': 0,
        'user_answers': {}, 'quiz_completed': False, 'quiz_ready': False,
        'topic': "", 'timer_mode': "No Timer", 'time_val': 0,
        'start_timestamp': 0.0, 'q_start_timestamp': 0.0
    })

# ==========================================
# AUTHENTICATION
# ==========================================
if not st.session_state.auth:
    st.markdown("<h1 style='text-align: center;'>🎓 Study Booster</h1>", unsafe_allow_html=True)
    pwd = st.text_input("Enter Passcode:", type="password")
    if st.button("Login"):
        found = False
        for name, p in ALLOWED_USERS.items():
            if p == pwd:
                st.session_state.auth = True
                st.session_state.current_user = name
                found = True
        if not found: st.error("Invalid Passcode!")
    st.stop()

# Logo
try: st.image("logo.png", width=120)
except: st.markdown("## 🎓 Study Booster")

# ==========================================
# FUNCTIONS
# ==========================================
def load_quiz(file_name):
    st.session_state.questions = []
    file_path = os.path.join(CSV_FOLDER, file_name)
    with open(file_path, 'r', encoding='utf-8-sig', errors='ignore') as f:
        reader = csv.DictReader(f)
        for row in reader:
            st.session_state.questions.append({
                'q': row['Question'], 
                'options': [row['Option1'], row['Option2'], row['Option3'], row['Option4'], row['Option5']], 
                'ans': int(row['Answer']) - 1
            })
    st.session_state.topic = os.path.splitext(file_name)[0]
    st.session_state.quiz_ready = True
    st.session_state.quiz_completed = False
    st.session_state.current_q = 0
    st.session_state.user_answers = {}

# ==========================================
# NAVIGATION
# ==========================================
menu = st.sidebar.radio("Navigation", ["Dashboard", "Start Test", "Manage CSVs"])

if menu == "Dashboard":
    st.title("Admin Dashboard")
    if "Admin" in st.session_state.current_user:
        uploaded_file = st.file_uploader("Upload CSV", type=['csv'])
        if uploaded_file:
            with open(os.path.join(CSV_FOLDER, uploaded_file.name), "wb") as f:
                f.write(uploaded_file.getbuffer())
    
    st.subheader("Load Quiz")
    for file in [f for f in os.listdir(CSV_FOLDER) if f.endswith('.csv')]:
        if st.button(f"Load: {file}"):
            load_quiz(file)
            st.success(f"{file} Ready!")

# ==========================================
# QUIZ INTERFACE
# ==========================================
elif menu == "Start Test":
    if not st.session_state.quiz_ready:
        st.warning("Pehle Dashboard se quiz load karein.")
    else:
        # Start/Reset Logic
        if st.button("Start/Reset Test", type="primary"):
            st.session_state.quiz_completed = False
            st.session_state.current_q = 0
            st.session_state.user_answers = {}
            st.rerun()

        if not st.session_state.quiz_completed and st.session_state.get('quiz_ready'):
            q_idx = st.session_state.current_q
            q_data = st.session_state.questions[q_idx]

            # Right Aligned Button Row
            col1, col2 = st.columns([5, 1])
            with col2:
                btn_txt = "Final Submit 🚀" if q_idx == len(st.session_state.questions)-1 else "Next ➡️"
                if st.button(btn_txt):
                    if st.session_state.get('last_choice'):
                        st.session_state.user_answers[q_idx] = st.session_state.last_choice
                        if q_idx == len(st.session_state.questions)-1: st.session_state.quiz_completed = True
                        else: st.session_state.current_q += 1
                        st.rerun()
                    else: st.error("Select an option!")

            st.subheader(f"Q{q_idx + 1}: {q_data['q']}")
            st.session_state.last_choice = st.radio("Options:", q_data['options'], index=None)

# ==========================================
# RESULTS
# ==========================================
if st.session_state.quiz_completed:
    st.title("Results")
    score = sum(1 for i, q in enumerate(st.session_state.questions) if st.session_state.user_answers.get(i) == q['options'][q['ans']])
    st.metric("Final Score", f"{score}/{len(st.session_state.questions)}")
    for i, q in enumerate(st.session_state.questions):
        st.write(f"Q{i+1}: {q['q']} | Your: {st.session_state.user_answers.get(i)} | Correct: {q['options'][q['ans']]}")
