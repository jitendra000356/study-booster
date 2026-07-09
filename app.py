import streamlit as st
import streamlit.components.v1 as components
import csv
import os
import time
import base64
from datetime import datetime

# ==========================================
# 1. PAGE CONFIGURATION
# ==========================================
st.set_page_config(page_title="Study Booster", page_icon="🎓", layout="wide", initial_sidebar_state="collapsed")

# 🖼️ Background Image Setup
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
    except:
        pass

add_bg_from_local('bg.jpg') 

# ==========================================
# 2. 🔥 THE ULTIMATE CSS FIX (SCROLL & STICKY)
# ==========================================
st.markdown("""
    <style>
    /* Main Background Box (Safed Sheesha) */
    .block-container { 
        max-width: 98% !important; 
        padding-top: 1rem !important; 
        padding-bottom: 1rem !important; 
        background-color: rgba(255, 255, 255, 0.95) !important; 
        border-radius: 12px;
        margin-top: 10px;
        box-shadow: 0 4px 10px rgba(0,0,0,0.15);
    }
    header[data-testid="stHeader"] { background-color: transparent !important; }

    /* Button Styling (Chote aur Gol) */
    div.stButton > button { 
        border-radius: 8px !important; 
        font-weight: bold !important; 
        padding: 0.2rem 0.1rem !important; 
        width: 100%;
        font-size: 14px !important;
    }
    div.stButton > button[kind="primary"] { 
        background-color: #4F46E5 !important; 
        color: white !important; 
        padding: 0.5rem 1rem !important; 
        font-size: 16px !important;
    }

    /* =======================================================
       🎯 MAIN MAGIC: STICKY & INDEPENDENT SCROLLBAR
       ======================================================= */
    
    /* 1. Parents ko 'overflow: visible' karna zaruri hai sticky ke liye */
    .stApp, .block-container, div[data-testid="stVerticalBlock"] {
        overflow: visible !important;
    }

    /* 2. Daayein (Right) column ko pakad kar fix karna */
    div[data-testid="stHorizontalBlock"] > div:nth-child(2) {
        position: -webkit-sticky !important;
        position: sticky !important;
        top: 20px !important;             /* Upar se 20px par chipak jayega */
        max-height: 85vh !important;      /* Box ki height screen ka 85% fix kar di */
        overflow-y: auto !important;      /* Sirf iske andar scrollbar aayega */
        padding-left: 15px;
        padding-right: 5px;
        border-left: 2px solid #E2E8F0;   /* Ek divider line */
    }
    
    /* Right Column ka Scrollbar Design */
    div[data-testid="stHorizontalBlock"] > div:nth-child(2)::-webkit-scrollbar { width: 6px; }
    div[data-testid="stHorizontalBlock"] > div:nth-child(2)::-webkit-scrollbar-thumb { background: #cbd5e1; border-radius: 5px; }
    </style>
""", unsafe_allow_html=True)

CSV_FOLDER = 'saved_csvs'
if not os.path.exists(CSV_FOLDER): os.makedirs(CSV_FOLDER)
ALLOWED_USERS = {"Jiten (Admin)": "admin123", "Rahul (Student)": "rahul2026"}

# ==========================================
# 3. SESSION STATE
# ==========================================
if 'auth' not in st.session_state:
    st.session_state.update({
        'auth': False, 'current_user': "", 'questions': [], 'current_q': 0,
        'user_answers': {}, 'visited_questions': set(), 'quiz_completed': False, 
        'quiz_ready': False, 'exam_started': False, 'topic': "", 'end_time': 0, 
        'timer_mode': "No Timer", 'time_val': 0
    })

# ==========================================
# 4. LOGIN SCREEN
# ==========================================
if not st.session_state.auth:
    col1, col2, col3 = st.columns([1, 1.5, 1]) 
    with col2:
        st.write("") 
        with st.container():
            st.markdown("<h2 style='text-align: center; color:#4F46E5;'>🎓 Study Booster</h2>", unsafe_allow_html=True)
            st.divider()
            username = st.selectbox("👤 Select Profile", ["-- Select User --"] + list(ALLOWED_USERS.keys()))
            pwd = st.text_input("🔑 Enter Passcode", type="password")
            st.write("")
            if st.button("Secure Login 🚀", type="primary", use_container_width=True):
                if username != "-- Select User --" and ALLOWED_USERS.get(username) == pwd:
                    st.session_state.auth = True
                    st.session_state.current_user = username
                    st.rerun()
                else:
                    st.error("❌ Invalid Credentials!")
    st.stop()

# ==========================================
# 5. FUNCTIONS
# ==========================================
def load_quiz(file_name, timer_mode, time_minutes):
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
# 6. DASHBOARD & SIDEBAR
# ==========================================
st.sidebar.markdown(f"### 👤 {st.session_state.current_user}")
st.sidebar.divider()
menu = st.sidebar.radio("Navigation", ["📚 Dashboard", "📝 Live Exam"])
st.sidebar.divider()
if st.sidebar.button("🚪 Logout", type="secondary"):
    st.session_state.auth = False
    st.rerun()

if menu == "📚 Dashboard":
    st.header("Welcome to Study Booster! 🚀")
    if "Admin" in st.session_state.current_user:
        with st.expander("➕ Upload New Quiz File"):
            uploaded_file = st.file_uploader("Upload CSV", type=['csv'])
            if uploaded_file:
                with open(os.path.join(CSV_FOLDER, uploaded_file.name), "wb") as f:
                    f.write(uploaded_file.getbuffer())
                st.success("Test uploaded successfully!")
                
    st.subheader("⚙️ Exam Settings")
    t_mode = st.radio("Timer Setup:", ["Total Time (Minutes)", "No Timer"], horizontal=True)
    t_val = 0
    if t_mode == "Total Time (Minutes)":
        t_val = st.number_input("Enter Total Time (in Minutes):", min_value=1, value=30)
    
    st.subheader("Available Test Series")
    files = [f for f in os.listdir(CSV_FOLDER) if f.endswith('.csv')]
    if not files:
        st.info("No test series available right now.")
    else:
        for file in files:
            col1, col2 = st.columns([4, 1])
            col1.markdown(f"#### 📄 {file.replace('.csv', '')}")
            if col2.button("Load & Ready", key=f"load_{file}", type="primary"):
                load_quiz(file, t_mode, t_val)
                st.success("Quiz Loaded! Go to 'Live Exam' from sidebar to start.")

# ==========================================
# 7. LIVE EXAM MODULE
# ==========================================
elif menu == "📝 Live Exam":
    if not st.session_state.quiz_ready:
        st.warning("⚠️ No active test. Please load a quiz from Dashboard first.")
        st.stop()
        
    # --- PHASE 1: INSTRUCTIONS ---
    if not st.session_state.exam_started:
        st.header(f"📜 Instructions: {st.session_state.topic}")
        st.divider()
        st.markdown(f"1. **Total Questions:** {len(st.session_state.questions)}\n2. **Time Limit:** {st.session_state.time_val} Mins\n3. **Auto Submit:** Exam submits when timer hits zero.")
        if st.button("✅ I am ready to begin", type="primary"):
            st.session_state.exam_started = True
            if st.session_state.timer_mode == "Total Time (Minutes)":
                st.session_state.end_time = time.time() + (st.session_state.time_val * 60)
            st.rerun()
        st.stop()
        
    # --- PHASE 2: RESULT SCREEN ---
    if st.session_state.quiz_completed:
        total_q = len(st.session_state.questions)
        score = sum(1 for i, q in enumerate(st.session_state.questions) if st.session_state.user_answers.get(i) == q['options'][q['ans']])
        st.header("🏆 Performance Analysis")
        st.metric("Final Score", f"{score} / {total_q}")
        st.divider()
        st.markdown("### 📋 Detailed Answer Key")
        for i, q in enumerate(st.session_state.questions):
            st.markdown(f"**Q{i+1}: {q['q']}**")
            correct_ans = q['options'][q['ans']]
            user_ans = st.session_state.user_answers.get(i)
            if user_ans == correct_ans: st.success(f"Your: {user_ans} (✅)")
            elif user_ans is None: st.warning(f"Not Attempted. Correct: {correct_ans}")
            else: st.error(f"Your: {user_ans} (❌) | Correct: {correct_ans}")
        st.stop()
            
    # --- PHASE 3: ACTIVE EXAM (FIXED SPLIT) ---
    else:
        if st.session_state.timer_mode == "Total Time (Minutes)":
            remaining_time = st.session_state.end_time - time.time()
            if remaining_time <= 0:
