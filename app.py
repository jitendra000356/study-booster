### 🛠️ DEBUG REPORT

**1. Critical Bug: Infinite Rerun & White Screen (Timer / Auto-Pause Crash)**

* **Root Cause:** The `inject_timer_and_autopause_js` function injected an HTML component running a `setInterval` that used `window.parent.document.querySelectorAll('button')` to click standard Streamlit buttons (like `AutoPauseTrigger` or `Final Submit`). Because Streamlit runs components in an iframe, constantly interacting with the parent DOM aggressively triggers React state updates. On top of that, every rerun injected a *new* interval, causing an avalanche of clicks, resulting in an infinite rerun loop and eventually a white screen.
* **File Location:** `inject_timer_and_autopause_js()` and `render_exam()`
* **Fix:** Completely removed the unsafe JavaScript DOM manipulation. Replaced the auto-pause and timer logic with a **server-side timestamp architecture**. Time tracking is now done mathematically using Python's `time.time()`. The visual timer is now a safe, isolated read-only JS script that doesn't interact with the parent window.

**2. State Corruption Bug: Question Radio Buttons Losing State**

* **Root Cause:** The code used a dynamically changing key for the radio buttons: `key=f"rad_{q_idx}_{clear_key}"`. When the key dynamically changes or evaluates out-of-bounds, Streamlit drops the component from the state tree, leading to unhandled `ValueError` crashes and wiped user answers when navigating back and forth.
* **File Location:** `render_exam()`
* **Fix:** Bound the radio button safely to session state using a static key (`f"radio_ans_{q_idx}"`). Used Streamlit's native `index` properties and handled the `on_change` callback natively to synchronize answers with `st.session_state.user_answers`.

**3. Bug: Navigation / Layout Freezing & "Sticky Palette" Breaking Mobile UI**

* **Root Cause:** The application attempted to force CSS `position: sticky` onto a Streamlit layout column via injected JavaScript (`col.style.position = '-webkit-sticky'`). This broke responsive flexbox calculations, causing extreme layout glitches on mobile devices and overlapping elements.
* **File Location:** `inject_timer_and_autopause_js()`
* **Fix:** Removed the sticky JS script completely. Relied strictly on Streamlit's native `st.columns()` capability, which correctly and gracefully stacks the main question window above the palette window natively on mobile screens.

**4. Data Error: CSV Parsing Failing on Empty Options**

* **Root Cause:** `q_data['options']` rigidly extracted exactly 5 options: `[row['Option1'], ..., row['Option5']]`. If a CSV contained a question with only 3 or 4 options, it rendered empty strings as valid radio options, crashing the index-matching function.
* **File Location:** `load_quiz()`
* **Fix:** Implemented a list comprehension to dynamically check and load only non-empty option strings during CSV parsing.

**5. Logic Flaw: Missing robust Pause/Resume Lifecycle**

* **Root Cause:** The `is_paused` flag was disconnected from the timer logic. If paused, time kept running in the background. If the user resumed, their exam would instantly submit.
* **File Location:** `render_exam()`, `pause_exam()`
* **Fix:** Overhauled the timer ecosystem using `last_calc_time` and `last_interaction_time`. Time only ticks away natively during an active session, pausing mathematically freezes the timer, and resuming restores the exact state perfectly.

---

### 💻 COMPLETE APPLICATION (`study_booster_app.py`)

```python
import streamlit as st
import streamlit.components.v1 as components
import csv
import os
import time
import base64

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
        'is_paused': False
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
def load_quiz(file_name, timer_mode, time_minutes):
    """Parses CSV correctly, filtering empty options, and resets exam state."""
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
            
    st.session_state.topic = os.path.splitext(file_name)[0].replace("_", " ")
    st.session_state.quiz_ready = True
    st.session_state.current_q = 0
    st.session_state.user_answers = {}
    st.session_state.visited_questions = {0}
    st.session_state.timer_mode = timer_mode
    st.session_state.time_val = time_minutes
    st.session_state.remaining_seconds = time_minutes * 60
    st.session_state.is_paused = False

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
    """Injects responsive, modern, and bug-free CSS."""
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

        /* Palette grid tweaks for better sizing */
        .palette-button-container {{ margin-bottom: 8px; }}
        
        /* Mobile Responsiveness */
        @media (max-width: 768px) {{
            .block-container {{ padding: 1rem 0.5rem !important; }}
            h3 {{ font-size: 1.3rem !important; line-height: 1.4 !important; }}
            div.stButton > button {{ font-size: 14px !important; padding: 0.4rem !important; }}
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
    st.markdown("<p style='font-size: 1.1rem; color: #475569;'>Select and configure your test settings below before starting.</p>", unsafe_allow_html=True)
    st.write("---")
    
    if "Admin" in st.session_state.current_user:
        with st.expander("⚙️ Admin Panel: Upload New Quiz File", expanded=False):
            uploaded_file = st.file_uploader("Upload CSV Format File", type=['csv'])
            if uploaded_file:
                with open(os.path.join(CSV_FOLDER, uploaded_file.name), "wb") as f: 
                    f.write(uploaded_file.getbuffer())
                st.success("✅ Test uploaded successfully! It is now available below.")
    
    col_settings, col_tests = st.columns([1, 1.5])
    
    with col_settings:
        st.markdown("### ⏱️ Exam Settings")
        with st.container(border=True):
            t_mode = st.radio("Timer Setup:", ["Total Time (Minutes)", "No Timer"], horizontal=True)
            t_val = 0
            if t_mode == "Total Time (Minutes)": 
                t_val = st.number_input("Enter Total Duration (in Minutes):", min_value=1, value=30, step=5)
            
    with col_tests:
        st.markdown("### 📋 Available Test Series")
        files = [f for f in os.listdir(CSV_FOLDER) if f.endswith('.csv')]
        
        if not files: 
            st.info("No test series available right now. Contact Administrator.")
        else:
            with st.container(border=True):
                for file in files:
                    c1, c2 = st.columns([3, 1])
                    c1.markdown(f"<h5 style='margin-top: 10px;'>📄 {file.replace('.csv', '').replace('_', ' ')}</h5>", unsafe_allow_html=True)
                    if c2.button("Load Test", key=f"load_{file}"):
                        load_quiz(file, t_mode, t_val)
                        
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
            st.markdown(f"🔹 **Time Limit:** {'No Time Limit' if st.session_state.timer_mode == 'No Timer' else f'{st.session_state.time_val} Minutes'}")
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

    # Native responsive Streamlit columns (Stacks automatically on mobile)
    col_main, col_pal = st.columns([7, 3]) 
    
    # ================== RIGHT PANEL (Timer + Palette) ==================
    with col_pal:
        render_visual_timer()
        
        st.markdown("<h4 style='text-align:center; margin-top:10px;'>Question Palette</h4>", unsafe_allow_html=True)
        st.markdown(
            "<p style='text-align:center; font-size:13px; font-weight:600; margin-bottom:15px; color:#475569;'>"
            "🔵 Curr &nbsp;|&nbsp; 🟢 Ans &nbsp;|&nbsp; 🔴 Skip &nbsp;|&nbsp; ⚪ Unvisit"
            "</p>", unsafe_allow_html=True
        )
        
        # Flex Grid Palette
        grid_cols = st.columns(5)
        for i in range(total_q):
            if st.session_state.user_answers.get(i) is not None: 
                icon = "🟢"
            elif i == q_idx: 
                icon = "🔵"
            elif i in st.session_state.visited_questions: 
                icon = "🔴"
            else: 
                icon = "⚪"
                
            with grid_cols[i % 5]:
                st.markdown("<div class='palette-button-container'>", unsafe_allow_html=True)
                st.button(f"{icon}\n{i+1}", key=f"pal_{i}", on_click=nav_goto, args=(i,))
                st.markdown("</div>", unsafe_allow_html=True)

    # ================== LEFT PANEL (Main Question Area) ==================
    with col_main:
        st.markdown(f"<h2 style='color:#4F46E5 !important; margin-top:0;'>{st.session_state.topic}</h2>", unsafe_allow_html=True)
        st.write("---")
        
        st.markdown(f"<h3 style='line-height: 1.6;'>Q{q_idx + 1}. {q_data['q']}</h3>", unsafe_allow_html=True)
        
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

```
