import streamlit as st
import streamlit.components.v1 as components
import csv
import os
import time
import base64
from datetime import datetime

# ==========================================
# 1. PAGE CONFIGURATION & SUPER STICKY CSS
# ==========================================
st.set_page_config(page_title="Study Booster", page_icon="🎓", layout="wide", initial_sidebar_state="collapsed")

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
            .stApp > header {{ background-color: transparent !important; }}
            div[data-testid="stVerticalBlock"] > div {{
                background-color: rgba(255, 255, 255, 0.94);
                border-radius: 12px;
                padding: 12px;
            }}
            </style>
            """,
            unsafe_allow_html=True
        )
    except:
        pass

add_bg_from_local('bg.jpg') 

# 🛠️ REAL STICKY CSS (Streamlit Layout Override)
st.markdown("""
    <style>
    .block-container { padding-top: 1rem !important; padding-bottom: 1rem !important; }
    div.stButton > button { border-radius: 6px !important; font-weight: 600 !important; width: 100%; }
    div.stButton > button[kind="primary"] { background-color: #4F46E5 !important; color: white !important; }
    
    /* 📌 STICKY COLUMN FIX: Streamlit ke default layout ko force karna */
    section[data-testid="stMain"] .block-container {
        overflow: visible !important;
    }
    div[data-testid="column"]:nth-of-type(2) {
        position: -webkit-sticky !important;
        position: sticky !important;
        top: 60px !important;
        align-self: flex-start !important;
        z-index: 999 !important;
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
    col1, col2, col3 = st.columns([1, 1.2, 1])
    with col2:
        st.write("") 
        with st.container(border=True):
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
# 4. FUNCTIONS
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
# 5. DASHBOARD & SIDEBAR
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
                st.success("Quiz Loaded! Go to 'Live Exam' from sidebar to read instructions.")

# ==========================================
# 6. LIVE EXAM MODULE
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
            
    # --- PHASE 3: ACTIVE EXAM (FIXED SCROLL LAYOUT) ---
    else:
        if st.session_state.timer_mode == "Total Time (Minutes)":
            remaining_time = st.session_state.end_time - time.time()
            if remaining_time <= 0:
                st.session_state.quiz_completed = True
                st.rerun()

        q_idx = st.session_state.current_q
        st.session_state.visited_questions.add(q_idx)
        total_q = len(st.session_state.questions)
        q_data = st.session_state.questions[q_idx]

        col_main, col_pal = st.columns([3, 1])
        
        # 📌 RIGHT PANEL (Sticky + Native Scrollbar)
        with col_pal:
            if st.session_state.timer_mode == "Total Time (Minutes)":
                rem_sec = int(st.session_state.end_time - time.time())
                timer_html = f"""
                <!DOCTYPE html>
                <html><head><style>
                body {{ margin:0; padding:5px; font-family:sans-serif; display:flex; justify-content:center; align-items:center; background:transparent; }}
                .timer-box {{ background-color:#fee2e2; border:2px solid #ef4444; color:#dc2626; padding:8px 0; border-radius:8px; font-size:22px; font-weight:bold; text-align:center; width:100%; box-shadow:0 4px 6px -1px rgba(0,0,0,0.1); }}
                </style></head><body>
                    <div class="timer-box">⏳ <span id="time">00:00</span></div>
                    <script>
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
                    </script>
                </body></html>
                """
                components.html(timer_html, height=85) 
            
            st.markdown("<h5 style='text-align:center; margin-top:0;'>Question Palette</h5>", unsafe_allow_html=True)
            st.markdown("<p style='text-align:center; font-size:11px; margin-bottom:5px;'>🔵 Curr | 🟢 Ans | 🔴 Skip | ⚪ Unvisit</p>", unsafe_allow_html=True)
            
            # 🔄 NATIVE STREAMLIT SCROLL CONTAINER (Height=350 ensures scrollbar appears!)
            with st.container(height=350, border=True):
                grid_cols = st.columns(4)
                for i in range(total_q):
                    if i == q_idx: icon = "🔵"
                    elif st.session_state.user_answers.get(i) is not None: icon = "🟢"
                    elif i in st.session_state.visited_questions: icon = "🔴"
                    else: icon = "⚪"
                        
                    with grid_cols[i % 4]:
                        if st.button(f"{icon}\n{i+1}", key=f"pal_{i}"):
                            st.session_state.current_q = i
                            st.rerun()

        # 👈 LEFT PANEL (Main Question)
        with col_main:
            st.markdown(f"<h3 style='color:#4F46E5; margin-top:0;'>{st.session_state.topic}</h3>", unsafe_allow_html=True)
            st.write("---")
            st.markdown(f"#### Q{q_idx + 1}. {q_data['q']}")
            
            saved_ans = st.session_state.user_answers.get(q_idx)
            try: def_idx = q_data['options'].index(saved_ans)
            except: def_idx = None
            
            clear_key = st.session_state.get(f"clear_{q_idx}", 0)
            choice = st.radio("Select your option:", q_data['options'], index=def_idx, key=f"rad_{q_idx}_{clear_key}", label_visibility="collapsed")
            if choice: st.session_state.user_answers[q_idx] = choice
                
            st.write("")
            b_col1, b_col2, b_col3, b_col4 = st.columns(4)
            with b_col1:
                if st.button("⏪ Previous"):
                    if q_idx > 0: st.session_state.current_q -= 1
                    st.rerun()
            with b_col2:
                if st.button("🧹 Clear"):
                    st.session_state.user_answers.pop(q_idx, None)
                    st.session_state[f"clear_{q_idx}"] = clear_key + 1
                    st.rerun()
            with b_col3:
                is_last = (q_idx == total_q - 1)
                btn_txt = "Next ⏩" if not is_last else "Finish"
                if st.button(btn_txt, type="primary"):
                    if not is_last:
                        st.session_state.current_q += 1
                        st.rerun()
            with b_col4:
                if st.button("🚀 Final Submit", type="primary"):
                    st.session_state.quiz_completed = True
                    st.rerun()
