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

# 🛠️ BASE CSS (100% PERFECT TOP ICONS FIX)
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
    
    /* 🎯 THE ULTIMATE FIX FOR TOP ICONS (Share & Sidebar shape fix) */
    header[data-testid="stHeader"] { 
        background-color: transparent !important; 
    }
    
    header[data-testid="stHeader"] button, 
    [data-testid="stToolbar"] button,
    [data-testid="collapsedControl"],
    button[kind="header"] {
        background-color: #ffffff !important; 
        border-radius: 8px !important; /* 'Share' button ke jaisa square/rounded shape */
        box-shadow: 0 2px 5px rgba(0,0,0,0.2) !important; 
        border: 1px solid #cbd5e1 !important; 
        opacity: 1 !important;
        visibility: visible !important;
        z-index: 99999 !important;
        color: #000000 !important;
    }
    
    /* Only fix text/icon color without thick strokes */
    header[data-testid="stHeader"] button *, 
    [data-testid="stToolbar"] button *,
    [data-testid="collapsedControl"] *,
    button[kind="header"] * {
        color: #000000 !important;
    }
    
    header[data-testid="stHeader"] button svg, 
    [data-testid="stToolbar"] button svg,
    [data-testid="collapsedControl"] svg,
    button[kind="header"] svg {
        fill: currentColor !important;
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
ALLOWED_USERS = {"Jitendra (Admin)": "Admin@1996", "Jili (Student)": "Jili@1999", "Satish (Student)": "Satish@2004", "Binita (Student)": "Bini@1993", "Arvind (Student)": "Arvind@1994", "Gaurav (Kalu)": "Kalu@1997", "Pankaj (Student)": "Pankaj@123", "Pappu (Student)": "Pappu@123"}

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
        score = sum(1 for i, q in enumerate(st.session_state.questions)
                    if st.session_state.user_answers.get(i) == q['options'][q['ans']])

        attempted = len(st.session_state.user_answers)
        skipped = total_q - attempted
        wrong = attempted - score

        st.header("🏆 Performance Analysis")

        c1,c2,c3,c4 = st.columns(4)
        c1.metric("✅ Correct", score)
        c2.metric("❌ Wrong", wrong)
        c3.metric("⚪ Skipped", skipped)
        c4.metric("🎯 Score", f"{score}/{total_q}")

        st.progress(score/total_q if total_q else 0)
        st.divider()
        st.subheader("📋 Detailed Answer Review")

        page_size=10
        total_pages=(total_q-1)//page_size+1
        page=st.number_input("Result Page",1,total_pages,1)

        start=(page-1)*page_size
        end=min(start+page_size,total_q)

        for i in range(start,end):
            q=st.session_state.questions[i]
            correct=q['options'][q['ans']]
            user=st.session_state.user_answers.get(i)

            st.markdown(f"### Q{i+1}. {q['q']}")
            if user==correct:
                st.success(f"✅ Your Answer: {user}")
            elif user is None:
                st.warning("⚪ Not Attempted")
                st.info(f"Correct Answer: {correct}")
            else:
                st.error(f"❌ Your Answer: {user}")
                st.success(f"✅ Correct Answer: {correct}")
            st.divider()
        st.stop()
            
    # --- PHASE 3: ACTIVE EXAM ---
    else:
        if st.session_state.timer_mode == "Total Time (Minutes)" and (st.session_state.end_time - time.time()) <= 0:
            st.session_state.quiz_completed = True; st.rerun()

        q_idx = st.session_state.current_q
        st.session_state.visited_questions.add(q_idx)
        total_q = len(st.session_state.questions)
        q_data = st.session_state.questions[q_idx]

        col_main, col_pal = st.columns([3.5, 1.2]) 
        
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
            .no-timer { background-color:#e0f2fe; border-color:#38bdf8; color:#0284c7 !important; }
            </style></head><body>
                __UI_CODE__
                <script>
                    __TIMER_CODE__
                    setTimeout(function() {
                        try {
                            var frame = window.frameElement;
                            var col = frame.closest('div[data-testid="column"]');
                            if(!col) col = frame.parentElement.parentElement.parentElement;
                            
                            if (col) {
                                col.style.position = '-webkit-sticky';
                                col.style.position = 'sticky';
                                col.style.top = '15px';
                                col.style.height = '85vh'; 
                                col.style.overflowY = 'auto'; 
                                col.style.borderLeft = '2px solid #e2e8f0';
                                col.style.paddingLeft = '10px';
                                col.style.paddingRight = '5px';
                                col.classList.add('my-palette');
                                
                                var main = window.parent.document.querySelector('section[data-testid="stMain"]');
                                if(main) main.style.overflow = 'visible';
                                var block = window.parent.document.querySelector('.block-container');
                                if(block) block.style.overflow = 'visible';
                                
                                if (!window.parent.document.getElementById('palette-css')) {
                                    var style = window.parent.document.createElement('style');
                                    style.id = 'palette-css';
                                    style.innerHTML = `
                                        .my-palette::-webkit-scrollbar { width: 5px; }
                                        .my-palette::-webkit-scrollbar-thumb { background: #cbd5e1; border-radius: 5px; }
                                        .my-palette div.stButton > button {
                                            background-color: #ffffff !important;
                                            padding: 0px !important;
                                            font-size: 13px !important;
                                            height: 38px !important;
                                            min-height: 38px !important;
                                            border-radius: 6px !important;
                                            border: 1px solid #cbd5e1 !important;
                                        }
                                        .my-palette div.stButton > button p {
                                            color: #000000 !important;
                                        }
                                        .my-palette div[data-testid="column"] { padding: 2px !important; }
                                    `;
                                    window.parent.document.head.appendChild(style);
                                }
                            }
                        } catch(e) {}
                    }, 200);
                </script>
            </body></html>
            """
            html_hack = html_hack.replace("__UI_CODE__", ui_code).replace("__TIMER_CODE__", timer_code)
            components.html(html_hack, height=60) 
            
            st.markdown("<h5 style='text-align:center; margin-top:5px;'>Question Palette</h5>", unsafe_allow_html=True)
            st.markdown("<p style='text-align:center; font-size:12px; margin-bottom:10px;'>🔵 Curr &nbsp; 🟢 Ans &nbsp; 🔴 Skip &nbsp; ⚪ Unvisit</p>", unsafe_allow_html=True)
            
            grid_cols = st.columns(5)
            for i in range(total_q):
                if i == q_idx: icon = "🔵"
                elif st.session_state.user_answers.get(i) is not None: icon = "🟢"
                elif i in st.session_state.visited_questions: icon = "🔴"
                else: icon = "⚪"
                    
                with grid_cols[i % 5]:
                    if st.button(f"{icon} {i+1}", key=f"pal_{i}"):
                        st.session_state.current_q = i
                        st.rerun()

        with col_main:
            st.markdown(f"<h3 style='color:#4F46E5 !important; margin-top:0;'>{st.session_state.topic}</h3>", unsafe_allow_html=True)
            st.write("---")
            
            st.markdown(f"<h4 style='line-height: 1.5;'>Q{q_idx + 1}. {q_data['q']}</h4>", unsafe_allow_html=True)
            
            saved_ans = st.session_state.user_answers.get(q_idx)
            try: def_idx = q_data['options'].index(saved_ans)
            except: def_idx = None
            
            clear_key = st.session_state.get(f"clear_{q_idx}", 0)
            choice = st.radio("Options:", q_data['options'], index=def_idx, key=f"rad_{q_idx}_{clear_key}", label_visibility="collapsed")
            if choice: st.session_state.user_answers[q_idx] = choice
                
            st.write("")
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
                if st.button("Next ⏩" if not is_last else "Finish", type="primary"):
                    if not is_last:
                        st.session_state.current_q += 1
                        st.rerun()
            with b_col4:
                if st.button("🚀 Final Submit", type="primary"):
                    st.session_state.quiz_completed = True
                    st.rerun()
