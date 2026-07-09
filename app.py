import streamlit as st
import csv
import os
import time
from datetime import datetime

# ==========================================
# 1. PAGE CONFIGURATION & COMPACT CSS
# ==========================================
st.set_page_config(page_title="Study Booster", page_icon="🎓", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
    <style>
    /* Compact Top Space */
    .block-container {
        padding-top: 1rem !important;
        padding-bottom: 1rem !important;
    }
    
    /* Clean App Background */
    .stApp { background-color: #F4F7FB; color: #1E293B; }
    
    /* Buttons Customization */
    div.stButton > button {
        border-radius: 6px !important;
        font-weight: 600 !important;
        padding: 0.3rem 0.5rem !important;
        width: 100%;
    }
    div.stButton > button[kind="primary"] {
        background-color: #4F46E5 !important;
        color: white !important;
        border: none !important;
    }
    
    /* Box for Palette */
    .palette-box {
        background-color: white;
        padding: 15px;
        border-radius: 10px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
    }
    </style>
""", unsafe_allow_html=True)

CSV_FOLDER = 'saved_csvs'
if not os.path.exists(CSV_FOLDER): os.makedirs(CSV_FOLDER)

ALLOWED_USERS = {"Jiten (Admin)": "jite1996", "Jili (Student)": "jili1999", "binita (Student)": "bini1993", "Satish (Student)": "satish2004", "gaurav (Kalu)": "gaurav1997", "Arvind (student)": "arvind1994"}

# ==========================================
# 2. SESSION STATE
# ==========================================
if 'auth' not in st.session_state:
    st.session_state.update({
        'auth': False, 'current_user': "", 'questions': [], 'current_q': 0,
        'user_answers': {}, 'visited_questions': set(), 'quiz_completed': False, 
        'quiz_ready': False, 'topic': "", 'end_time': 0, 'timer_mode': "No Timer"
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
    st.session_state.quiz_completed = False
    st.session_state.current_q = 0
    st.session_state.user_answers = {}
    st.session_state.visited_questions = {0} # First question is visited
    st.session_state.timer_mode = timer_mode
    
    if timer_mode == "Total Time (Minutes)":
        st.session_state.end_time = time.time() + (time_minutes * 60)
    else:
        st.session_state.end_time = 0

# ==========================================
# 5. SIDEBAR
# ==========================================
st.sidebar.markdown(f"### 👤 {st.session_state.current_user}")
st.sidebar.divider()
menu = st.sidebar.radio("Navigation", ["📚 Dashboard", "📝 Live Exam"])
st.sidebar.divider()
if st.sidebar.button("🚪 Logout", type="secondary"):
    st.session_state.auth = False
    st.rerun()

# ==========================================
# 6. DASHBOARD
# ==========================================
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
    t_mode = st.radio("Timer Setup:", ["No Timer", "Total Time (Minutes)"], horizontal=True)
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
            if col2.button("Load & Start", key=f"load_{file}", type="primary"):
                load_quiz(file, t_mode, t_val)
                st.success("Quiz Loaded! Go to 'Live Exam' from sidebar.")

# ==========================================
# 7. LIVE EXAM (Testbook Pattern)
# ==========================================
elif menu == "📝 Live Exam":
    if not st.session_state.quiz_ready:
        st.warning("⚠️ No active test. Please load a quiz from Dashboard first.")
        st.stop()
        
    # --- RESULT SCREEN ---
    if st.session_state.quiz_completed:
        total_q = len(st.session_state.questions)
        attempted = len([k for k,v in st.session_state.user_answers.items() if v is not None])
        score = sum(1 for i, q in enumerate(st.session_state.questions) if st.session_state.user_answers.get(i) == q['options'][q['ans']])
        
        st.header("🏆 Performance Analysis")
        st.success("Exam submitted successfully!")
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Total Questions", total_q)
        c2.metric("Attempted", attempted)
        c3.metric("Final Score", f"{score} / {total_q}")
        
        st.divider()
        st.markdown("### 📋 Detailed Answer Key")
        for i, q in enumerate(st.session_state.questions):
            st.markdown(f"**Q{i+1}: {q['q']}**")
            correct_ans = q['options'][q['ans']]
            user_ans = st.session_state.user_answers.get(i)
            
            if user_ans == correct_ans:
                st.success(f"Your Answer: {user_ans} (✅ Correct)")
            elif user_ans is None:
                st.warning(f"Not Attempted. Correct Answer: {correct_ans}")
            else:
                st.error(f"Your Answer: {user_ans} (❌ Wrong)")
                st.info(f"Correct Answer: {correct_ans}")
            st.write("---")
            
    # --- ACTIVE EXAM SCREEN ---
    else:
        # TIMING CHECK (Backend check to auto-submit)
        if st.session_state.timer_mode == "Total Time (Minutes)":
            remaining_time = st.session_state.end_time - time.time()
            if remaining_time <= 0:
                st.session_state.quiz_completed = True
                st.rerun()

        q_idx = st.session_state.current_q
        st.session_state.visited_questions.add(q_idx)
        total_q = len(st.session_state.questions)
        q_data = st.session_state.questions[q_idx]

        # TOP BAR: COMPACT (Topic + Live Timer)
        top_col1, top_col2 = st.columns([3, 1])
        with top_col1:
            st.markdown(f"<h4 style='margin:0; padding:0; color:#4F46E5;'>{st.session_state.topic}</h4>", unsafe_allow_html=True)
        with top_col2:
            if st.session_state.timer_mode == "Total Time (Minutes)":
                rem_sec = int(st.session_state.end_time - time.time())
                # Javascript Live Timer Injection
                timer_html = f"""
                <div style="font-size: 1.2rem; font-weight: bold; color: #DC2626; text-align: right;">
                    ⏳ <span id="clock"></span>
                </div>
                <script>
                    var timeleft = {rem_sec};
                    var timer = setInterval(function(){{
                        if(timeleft <= 0){{
                            clearInterval(timer);
                            document.getElementById("clock").innerHTML = "TIME UP! Submitting...";
                        }} else {{
                            var m = Math.floor(timeleft / 60);
                            var s = timeleft % 60;
                            if (s < 10) {{ s = "0" + s; }}
                            document.getElementById("clock").innerHTML = m + ":" + s + " Left";
                        }}
                        timeleft -= 1;
                    }}, 1000);
                </script>
                """
                st.markdown(timer_html, unsafe_allow_html=True)
            else:
                st.markdown("<div style='text-align: right; font-weight:bold;'>No Timer</div>", unsafe_allow_html=True)
        
        st.write("---")

        # MAIN LAYOUT (Left: Question, Right: Palette)
        col_main, col_pal = st.columns([3, 1])
        
        with col_main:
            # The Question
            st.markdown(f"#### Q{q_idx + 1}. {q_data['q']}")
            
            # Options Setup
            saved_ans = st.session_state.user_answers.get(q_idx)
            try: def_idx = q_data['options'].index(saved_ans)
            except: def_idx = None
            
            # clear_key ensure karta hai ki 'Clear Response' kaam kare
            clear_key = st.session_state.get(f"clear_{q_idx}", 0)
            
            choice = st.radio("Select your option:", q_data['options'], index=def_idx, key=f"rad_{q_idx}_{clear_key}", label_visibility="collapsed")
            if choice:
                st.session_state.user_answers[q_idx] = choice
                
            st.write("")
            st.write("")
            
            # NAVIGATION BUTTONS (Bottom)
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

        with col_pal:
            st.markdown("<div class='palette-box'>", unsafe_allow_html=True)
            st.markdown("<h5 style='text-align:center;'>Question Palette</h5>", unsafe_allow_html=True)
            st.markdown("<small>🔵 Current &nbsp; 🟢 Answered <br> 🔴 Skipped &nbsp;&nbsp; ⚪ Unvisited</small>", unsafe_allow_html=True)
            st.write("")
            
            # GRID OF BUTTONS
            grid_cols = st.columns(4)
            for i in range(total_q):
                # Status Check logic
                if i == q_idx:
                    icon = "🔵"
                elif st.session_state.user_answers.get(i) is not None:
                    icon = "🟢"
                elif i in st.session_state.visited_questions:
                    icon = "🔴"
                else:
                    icon = "⚪"
                    
                with grid_cols[i % 4]:
                    if st.button(f"{icon} {i+1}", key=f"pal_{i}"):
                        st.session_state.current_q = i
                        st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)
