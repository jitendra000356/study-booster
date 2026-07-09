import streamlit as st
import csv
import os
import time
import base64
from datetime import datetime

# ==========================================
# 1. PAGE CONFIGURATION
# ==========================================
st.set_page_config(page_title="Study Booster", page_icon="🎓", layout="wide", initial_sidebar_state="collapsed")

# 🖼️ Background Setup
def add_bg_from_local(image_file):
    try:
        with open(image_file, "rb") as image_file:
            encoded_string = base64.b64encode(image_file.read())
        st.markdown(
            f"""
            <style>
            .stApp {{
                background-image: url(data:image/{"jpeg"};base64,{encoded_string.decode()});
                background-size: cover;
                background-position: center;
                background-attachment: fixed;
            }}
            </style>
            """,
            unsafe_allow_html=True
        )
    except: pass

add_bg_from_local('bg.jpg') 

# 🛠️ CRYSTAL CLEAR CSS
st.markdown("""
    <style>
    /* Main Content Area */
    .block-container { 
        max-width: 96% !important; 
        padding-top: 1rem !important; 
        background-color: rgba(255, 255, 255, 0.95) !important; 
        border-radius: 12px;
        margin-top: 10px;
        box-shadow: 0 4px 10px rgba(0,0,0,0.2);
    }
    
    /* Force Text to Black */
    section[data-testid="stMain"] * { color: #000000 !important; }

    /* Palette Buttons (Clean & Readable) */
    div[data-testid="column"] button { 
        background-color: #ffffff !important; 
        border: 1px solid #475569 !important;
        border-radius: 4px !important; 
        font-weight: bold !important; 
        height: 35px !important;
        width: 100% !important;
        font-size: 14px !important;
        color: #000000 !important;
        padding: 0px !important;
    }
    
    /* Primary Buttons */
    div.stButton > button[kind="primary"] { 
        background-color: #4F46E5 !important; 
        border: none !important;
        color: #ffffff !important;
    }
    
    /* Timer Box */
    .timer-box { background-color:#fee2e2; border:2px solid #ef4444; color:#dc2626 !important; padding:8px; border-radius:8px; font-size:20px; font-weight:bold; text-align:center; margin-bottom:10px; }
    </style>
""", unsafe_allow_html=True)

CSV_FOLDER = 'saved_csvs'
if not os.path.exists(CSV_FOLDER): os.makedirs(CSV_FOLDER)
ALLOWED_USERS = {"Jiten (Admin)": "admin123", "Rahul (Student)": "rahul2026"}

# ==========================================
# 2. SESSION STATE
# ==========================================
if 'auth' not in st.session_state:
    st.session_state.update({
        'auth': False, 'current_user': "", 'questions': [], 'current_q': 0,
        'user_answers': {}, 'visited_questions': set(), 'quiz_completed': False, 
        'quiz_ready': False, 'exam_started': False, 'topic': "", 'end_time': 0, 
        'timer_mode': "No Timer", 'time_val': 0
    })

# ==========================================
# 3. LOGIN SCREEN
# ==========================================
if not st.session_state.auth:
    col1, col2, col3 = st.columns([1, 1.5, 1]) 
    with col2:
        with st.container():
            st.markdown("<h2 style='text-align: center; color:#4F46E5;'>🎓 Study Booster</h2>", unsafe_allow_html=True)
            st.divider()
            username = st.selectbox("👤 Select Profile", ["-- Select User --"] + list(ALLOWED_USERS.keys()))
            pwd = st.text_input("🔑 Enter Passcode", type="password")
            if st.button("Secure Login 🚀", type="primary", use_container_width=True):
                if username != "-- Select User --" and ALLOWED_USERS.get(username) == pwd:
                    st.session_state.auth = True
                    st.session_state.current_user = username
                    st.rerun()
                else: st.error("❌ Invalid Credentials!")
    st.stop()

# ==========================================
# 4. FUNCTIONS
# ==========================================
def load_quiz(file_name, timer_mode, time_minutes):
    st.session_state.questions = []
    file_path = os.path.join(CSV_FOLDER, file_name)
    with open(file_path, 'r', encoding='utf-8-sig', errors='ignore') as f:
        reader = csv.DictReader(f)
        for row in reader:
            st.session_state.questions.append({'q': row['Question'], 'options': [row['Option1'], row['Option2'], row['Option3'], row['Option4'], row['Option5']], 'ans': int(row['Answer']) - 1})
    st.session_state.topic = os.path.splitext(file_name)[0].replace("_", " ")
    st.session_state.quiz_ready = True
    st.session_state.exam_started = False 
    st.session_state.quiz_completed = False
    st.session_state.current_q = 0
    st.session_state.user_answers = {}
    st.session_state.visited_questions = {0}
    st.session_state.timer_mode = timer_mode
    st.session_state.time_val = time_minutes

# ==========================================
# 5. SIDEBAR
# ==========================================
try: st.sidebar.image("logo.png", use_container_width=True)
except: st.sidebar.markdown("<h2 style='text-align: center;'>🎓 Study Booster</h2>", unsafe_allow_html=True)
menu = st.sidebar.radio("Navigation", ["📚 Dashboard", "📝 Live Exam"])
if st.sidebar.button("🚪 Logout"): st.session_state.auth = False; st.rerun()

if menu == "📚 Dashboard":
    st.header("Welcome to Study Booster! 🚀")
    t_mode = st.radio("Timer:", ["Total Time (Minutes)", "No Timer"], horizontal=True)
    t_val = st.number_input("Enter Time:", value=30) if t_mode == "Total Time (Minutes)" else 0
    for file in [f for f in os.listdir(CSV_FOLDER) if f.endswith('.csv')]:
        if st.button(f"Load: {file}", type="primary"): load_quiz(file, t_mode, t_val); st.success("Loaded!")

# ==========================================
# 6. LIVE EXAM (Fixed Grid)
# ==========================================
elif menu == "📝 Live Exam":
    if not st.session_state.quiz_ready: st.warning("Load quiz first."); st.stop()
    if not st.session_state.exam_started:
        if st.button("✅ Start Exam", type="primary"): st.session_state.exam_started = True; st.rerun()
        st.stop()
    
    if st.session_state.quiz_completed:
        st.write("Exam Finished.")
        st.stop()

    q_idx = st.session_state.current_q
    q_data = st.session_state.questions[q_idx]

    col_main, col_pal = st.columns([3.5, 1.2]) 
    
    with col_pal:
        st.markdown("<div class='timer-box'>⏳ Active Exam</div>", unsafe_allow_html=True)
        st.markdown("<b>Palette:</b>", unsafe_allow_html=True)
        # 🔄 FIXED PALETTE AREA
        with st.container(height=400, border=True):
            cols = st.columns(5)
            for i in range(len(st.session_state.questions)):
                icon = "🔵" if i == q_idx else ("🟢" if st.session_state.user_answers.get(i) else "⚪")
                with cols[i % 5]:
                    if st.button(f"{icon}{i+1}", key=f"p_{i}"): st.session_state.current_q = i; st.rerun()

    with col_main:
        st.markdown(f"### {st.session_state.topic}")
        st.markdown(f"#### Q{q_idx + 1}. {q_data['q']}")
        choice = st.radio("Select:", q_data['options'], index=None, key=f"r_{q_idx}")
        if choice: st.session_state.user_answers[q_idx] = choice
        
        c1, c2, c3 = st.columns(3)
        if c1.button("⏪ Prev"): 
            if q_idx > 0: st.session_state.current_q -= 1; st.rerun()
        if c2.button("Next ⏩", type="primary"): 
            if q_idx < len(st.session_state.questions)-1: st.session_state.current_q += 1; st.rerun()
        if c3.button("🚀 Submit"): st.session_state.quiz_completed = True; st.rerun()
