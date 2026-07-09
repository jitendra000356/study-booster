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

# 🛠️ BASE CSS (100% GUARANTEED TOP ICONS FIX)
st.markdown("""
    <style>
    .block-container { 
        max-width: 96% !important; 
        padding-top: 1rem !important; 
        padding-bottom: 1rem !important; 
        background-color: rgba(255, 255, 255, 0.94) !important; 
        border-radius: 12px;
        margin-top: 10px;
        box-shadow: 0 4px 10px rgba(0,0,0,0.15);
    }
    
    /* 🎯 THE ULTIMATE FIX FOR TOP ICONS (Menu & Sidebar) */
    header[data-testid="stHeader"] { 
        background-color: transparent !important; 
    }
    
    /* Targeting every possible Streamlit class for top corners */
    header[data-testid="stHeader"] button, 
    [data-testid="stToolbar"] button,
    [data-testid="collapsedControl"],
    button[kind="header"] {
        background-color: #ffffff !important; 
        border-radius: 50% !important;
        box-shadow: 0 4px 10px rgba(0,0,0,0.8) !important; 
        border: 2px solid #000000 !important; 
        opacity: 1 !important;
        visibility: visible !important;
        z-index: 99999 !important;
    }
    
    /* Forcing all icons inside them to be pure black */
    header[data-testid="stHeader"] button *, 
    [data-testid="stToolbar"] button *,
    [data-testid="collapsedControl"] *,
    button[kind="header"] * {
        fill: #000000 !important;
        color: #000000 !important;
        stroke: #000000 !important;
    }
    
    /* Force text to be dark inside the main white container */
    section[data-testid="stMain"] p, 
    section[data-testid="stMain"] h1, 
    section[data-testid="stMain"] h2, 
    section[data-testid="stMain"] h3, 
    section[data-testid="stMain"] h4, 
    section[data-testid="stMain"] h5, 
    section[data-testid="stMain"] h6, 
    section[data-testid="stMain"] label, 
    section[data-testid="stMain"] span,
    section[data-testid="stMain"] div[data-baseweb="radio"] div {
        color: #0f172a !important; 
    }

    /* Sabhi Normal Buttons (Previous, Clear, Palette) ko White BG & Black Text Dena */
    div.stButton > button { 
        background-color: #ffffff !important; 
        border: 1px solid #cbd5e1 !important;
        border-radius: 8px !important; 
        font-weight: bold !important; 
        padding: 0.2rem 0.1rem !important; 
        width: 100%;
        font-size: 14px !important;
    }
    div.stButton > button p, div.stButton > button span {
        color: #000000 !important;
    }

    /* Primary Buttons (Next, Submit) ko Blue BG aur White Text dena */
    div.stButton > button[kind="primary"] { 
        background-color: #4F46E5 !important; 
        border: none !important;
        border-radius: 6px !important; 
    }
    div.stButton > button[kind="primary"] p, div.stButton > button[kind="primary"] span {
        color: #ffffff !important;
    }
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
        st.write("") 
        with st.container():
            st.markdown("<h2 style='text-align: center; color:#4F46E5 !important;'>🎓 Study Booster</h2>", unsafe_allow_html=True)
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
# 4. FUNCTIONS
# ==========================================
def load_quiz(file_name, timer_mode, time_minutes):
    st.session_state.questions = []
    file_path = os.path.join(CSV_FOLDER, file_name)
    with open(file_path, 'r', encoding='utf-8-sig', errors='ignore') as f:
        reader = csv.DictReader(f)
        for row in reader:
            st.session_state.questions.append({
                'q': row['Question'], 'options': [row['Option1'], row['Option2'], row['Option3'], row['Option4'], row['Option5']], 
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
# 5. DASHBOARD & SIDEBAR
# ==========================================
try:
    st.sidebar.image("logo.png", use_container_width=True)
except:
    st.sidebar.markdown("<h2 style='text-align: center;'>🎓 Study Booster</h2>", unsafe_allow_html=True)

st.sidebar.markdown(f"### 👤 {st.session_state.current_user}")
st.sidebar.divider()
menu = st.sidebar.radio("Navigation", ["📚 Dashboard", "📝 Live Exam"])
st.sidebar.divider()
if st.sidebar.button("🚪 Logout", type="secondary"):
    st.session_state.auth = False; st.rerun()

if menu == "📚 Dashboard":
    st.header("Welcome to Study Booster! 🚀")
    if "Admin" in st.session_state.current_user:
        with st.expander("➕ Upload New Quiz File"):
            uploaded_file = st.file_uploader("Upload CSV", type=['csv'])
            if uploaded_file:
                with open(os.path.join(CSV_FOLDER, uploaded_file.name), "wb") as f: f.write(uploaded_file.getbuffer())
                st.success("Test uploaded successfully!")
    st.subheader("⚙️ Exam Settings")
    t_mode = st.radio("Timer Setup:", ["Total Time (Minutes)", "No Timer"], horizontal=True)
    t_val = 0
    if t_mode == "Total Time (Minutes)": t_val = st.number_input("Enter Total Time (in Minutes):", min_value=1, value=30)
    
    st.subheader("Available Test Series")
    files = [f for f in os.listdir(CSV_FOLDER) if f.endswith('.csv')]
    if not files: st.info("No test series available right now.")
    else:
        for file in files:
            col1, col2 = st.columns([4, 1])
            col1.markdown(f"#### 📄 {file.replace('.csv', '')}")
            if col2.button("Load & Ready", key=f"load_{file}", type="primary"):
                load_quiz(file, t_mode, t_val)
                st.success("Quiz Loaded! Go to 'Live Exam' from sidebar to start.")

# ==========================================
# 6. LIVE EXAM MODULE
# ==========================================
elif menu == "📝 Live Exam":
    if not st.session_state.quiz_ready:
        st.warning("⚠️ No active test. Please load a quiz from Dashboard first."); st.stop()
        
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
            
    # --- PHASE 3: ACTIVE EXAM (FIXED INDEPENDENT SCROLL) ---
    else:
        if st.session_state.timer_mode == "Total Time (Minutes)" and (st.session_state.end_time - time.time()) <= 0:
            st.session_state.quiz_completed = True; st.rerun()

        q_idx = st.session_state.current_q
        st.session_state.visited_questions.add(q_idx)
        total_q = len(st.session_state.questions)
        q_data = st.session_state.questions[q_idx]

        col_main, col_pal = st.columns([3.5, 1.2]) 
        
        # 📌 RIGHT PANEL
        with col_pal:
            timer_code = ""
            ui_code = ""
            
            if st.session_state.timer_mode == "Total Time (Minutes)":
                rem_sec = int(st.session_state.end_time - time.time())
                ui_code = '<div class="timer-box">⏳ <span id="time">00:00</span></div>'
                timer_code = f"""
                var countDownDate = new Date().getTime() + ({rem_sec} * 1000);
                var x = setInterval(function() {{
                    var now = new Date().getTime();
                    var distance = countDownDate - now;
                    if (distance <= 0) {{
                        clearInterval(x); document.getElementById("time").innerHTML = "TIME UP!";
                        var buttons = window.parent.document.querySelectorAll('button');
                        for(var i=0; i<buttons.length; i++) {{ if(buttons[i].innerText.includes('Final Submit')) {{ buttons[i].click(); break; }} }}
                    }} else {{
                        var m = Math.floor((distance % (1000 * 60 * 60)) / (1000 * 60));
                        var s = Math.floor((distance % (1000 * 60)) / 1000);
                        m = m < 10 ? "0" + m : m; s = s < 10 ? "0" + s : s;
                        document.getElementById("time").innerHTML = m + ":" + s;
                    }}
                }}, 1000);
                """
            else:
                ui_code = '<div class="timer-box no-timer">📝 No Time Limit</div>'

            html_hack = """
            <!DOCTYPE html>
            <html><head><style>
            body { margin:0; padding:0; font-family:sans-serif; }
            .timer-box { background-color:#fee2e2; border:2px solid #ef4444; color:#dc2626 !important; padding:8px 0; border-radius:8px; font-size:20px; font-weight:bold; text-align:center; box-shadow:0 2px 4px rgba(0,0,0,0.1); margin-bottom: 5px; }
            .timer-box span { color:#dc2626 !important; }
            .no-timer { background-color
