import streamlit as st
import streamlit.components.v1 as components
import csv
import os
import time
import base64
import re
import json

# ==========================================
# 1. CONFIGURATION & CONSTANTS
# ==========================================
st.set_page_config(
    page_title="Study Booster | Pro CBT Platform", 
    page_icon="🎓", 
    layout="wide", 
    initial_sidebar_state="collapsed"
)

CSV_FOLDER = 'saved_csvs'
if not os.path.exists(CSV_FOLDER): 
    os.makedirs(CSV_FOLDER)

ATTEMPTS_FILE = 'attempts_data.json'
TIMERS_FILE = 'timers_data.json'

# Existing Authentication mapping
ALLOWED_USERS = {
    "Jitendra (Admin)": "Admin@1996", 
    "Jili (Student)": "Jili@1999", 
    "Satish (Student)": "Satish@2004", 
    "Binita (Student)": "Bini@1993", 
    "Arvind (Student)": "Arvind@1994", 
    "Gaurav (Kalu)": "Kalu@1997", 
    "Pankaj (Student)": "Pankaj@123", 
    "Pappu (Student)": "Pappu@123"
}

# ==========================================
# DATA MANAGEMENT FUNCTIONS
# ==========================================

# -- Attempts Logic --
def load_attempts_data():
    if not os.path.exists(ATTEMPTS_FILE):
        return {}
    with open(ATTEMPTS_FILE, 'r') as f:
        try:
            return json.load(f)
        except:
            return {}

def save_attempts_data(data):
    with open(ATTEMPTS_FILE, 'w') as f:
        json.dump(data, f, indent=4)

def get_attempt_data(user, test_file):
    data = load_attempts_data()
    if user not in data:
        data[user] = {}
    if test_file not in data[user]:
        data[user][test_file] = {'allowed': 2, 'used': 0}
    return data[user][test_file]

def increment_attempt(user, test_file):
    data = load_attempts_data()
    if user not in data: data[user] = {}
    if test_file not in data[user]: data[user][test_file] = {'allowed': 2, 'used': 0}
    data[user][test_file]['used'] += 1
    save_attempts_data(data)

def set_allowed_attempts(user, test_file, allowed_count):
    data = load_attempts_data()
    if user not in data: data[user] = {}
    if test_file not in data[user]: data[user][test_file] = {'allowed': 2, 'used': 0}
    data[user][test_file]['allowed'] = allowed_count
    save_attempts_data(data)

def record_attempt_usage():
    """Securely increments the attempt count once per active test session upon completion."""
    if not st.session_state.get('attempt_recorded', False):
        user = st.session_state.get('current_user')
        test_file = st.session_state.get('current_test_filename')
        if user and test_file:
            increment_attempt(user, test_file)
        st.session_state.attempt_recorded = True

# -- Timers Logic --
def load_timers_data():
    if not os.path.exists(TIMERS_FILE):
        return {}
    with open(TIMERS_FILE, 'r') as f:
        try:
            return json.load(f)
        except:
            return {}

def save_timers_data(data):
    with open(TIMERS_FILE, 'w') as f:
        json.dump(data, f, indent=4)

# ==========================================
# 2. STATE INITIALIZATION
# ==========================================
def init_session():
    """Initialize all session state variables safely."""
    default_state = {
        'auth': False, 
        'current_user': "", 
        'questions': [], 
        'current_q': 0,
        'user_answers': {}, 
        'visited_questions': set(), 
        'quiz_ready': False, 
        'topic': "", 
        'timer_mode': "No Timer", 
        'time_val': 0,
        'remaining_seconds': 0,
        'last_calc_time': 0,
        'last_interaction_time': 0,
        'active_page': "Dashboard",
        'is_paused': False,
        'current_test_filename': "",
        'attempt_recorded': False
    }
    for key, value in default_state.items():
        if key not in st.session_state:
            st.session_state[key] = value

# ==========================================
# 3. CORE TIME & EVENT HANDLERS
# ==========================================
def passive_time_check():
    """Validates time elapsed passively on every script run."""
    if st.session_state.get('active_page') != 'Exam' or st.session_state.get('is_paused', False):
        return

    now = time.time()
    elapsed = now - st.session_state.get('last_calc_time', now)
    st.session_state.last_calc_time = now

    # Deduct Time
    if st.session_state.timer_mode == "Total Time (Minutes)":
        st.session_state.remaining_seconds -= elapsed
        if st.session_state.remaining_seconds <= 0:
            st.session_state.remaining_seconds = 0
            st.session_state.active_page = "Result"
            record_attempt_usage()
            st.rerun()

    # Auto-Pause if inactive for 5 minutes (300 seconds)
    inactive_duration = now - st.session_state.get('last_interaction_time', now)
    if inactive_duration > 300:
        st.session_state.is_paused = True
        if st.session_state.timer_mode == "Total Time (Minutes)":
            # Refund the lost idle time beyond the 5 min penalty
            st.session_state.remaining_seconds += (inactive_duration - 300)
        st.session_state.last_interaction_time = now
        st.rerun()

def record_activity():
    """Callback wrapper applied to buttons/inputs to record user activity."""
    now = time.time()
    
    # Process time normally before recording action
    if not st.session_state.is_paused:
        elapsed = now - st.session_state.last_calc_time
        if st.session_state.timer_mode == "Total Time (Minutes)":
            st.session_state.remaining_seconds -= elapsed
    
    st.session_state.last_calc_time = now
    
    # Check if they were already inactive before this action
    inactive_duration = now - st.session_state.last_interaction_time
    if inactive_duration > 300 and not st.session_state.is_paused:
        st.session_state.is_paused = True
        if st.session_state.timer_mode == "Total Time (Minutes)":
            st.session_state.remaining_seconds += (inactive_duration - 300)
        st.session_state.last_interaction_time = now
    else:
        # Normal interaction recorded
        st.session_state.last_interaction_time = now

# ==========================================
# 4. EXAM CONTROL & LOGIC FUNCTIONS
# ==========================================
def load_quiz(file_name):
    """Parses CSV correctly, filtering empty options, applies stored timer settings, and resets exam state."""
    st.session_state.questions = []
    file_path = os.path.join(CSV_FOLDER, file_name)
    
    with open(file_path, 'r', encoding='utf-8-sig', errors='ignore') as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Dynamic option loader ignores empty string cells
            opts = []
            for i in range(1, 6):
                col_name = f'Option{i}'
                if col_name in row and row[col_name].strip():
                    opts.append(row[col_name].strip())
            
            st.session_state.questions.append({
                'q': row['Question'].strip(), 
                'options': opts, 
                'ans': int(row['Answer']) - 1
            })
            
    # Apply Admin Configured Timer Settings
    timers_data = load_timers_data()
    t_config = timers_data.get(file_name, {"mode": "Total Time", "value": 30}) # Default to 30 mins
    
    if t_config["mode"] == "No Timer":
        t_mode = "No Timer"
        t_val = 0
        rem_sec = 0
    elif t_config["mode"] == "Per Question":
        t_mode = "Total Time (Minutes)" # We disguise it as Total Time so the existing visual timer works flawlessly
        total_seconds = len(st.session_state.questions) * t_config["value"]
        t_val = round(total_seconds / 60, 2)
        rem_sec = total_seconds
    else: # Total Time
        t_mode = "Total Time (Minutes)"
        t_val = t_config["value"]
        rem_sec = t_val * 60
            
    st.session_state.topic = os.path.splitext(file_name)[0].replace("_", " ")
    st.session_state.quiz_ready = True
    st.session_state.current_q = 0
    st.session_state.user_answers = {}
    st.session_state.visited_questions = {0}
    st.session_state.timer_mode = t_mode
    st.session_state.time_val = t_val
    st.session_state.remaining_seconds = rem_sec
    st.session_state.is_paused = False
    
    # Store test info for accurate attempt recording
    st.session_state.current_test_filename = file_name
    st.session_state.attempt_recorded = False

def calculate_score():
    """Calculates final score dynamically and safely."""
    score = 0
    for i, q in enumerate(st.session_state.questions):
        correct_ans = q['options'][q['ans']] if 0 <= q['ans'] < len(q['options']) else None
        if st.session_state.user_answers.get(i) == correct_ans:
            score += 1
    return score

# -- Button Navigation Callbacks --
def nav_goto(q_idx):
    record_activity()
    if not st.session_state.is_paused:
        st.session_state.current_q = q_idx

def nav_prev():
    record_activity()
    if not st.session_state.is_paused and st.session_state.current_q > 0:
        st.session_state.current_q -= 1

def nav_next():
    record_activity()
    if not st.session_state.is_paused and st.session_state.current_q < len(st.session_state.questions) - 1:
        st.session_state.current_q += 1

def nav_submit():
    record_activity()
    if not st.session_state.is_paused:
        st.session_state.active_page = "Result"
        record_attempt_usage()

def pause_exam():
    record_activity()
    st.session_state.is_paused = True

def clear_answer(q_idx):
    record_activity()
    if not st.session_state.is_paused:
        st.session_state.user_answers.pop(q_idx, None)
        st.session_state[f"radio_ans_{q_idx}"] = None

def on_radio_change(q_idx):
    record_activity()
    if not st.session_state.is_paused:
        selected = st.session_state.get(f"radio_ans_{q_idx}")
        if selected is not None:
            st.session_state.user_answers[q_idx] = selected
        else:
            st.session_state.user_answers.pop(q_idx, None)

# ==========================================
# 5. CSS & JAVASCRIPT INJECTION
# ==========================================
def inject_custom_css():
    """Injects responsive, modern, and bug-free CSS. Left untouched as requested."""
    try:
        with open('bg.jpg', "rb") as image_file:
            encoded_string = base64.b64encode(image_file.read())
            bg_css = f"""
            .stApp {{
                background-image: url(data:image/jpeg;base64,{encoded_string.decode()});
                background-size: cover;
                background-position: center;
                background-attachment: fixed;
            }}
            """
    except Exception:
        bg_css = ".stApp { background-color: #f8fafc; }"

    st.markdown(f"""
        <style>
        {bg_css}
        
        /* Main Professional Container */
        .block-container {{ 
            max-width: 98% !important; 
            padding: 1.5rem !important; 
            background-color: rgba(255, 255, 255, 0.98) !important; 
            border-radius: 16px;
            margin-top: 15px;
            box-shadow: 0 8px 32px rgba(0,0,0,0.15);
            transition: all 0.3s ease;
        }}
        
        /* Hide default Streamlit headers for clean UI */
        header[data-testid="stHeader"] {{ background-color: transparent !important; }}
        
        /* Force Text Colors to be readable inside main container */
        section[data-testid="stMain"] p, 
        section[data-testid="stMain"] h1, 
        section[data-testid="stMain"] h2, 
        section[data-testid="stMain"] h3, 
        section[data-testid="stMain"] h4, 
        section[data-testid="stMain"] h5, 
        section[data-testid="stMain"] h6, 
        section[data-testid="stMain"] label, 
        section[data-testid="stMain"] span,
        section[data-testid="stMain"] div[data-baseweb="radio"] div {{
            color: #0f172a !important; 
        }}

        /* Universal Button Styling */
        div.stButton > button {{ 
            background-color: #ffffff !important; 
            border: 2px solid #e2e8f0 !important;
            border-radius: 10px !important; 
            font-weight: 700 !important; 
            padding: 0.5rem 1rem !important; 
            width: 100%;
            font-size: 15px !important;
            transition: all 0.2s ease-in-out;
            color: #0f172a !important;
        }}
        div.stButton > button:hover {{
            border-color: #cbd5e1 !important;
            box-shadow: 0 4px 12px rgba(0,0,0,0.08);
            transform: translateY(-2px);
        }}
        
        /* Primary Buttons */
        div.stButton > button[kind="primary"] {{ 
            background: linear-gradient(135deg, #4f46e5 0%, #3b82f6 100%) !important; 
            border: none !important;
            color: #ffffff !important;
        }}
        div.stButton > button[kind="primary"] * {{
            color: #ffffff !important;
        }}
        div.stButton > button[kind="primary"]:hover {{
            box-shadow: 0 6px 20px rgba(79, 70, 229, 0.6) !important;
        }}

        /* Secondary Pause Buttons */
        div.stButton > button[kind="secondary"] {{
            background-color: #fff1f2 !important;
            border-color: #fecdd3 !important;
            color: #be123c !important;
        }}
        div.stButton > button[kind="secondary"] * {{
            color: #be123c !important;
        }}

        /* =========================================
           Testbook-Style Question Palette CSS
           ========================================= */
        .cbt-btn-wrapper {{ margin-bottom: 8px; }}

        /* Shared Palette Button Properties */
        .cbt-btn-wrapper div.stButton > button {{
            aspect-ratio: 1 / 1 !important;
            width: 100% !important;
            height: auto !important;
            padding: 0 !important;
            display: flex !important;
            align-items: center !important;
            justify-content: center !important;
            border-radius: 6px !important;
            border: 1px solid #cbd5e1 !important;
            transition: all 0.2s ease-in-out;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05) !important;
        }}
        
        .cbt-btn-wrapper div.stButton > button p {{
            margin: 0 !important;
            font-size: 15px !important;
            font-weight: 700 !important;
            line-height: 1 !important;
        }}

        /* Not Visited (White Background, Dark Text) */
        .cbt-not-visited div.stButton > button {{
            background-color: #ffffff !important;
            color: #334155 !important;
        }}
        .cbt-not-visited div.stButton > button p {{ color: #334155 !important; }}

        /* Answered (Green Background, White Text) */
        .cbt-answered div.stButton > button {{
            background-color: #22c55e !important;
            border-color: #16a34a !important;
            color: #ffffff !important;
        }}
        .cbt-answered div.stButton > button p {{ color: #ffffff !important; }}

        /* Not Answered / Visited (Red Background, White Text) */
        .cbt-not-answered div.stButton > button {{
            background-color: #ef4444 !important;
            border-color: #dc2626 !important;
            color: #ffffff !important;
        }}
        .cbt-not-answered div.stButton > button p {{ color: #ffffff !important; }}

        /* Current Question Highlight (Thick Blue Border) */
        .cbt-current div.stButton > button {{
            border: 3px solid #2563eb !important;
            transform: scale(1.08) !important;
            box-shadow: 0 0 10px rgba(37, 99, 235, 0.3) !important;
        }}
        
        /* Mobile Responsiveness */
        @media (max-width: 768px) {{
            .block-container {{ padding: 1rem 0.5rem !important; }}
            h3 {{ font-size: 1.3rem !important; line-height: 1.4 !important; }}
            div.stButton > button {{ font-size: 14px !important; padding: 0.4rem !important; }}
            
            /* Prevent buttons from becoming giant squares on mobile */
            .cbt-btn-wrapper div.stButton > button {{
                max-width: 50px !important;
                margin: 0 auto !important;
            }}
        }}
        </style>
    """, unsafe_allow_html=True)

def render_visual_timer():
    """Renders a 100% safe, read-only HTML timer that doesn't trigger endless reruns."""
    is_timed = (st.session_state.timer_mode == "Total Time (Minutes)")
    rem_sec = int(max(0, st.session_state.remaining_seconds))
    
    html_code = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ margin:0; padding:0; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }}
            .timer-box {{ 
                background: linear-gradient(135deg, #fee2e2 0%, #fecaca 100%); 
                border: 2px solid #ef4444; 
                color: #b91c1c; 
                padding: 12px 0; 
                border-radius: 12px; 
                font-size: 24px; 
                font-weight: 800; 
                text-align: center; 
                box-shadow: 0 4px 6px rgba(239, 68, 68, 0.2); 
                letter-spacing: 1px;
            }}
            .no-timer {{ 
                background: linear-gradient(135deg, #e0f2fe 0%, #bae6fd 100%); 
                border-color: #38bdf8; 
                color: #0369a1; 
            }}
        </style>
    </head>
    <body>
        <div id="t-box" class="timer-box {'no-timer' if not is_timed else ''}">
            ⏳ <span id="time">Loading...</span>
        </div>
        <script>
            var is_timed = {1 if is_timed else 0};
            var rem = {rem_sec};
            var display = document.getElementById("time");
            
            if (!is_timed) {{
                display.innerHTML = "No Time Limit";
            }} else {{
                function updateDisplay() {{
                    if (rem <= 0) {{
                        display.innerHTML = "TIME UP! Click Submit.";
                        return false;
                    }}
                    var m = Math.floor(rem / 60);
                    var s = Math.floor(rem % 60);
                    display.innerHTML = (m < 10 ? "0" + m : m) + ":" + (s < 10 ? "0" + s : s);
                    return true;
                }}
                updateDisplay();
                var x = setInterval(function() {{
                    rem--;
                    if (!updateDisplay()) clearInterval(x);
                }}, 1000);
            }}
        </script>
    </body>
    </html>
    """
    components.html(html_code, height=75)

# ==========================================
# 6. PAGE RENDERING FUNCTIONS
# ==========================================

def render_login():
    """Renders the secure login portal."""
    st.write("<br><br><br>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 1.5, 1]) 
    with col2:
        with st.container():
            st.markdown("<h1 style='text-align: center; color:#4F46E5 !important; font-weight: 800;'>🎓 Study Booster</h1>", unsafe_allow_html=True)
            st.markdown("<p style='text-align: center; font-size: 1.1rem; color: #64748b !important;'>Sign in to access your dashboard</p>", unsafe_allow_html=True)
            st.divider()
            
            username = st.selectbox("👤 Select Profile", ["-- Select User --"] + list(ALLOWED_USERS.keys()))
            pwd = st.text_input("🔑 Enter Passcode", type="password")
            
            st.write("")
            if st.button("Secure Login 🚀", type="primary", use_container_width=True):
                if username != "-- Select User --" and ALLOWED_USERS.get(username) == pwd:
                    st.session_state.auth = True
                    st.session_state.current_user = username
                    st.session_state.active_page = "Dashboard"
                    st.rerun()
                else:
                    st.error("❌ Invalid Credentials! Please try again.")

def render_sidebar():
    """Renders the standard navigation sidebar."""
    try:
        st.sidebar.image("logo.png", use_container_width=True)
    except:
        st.sidebar.markdown("<h2 style='text-align: center; color: #4F46E5;'>🎓 Study Booster</h2>", unsafe_allow_html=True)

    st.sidebar.markdown(f"### 👤 {st.session_state.current_user}")
    st.sidebar.divider()
    
    if st.sidebar.button("📚 Dashboard", use_container_width=True):
        st.session_state.active_page = "Dashboard"
        st.rerun()
        
    st.sidebar.divider()
    if st.sidebar.button("🚪 Logout", type="secondary", use_container_width=True):
        st.session_state.auth = False
        st.rerun()

def render_dashboard():
    """Renders the main dashboard for loading and starting tests."""
    st.markdown("<h1 style='color: #1e293b;'>Welcome to Study Booster! 🚀</h1>", unsafe_allow_html=True)
    st.markdown("<p style='font-size: 1.1rem; color: #475569;'>Select a test series below to begin.</p>", unsafe_allow_html=True)
    st.write("---")
    
    if "Admin" in st.session_state.current_user:
        
        # --- FEATURE 1: CSV MANAGEMENT ADMIN PANEL ---
        with st.expander("📁 Admin Panel: CSV Management", expanded=False):
            st.markdown("#### 📤 Upload New CSV")
            uploaded_file = st.file_uploader("Upload CSV Format File", type=['csv'])
            if uploaded_file:
                save_path = os.path.join(CSV_FOLDER, uploaded_file.name)
                if os.path.exists(save_path):
                    st.error(f"File '{uploaded_file.name}' already exists. Please delete it first or rename your file.")
                else:
                    with open(save_path, "wb") as f:
                        f.write(uploaded_file.getbuffer())
                    st.success("✅ Test uploaded successfully!")
                    time.sleep(1)
                    st.rerun()
            
            st.markdown("#### 📋 Available CSV Files")
            all_tests_admin = [f for f in os.listdir(CSV_FOLDER) if f.endswith('.csv')]
            if not all_tests_admin:
                st.info("No CSV files found.")
            else:
                for f_name in all_tests_admin:
                    file_p = os.path.join(CSV_FOLDER, f_name)
                    f_size = os.path.getsize(file_p) / 1024 # KB Size
                    
                    # Fast calculate Total Questions
                    q_cnt = 0
                    with open(file_p, 'r', encoding='utf-8-sig', errors='ignore') as f:
                        q_cnt = sum(1 for _ in f) - 1 # Subtract Header
                    
                    c1, c2, c3 = st.columns([4, 2, 2])
                    c1.markdown(f"**{f_name}**")
                    c2.markdown(f"Questions: {q_cnt} | Size: {f_size:.1f} KB")
                    c3.markdown("")
                
                st.markdown("#### 🗑️ Delete CSV")
                del_file = st.selectbox("Select file to delete", ["-- Select --"] + all_tests_admin)
                if del_file != "-- Select --":
                    if st.checkbox(f"Are you sure you want to delete {del_file}?"):
                        if st.button("Yes, Delete Test", type="primary"):
                            os.remove(os.path.join(CSV_FOLDER, del_file))
                            st.success(f"Deleted {del_file}!")
                            time.sleep(1)
                            st.rerun()

        # --- FEATURE 2: TIMER MANAGEMENT ADMIN PANEL ---
        with st.expander("⏱️ Admin Panel: Timer Management", expanded=False):
            st.markdown("Configure timer rules for each test individually.")
            all_tests_admin_tmr = [f for f in os.listdir(CSV_FOLDER) if f.endswith('.csv')]
            
            if all_tests_admin_tmr:
                t_file = st.selectbox("Select Test to Configure Timer", all_tests_admin_tmr, key="tmr_test")
                if t_file:
                    timers_data = load_timers_data()
                    current_settings = timers_data.get(t_file, {"mode": "Total Time", "value": 30})
                    
                    new_mode = st.radio(
                        "Timer Mode", 
                        ["Total Time", "Per Question", "No Timer"], 
                        index=["Total Time", "Per Question", "No Timer"].index(current_settings["mode"])
                    )
                    new_val = current_settings.get("value", 30)
                    
                    if new_mode == "Total Time":
                        new_val = st.number_input("Total Minutes", min_value=1, value=new_val if current_settings["mode"] == "Total Time" else 30)
                    elif new_mode == "Per Question":
                        new_val = st.number_input("Seconds per Question", min_value=1, value=new_val if current_settings["mode"] == "Per Question" else 45)
                    else:
                        new_val = 0 # No Timer
                    
                    if st.button("Save Timer Settings", type="primary"):
                        timers_data[t_file] = {"mode": new_mode, "value": new_val}
                        save_timers_data(timers_data)
                        st.success(f"✅ Timer settings saved for {t_file}!")
            else:
                st.info("No tests available to configure.")

        # --- ATTEMPT MANAGEMENT ADMIN PANEL ---
        with st.expander("⚙️ Admin Panel: Attempt Management", expanded=False):
            st.markdown("Select a user and a test to modify attempt limits.")
            a_col1, a_col2 = st.columns(2)
            with a_col1:
                sel_user = st.selectbox("Select User", list(ALLOWED_USERS.keys()), key="adm_user")
            with a_col2:
                all_tests_admin_att = [f for f in os.listdir(CSV_FOLDER) if f.endswith('.csv')]
                if all_tests_admin_att:
                    sel_test = st.selectbox("Select Test", all_tests_admin_att, key="adm_test")
                else:
                    sel_test = None
            
            if sel_user and sel_test:
                curr_data = get_attempt_data(sel_user, sel_test)
                new_limit = st.number_input("Allowed Attempts", min_value=1, value=curr_data['allowed'], key="adm_limit")
                if st.button("Update Limit", type="primary", key="btn_update_limit"):
                    set_allowed_attempts(sel_user, sel_test, new_limit)
                    st.success(f"✅ Updated! {sel_user.split()[0]} now has {new_limit} allowed attempts for {sel_test.replace('.csv', '').replace('_', ' ')}.")
    
    # --- STUDENTS VIEW (DASHBOARD TESTS LIST) ---
    col_space1, col_tests, col_space2 = st.columns([1, 4, 1])
    
    with col_tests:
        st.markdown("### 📋 Available Test Series")
        files = [f for f in os.listdir(CSV_FOLDER) if f.endswith('.csv')]
        
        if not files: 
            st.info("No test series available right now. Contact Administrator.")
        else:
            with st.container(border=True):
                for file in files:
                    user = st.session_state.current_user
                    attempt_data = get_attempt_data(user, file)
                    allowed = attempt_data['allowed']
                    used = attempt_data['used']
                    remaining = allowed - used

                    c1, c2 = st.columns([3, 1])
                    c1.markdown(f"<h5 style='margin-top: 10px; margin-bottom: 2px;'>📄 {file.replace('.csv', '').replace('_', ' ')}</h5>", unsafe_allow_html=True)
                    
                    # Display updated attempts count
                    c1.markdown(f"<p style='font-size: 0.85rem; color: #64748b; margin-top: 0;'>Attempts: {used} / {allowed} &nbsp;|&nbsp; Remaining: {remaining}</p>", unsafe_allow_html=True)
                    
                    if remaining > 0:
                        if c2.button("Load Test", key=f"load_{file}"):
                            load_quiz(file)
                    else:
                        c2.button("Limit Reached", key=f"limit_{file}", disabled=True, help="You have reached the maximum number of attempts allowed for this test. Please contact the administrator.")
                        
    # Start Test section appended directly to dashboard bottom
    if st.session_state.quiz_ready:
        st.divider()
        st.success(f"✅ **{st.session_state.topic}** is loaded and ready.")
        col_space1, col_start, col_space2 = st.columns([1, 2, 1])
        with col_start:
            if st.button("🚀 Proceed to Instructions", type="primary", use_container_width=True):
                st.session_state.active_page = "Instructions"
                st.rerun()

def render_instructions():
    """Renders the pre-exam instructions page."""
    st.markdown(f"<h1 style='color: #4F46E5; text-align: center;'>📜 Instructions</h1>", unsafe_allow_html=True)
    st.markdown(f"<h3 style='text-align: center; color: #475569;'>{st.session_state.topic}</h3>", unsafe_allow_html=True)
    st.divider()
    
    col1, col2, col3 = st.columns([1, 3, 1])
    with col2:
        with st.container(border=True):
            st.markdown("### Please read carefully before starting:")
            st.markdown(f"🔹 **Total Questions:** {len(st.session_state.questions)}")
            
            # Format time display dynamically 
            time_display_str = "No Time Limit"
            if st.session_state.timer_mode != "No Timer":
                time_display_str = f"{st.session_state.time_val} Minutes"

            st.markdown(f"🔹 **Time Limit:** {time_display_str}")
            st.markdown("""
            🔹 **Navigation:** You can jump to any question using the Question Palette on the right.
            🔹 **Auto-Pause:** If you become completely inactive for **5 minutes**, the exam will pause itself to save your time safely.
            🔹 **Marking Scheme:** Every correct answer adds to your score. No negative marking.
            🔹 **Submission:** Exam submits automatically when timer hits zero.
            """)
            
            st.write("<br>", unsafe_allow_html=True)
            if st.button("✅ I have read the instructions. Begin Exam.", type="primary", use_container_width=True):
                now = time.time()
                st.session_state.last_calc_time = now
                st.session_state.last_interaction_time = now
                st.session_state.is_paused = False
                st.session_state.active_page = "Exam"
                st.rerun()

def render_paused_screen():
    """Renders a simple, reliable screen when the test is paused."""
    st.write("<br><br>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        with st.container(border=True):
            st.markdown("<h1 style='text-align: center; color: #b91c1c;'>⏸ Exam Paused</h1>", unsafe_allow_html=True)
            st.markdown("<p style='text-align: center; color: #475569; font-size: 1.1rem;'>Your timer has been frozen and your progress is safely saved.</p>", unsafe_allow_html=True)
            st.write("---")
            if st.button("▶️ Resume Test", type="primary", use_container_width=True):
                now = time.time()
                st.session_state.last_calc_time = now
                st.session_state.last_interaction_time = now
                st.session_state.is_paused = False
                st.rerun()

def render_exam():
    """Renders the main Examination Layout, securely executing state interactions."""
    if st.session_state.is_paused:
        render_paused_screen()
        return

    q_idx = st.session_state.current_q
    st.session_state.visited_questions.add(q_idx)
    total_q = len(st.session_state.questions)
    q_data = st.session_state.questions[q_idx]

    # Inject Exam-specific CSS to strictly target the right panel (col_pal)
    # This ensures no global components (like Dashboard) are affected by the redesign.
    st.markdown("""
    <style>
    /* Question Panel (Right Column) Complete Redesign */
    div[data-testid="column"]:nth-of-type(2) {
        background-color: #f0f8ff !important; /* Testbook light blue panel bg */
        border: 1px solid #bfdbfe !important;
        border-radius: 8px !important;
        padding-bottom: 15px !important;
        overflow: hidden; /* Ensures child element negative margins don't break border radius */
    }
    
    /* Perfect Square Grid Buttons */
    .cbt-btn-wrapper div.stButton > button {
        aspect-ratio: 1 / 1 !important;
        width: 100% !important;
        border-radius: 4px !important;
        border: 1px solid #cbd5e1 !important;
        padding: 0 !important;
        font-size: 13px !important; /* Reduced slightly to fit double digits */
        font-weight: 600 !important;
        background-color: #ffffff !important;
        color: #334155 !important;
        min-width: 0 !important; /* Forces uniform shape */
        min-height: 0 !important; /* Forces uniform shape */
        line-height: 1 !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
    }

    /* FORCES NUMBERS TO STAY IN A SINGLE LINE */
    .cbt-btn-wrapper div.stButton > button p {
        margin: 0 !important;
        padding: 0 !important;
        font-size: 13px !important;
        white-space: nowrap !important; 
    }

    .cbt-btn-wrapper.cbt-answered div.stButton > button {
        background-color: #2bc765 !important; /* Testbook Green */
        border-color: #2bc765 !important;
        color: white !important;
    }

    .cbt-btn-wrapper.cbt-not-answered div.stButton > button {
        background-color: #e55a45 !important; /* Testbook Red/Orange */
        border-color: #e55a45 !important;
        color: white !important;
    }

    .cbt-btn-wrapper.cbt-not-visited div.stButton > button {
        background-color: #ffffff !important;
        border-color: #cbd5e1 !important;
        color: #475569 !important;
    }

    /* Current Question Highlight */
    .cbt-btn-wrapper.cbt-current div.stButton > button {
        border: 2px solid #2563eb !important;
        box-shadow: 0 0 0 3px rgba(37,99,235,0.2) !important;
        transform: scale(1.08) !important;
        z-index: 2;
    }
    
    /* Bottom buttons specifically mapped in the Right Panel */
    div[data-testid="column"]:nth-of-type(2) div[data-testid="stHorizontalBlock"] div.stButton > button {
        background-color: #dbeafe !important;
        color: #1e40af !important;
        border: none !important;
        font-size: 13px !important;
        border-radius: 4px !important;
    }
    div[data-testid="column"]:nth-of-type(2) > div[data-testid="stVerticalBlock"] > div:last-child div.stButton > button {
        background-color: #0ea5e9 !important; /* Cyan Submit Button */
        color: white !important;
        border: none !important;
        font-size: 14px !important;
        border-radius: 4px !important;
        margin-top: 5px !important;
    }
    </style>
    """, unsafe_allow_html=True)

    # Native responsive Streamlit columns
    col_main, col_pal = st.columns([7, 3]) 
    
    # ================== RIGHT PANEL (Timer + Palette) ==================
    with col_pal:
        render_visual_timer()
        
        # Calculate Legend Counts based on existing logic
        ans_count = len(st.session_state.user_answers)
        visited_count = len(st.session_state.visited_questions)
        not_ans_count = visited_count - ans_count
        not_visit_count = total_q - visited_count
        
        username_display = st.session_state.current_user.split()[0]
        avatar_letter = username_display[0].upper() if username_display else "U"
        
        # Testbook-style Profile & Legend Redesign
        # Note: HTML is strictly left-aligned to prevent Streamlit's Markdown parser from mistakenly treating it as a raw code block.
        html_legend = f"""
<div style="background-color: #ffffff; padding: 15px; border-bottom: 1px solid #bfdbfe; margin: 10px -1.5rem 0 -1.5rem;">
<div style="display: flex; align-items: center; gap: 10px; margin-bottom: 15px;">
<div style="width: 34px; height: 34px; background-color: #3b82f6; color: white; border-radius: 50%; display: flex; justify-content: center; align-items: center; font-weight: bold; font-size: 16px;">
<img src="https://ui-avatars.com/api/?name={username_display}&background=3b82f6&color=fff&rounded=true&bold=true&size=34" style="border-radius: 50%;" onerror="this.style.display='none'; this.parentElement.innerText='{avatar_letter}';">
</div>
<span style="font-weight: 600; color: #1e293b; font-size: 15px;">{username_display}</span>
</div>
<div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 8px 4px; font-size: 11px; color: #475569;">
<div style="display: flex; align-items: center; gap: 4px;">
<div style="width: 18px; height: 18px; background-color: #2bc765; color: white; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-weight: bold; font-size: 10px;">{ans_count}</div>
<span>Answered</span>
</div>
<div style="display: flex; align-items: center; gap: 4px;">
<div style="width: 18px; height: 18px; background-color: #9d48b1; color: white; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-weight: bold; font-size: 10px;">0</div>
<span>Marked</span>
</div>
<div style="display: flex; align-items: center; gap: 4px;">
<div style="width: 18px; height: 18px; background-color: #ffffff; border: 1px solid #cbd5e1; color: #333; border-radius: 3px; display: flex; align-items: center; justify-content: center; font-weight: bold; font-size: 10px;">{not_visit_count}</div>
<span>Not Visited</span>
</div>
<div style="display: flex; align-items: center; gap: 4px; grid-column: span 2;">
<div style="width: 18px; height: 18px; background-color: #9d48b1; color: white; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-weight: bold; font-size: 10px; position: relative;">0<div style="position: absolute; bottom: -2px; right: -2px; width: 8px; height: 8px; background-color: #2bc765; border-radius: 50%; border: 1px solid white;"></div></div>
<span>Marked and answered</span>
</div>
<div style="display: flex; align-items: center; gap: 4px;">
<div style="width: 18px; height: 18px; background-color: #e55a45; color: white; border-radius: 3px; display: flex; align-items: center; justify-content: center; font-weight: bold; font-size: 10px;">{not_ans_count}</div>
<span>Not Answered</span>
</div>
</div>
</div>
"""
        st.markdown(html_legend, unsafe_allow_html=True)
        
        # Testbook-style Section Header
        st.markdown(
            f"""<div style='background-color:#dbeafe; padding:8px 15px; font-weight:700; color:#1e3a8a; font-size:12px; text-transform: uppercase; margin: 0 -1.5rem 10px -1.5rem; border-bottom: 1px solid #bfdbfe;'>
            SECTION : {st.session_state.topic}
            </div>""", 
            unsafe_allow_html=True
        )
        
        # Independent Scrollable Container for the Buttons Grid
        try:
            palette_scroll = st.container(height=350, border=False)
        except TypeError:
            try:
                palette_scroll = st.container(height=350)
            except TypeError:
                palette_scroll = st.container()

        # Flex Grid Palette inside the independent scroll container
        with palette_scroll:
            grid_cols = st.columns(5)
            for i in range(total_q):
                is_ans = st.session_state.user_answers.get(i) is not None
                is_vis = i in st.session_state.visited_questions
                is_curr = (i == q_idx)
                
                # Determine class based on state exactly matching reference logic
                wrapper_class = "cbt-btn-wrapper"
                if is_ans:
                    wrapper_class += " cbt-answered"
                elif is_vis:
                    wrapper_class += " cbt-not-answered"
                else:
                    wrapper_class += " cbt-not-visited"
                    
                if is_curr:
                    wrapper_class += " cbt-current"
                    
                with grid_cols[i % 5]:
                    st.markdown(f"<div class='{wrapper_class}'>", unsafe_allow_html=True)
                    st.button(f"{i+1}", key=f"pal_{i}", on_click=nav_goto, args=(i,))
                    st.markdown("</div>", unsafe_allow_html=True)
                    
        # Fixed Bottom Action Area
        st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)
        b1, b2 = st.columns(2)
        with b1:
            st.button("Question Paper", use_container_width=True, key="btn_qp")
        with b2:
            st.button("Instructions", use_container_width=True, key="btn_inst")
            
        st.button("Submit Test", type="primary", use_container_width=True, key="btn_sub_right", on_click=nav_submit)

    # ================== LEFT PANEL (Main Question Area) ==================
    # This section is strictly left untouched as per instructions.
    with col_main:
        st.markdown(f"<h2 style='color:#4F46E5 !important; margin-top:0;'>{st.session_state.topic}</h2>", unsafe_allow_html=True)
        st.write("---")
        
        # Clean double question numbers (e.g., 'Q1. Q1. Text' -> 'Q1. Text') and adjust font size
        raw_q = q_data['q']
        clean_q = re.sub(r'^[Qq]?(?:uestion)?\s*\d+[\.\)]\s*', '', raw_q)
        
        # Render Question with 1.3rem (~20px) which is ~1.5x the size of the standard option font (~14px)
        st.markdown(f"<div style='font-size: 1.3rem; font-weight: 600; line-height: 1.6; color: #1e293b; margin-bottom: 15px;'>Q{q_idx + 1}. {clean_q}</div>", unsafe_allow_html=True)
        
        # State-Synced Radio Implementation
        saved_ans = st.session_state.user_answers.get(q_idx)
        st.session_state[f"radio_ans_{q_idx}"] = saved_ans

        try:
            default_index = q_data['options'].index(saved_ans) if saved_ans in q_data['options'] else None
        except ValueError:
            default_index = None
            
        st.radio(
            "Options:", 
            options=q_data['options'], 
            index=default_index, 
            key=f"radio_ans_{q_idx}", 
            on_change=on_radio_change,
            args=(q_idx,),
            label_visibility="collapsed"
        )
            
        st.write("<br><br>", unsafe_allow_html=True)
        
        # Bottom Navigation Control Panel
        b_col1, b_col2, b_col3, b_col4, b_col5 = st.columns([2, 2, 2, 2, 2])
        
        with b_col1:
            st.button("⏪ Previous", on_click=nav_prev, use_container_width=True)
                
        with b_col2:
            st.button("🧹 Clear", on_click=clear_answer, args=(q_idx,), use_container_width=True)
                
        with b_col3:
            is_last = (q_idx == total_q - 1)
            if not is_last:
                st.button("Next ⏩", type="primary", on_click=nav_next, use_container_width=True)
            else:
                st.button("Finish", type="secondary", disabled=True, use_container_width=True)
                    
        with b_col4:
            st.button("⏸ Pause", type="secondary", on_click=pause_exam, use_container_width=True)
                
        with b_col5:
            st.button("🚀 Final Submit", type="primary", on_click=nav_submit, use_container_width=True)

def render_result():
    """Renders the detailed post-exam result analysis."""
    total_q = len(st.session_state.questions)
    score = calculate_score()
    attempted = len(st.session_state.user_answers)
    
    st.markdown("<h1 style='color: #4F46E5; text-align: center;'>🏆 Performance Analysis</h1>", unsafe_allow_html=True)
    st.divider()
    
    c1, c2, c3 = st.columns(3)
    with c1:
        st.info(f"### 📝 Attempted\n# {attempted} / {total_q}")
    with c2:
        st.success(f"### ✅ Score\n# {score} / {total_q}")
    with c3:
        accuracy = round((score / attempted * 100) if attempted > 0 else 0, 1)
        st.warning(f"### 🎯 Accuracy\n# {accuracy}%")
        
    st.write("<br><br>", unsafe_allow_html=True)
    st.markdown("### 📋 Detailed Answer Key")
    st.write("---")
    
    for i, q in enumerate(st.session_state.questions):
        st.markdown(f"**Q{i+1}: {q['q']}**")
        
        # Safely pull correct answer based on accurate length checking
        correct_ans = q['options'][q['ans']] if 0 <= q['ans'] < len(q['options']) else "N/A"
        user_ans = st.session_state.user_answers.get(i)
        
        if user_ans == correct_ans: 
            st.success(f"**Your Answer:** {user_ans} (✅ Correct)")
        elif user_ans is None: 
            st.warning(f"**Not Attempted.** Correct Answer: {correct_ans}")
        else: 
            st.error(f"**Your Answer:** {user_ans} (❌ Wrong)")
            st.info(f"**Correct Answer:** {correct_ans}")
        st.write("---")
        
    st.write("<br>", unsafe_allow_html=True)
    if st.button("🏠 Back to Dashboard", type="primary"):
        st.session_state.active_page = "Dashboard"
        st.session_state.quiz_ready = False
        st.rerun()

# ==========================================
# 7. MAIN APPLICATION LOOP
# ==========================================
def main():
    init_session()
    
    # 1. Passive time calculation before any page render executes
    passive_time_check()
    
    # 2. Universal styling setup
    inject_custom_css()
    
    # 3. Secure routing logic
    if not st.session_state.auth:
        render_login()
    else:
        render_sidebar()
        
        # 4. App Engine Workflow
        if st.session_state.active_page == "Dashboard":
            render_dashboard()
        elif st.session_state.active_page == "Instructions":
            render_instructions()
        elif st.session_state.active_page == "Exam":
            render_exam()
        elif st.session_state.active_page == "Result":
            render_result()

if __name__ == "__main__":
    main()
