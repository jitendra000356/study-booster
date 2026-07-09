import streamlit as st
import streamlit.components.v1 as components
import csv
import os
import time
import base64
from datetime import datetime

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
    """Initialize all session state variables."""
    default_state = {
        'auth': False, 
        'current_user': "", 
        'questions': [], 
        'current_q': 0,
        'user_answers': {}, 
        'visited_questions': set(), 
        'quiz_completed': False, 
        'quiz_ready': False, 
        'exam_started': False, 
        'topic': "", 
        'end_time': 0, 
        'timer_mode': "No Timer", 
        'time_val': 0,
        'active_page': "Dashboard",   # Controls the new linear workflow
        'is_paused': False,           # Pause/Resume functionality
        'remaining_seconds': 0        # Stores exact time remaining when paused
    }
    for key, value in default_state.items():
        if key not in st.session_state:
            st.session_state[key] = value

# ==========================================
# 3. CORE LOGIC FUNCTIONS
# ==========================================
def load_quiz(file_name, timer_mode, time_minutes):
    """Parses CSV and sets up the exam structure."""
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
    st.session_state.is_paused = False
    st.session_state.remaining_seconds = time_minutes * 60

def pause_exam():
    """Pauses the exam and freezes the timer."""
    if not st.session_state.is_paused:
        st.session_state.is_paused = True
        if st.session_state.timer_mode == "Total Time (Minutes)":
            # Save the exact remaining seconds
            st.session_state.remaining_seconds = int(st.session_state.end_time - time.time())
            # Ensure it doesn't drop below 0
            if st.session_state.remaining_seconds < 0:
                st.session_state.remaining_seconds = 0

def resume_exam():
    """Resumes the exam and recalculates the end time."""
    if st.session_state.is_paused:
        st.session_state.is_paused = False
        if st.session_state.timer_mode == "Total Time (Minutes)":
            # Push the end time forward based on the frozen remaining seconds
            st.session_state.end_time = time.time() + st.session_state.remaining_seconds

def calculate_score():
    """Calculates final score dynamically."""
    score = sum(
        1 for i, q in enumerate(st.session_state.questions) 
        if st.session_state.user_answers.get(i) == q['options'][q['ans']]
    )
    return score

# ==========================================
# 4. CSS & JAVASCRIPT INJECTION
# ==========================================
def inject_custom_css():
    """Injects responsive, modern, and dark-mode safe CSS."""
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
        bg_css = ".stApp { background-color: #f0f4f8; }"

    st.markdown(f"""
        <style>
        {bg_css}
        
        /* Main Professional Container */
        .block-container {{ 
            max-width: 98% !important; 
            padding: 1.5rem !important; 
            background-color: rgba(255, 255, 255, 0.96) !important; 
            border-radius: 16px;
            margin-top: 15px;
            box-shadow: 0 8px 32px rgba(0,0,0,0.15);
            transition: all 0.3s ease;
        }}
        
        /* Hide default Streamlit headers for clean UI */
        header[data-testid="stHeader"] {{ background-color: transparent !important; }}
        
        /* Top Navigation Buttons Fix (Dark mode safe, clear borders) */
        header[data-testid="stHeader"] button, 
        [data-testid="stToolbar"] button,
        [data-testid="collapsedControl"],
        button[kind="header"] {{
            background-color: #ffffff !important; 
            border-radius: 8px !important; 
            box-shadow: 0 4px 6px rgba(0,0,0,0.1) !important; 
            border: 1px solid #cbd5e1 !important; 
            opacity: 1 !important;
            visibility: visible !important;
            z-index: 99999 !important;
            color: #000000 !important;
        }}
        header[data-testid="stHeader"] button *, 
        [data-testid="stToolbar"] button *,
        [data-testid="collapsedControl"] *,
        button[kind="header"] * {{
            color: #000000 !important;
            fill: currentColor !important;
        }}
        
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
            color: #1e293b !important; 
        }}

        /* Universal Button Styling (Modern, Rounded, Hover Effects) */
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
        
        /* Primary Buttons (Start, Next, Submit) */
        div.stButton > button[kind="primary"] {{ 
            background: linear-gradient(135deg, #4f46e5 0%, #3b82f6 100%) !important; 
            border: none !important;
            border-radius: 10px !important; 
            box-shadow: 0 4px 15px rgba(79, 70, 229, 0.4) !important;
        }}
        div.stButton > button[kind="primary"]:hover {{
            box-shadow: 0 6px 20px rgba(79, 70, 229, 0.6) !important;
            transform: translateY(-2px);
        }}
        div.stButton > button[kind="primary"] p, 
        div.stButton > button[kind="primary"] span {{
            color: #ffffff !important;
        }}

        /* Secondary Warning/Pause Buttons */
        div.stButton > button[kind="secondary"] {{
            background-color: #fff1f2 !important;
            border-color: #fecdd3 !important;
            color: #be123c !important;
        }}
        div.stButton > button[kind="secondary"] * {{
            color: #be123c !important;
        }}
        
        /* Palette Specific Tuning */
        .palette-btn button {{
            padding: 0px !important;
            height: 42px !important;
            min-height: 42px !important;
        }}

        /* Hide the Auto-Pause Trigger Button Completely */
        .hidden-trigger-container {{
            display: none !important;
            opacity: 0 !important;
            height: 0 !important;
            width: 0 !important;
            overflow: hidden !important;
        }}

        /* Mobile Responsiveness & Adjustments */
        @media (max-width: 768px) {{
            .block-container {{ padding: 1rem 0.5rem !important; }}
            h3 {{ font-size: 1.4rem !important; }}
            h4 {{ font-size: 1.1rem !important; }}
            div.stButton > button {{ font-size: 14px !important; padding: 0.4rem !important; }}
        }}
        </style>
    """, unsafe_allow_html=True)

def inject_timer_and_autopause_js(remaining_sec, is_timer_active):
    """
    Injects the JS that runs the timer and tracks inactivity.
    If inactive for 5 mins (300 sec) or offline, it auto-pauses the exam.
    Also handles responsive sticky positioning for desktop.
    """
    ui_code = f'<div class="timer-box">⏳ <span id="time">{"00:00" if is_timer_active else "📝 No Time Limit"}</span></div>'
    
    js_timer_logic = ""
    if is_timer_active:
        js_timer_logic = f"""
        var countDownDate = new Date().getTime() + ({remaining_sec} * 1000);
        var x = setInterval(function() {{
            var now = new Date().getTime();
            var distance = countDownDate - now;
            if (distance <= 0) {{
                clearInterval(x); 
                document.getElementById("time").innerHTML = "TIME UP!";
                var btns = window.parent.document.querySelectorAll('button');
                for(var i=0; i<btns.length; i++) {{ 
                    if(btns[i].innerText.includes('Final Submit')) {{ btns[i].click(); break; }} 
                }}
            }} else {{
                var m = Math.floor((distance % (1000 * 60 * 60)) / (1000 * 60));
                var s = Math.floor((distance % (1000 * 60)) / 1000);
                m = m < 10 ? "0" + m : m; s = s < 10 ? "0" + s : s;
                document.getElementById("time").innerHTML = m + ":" + s;
            }}
        }}, 1000);
        """

    html_code = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ margin:0; padding:0; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }}
            .timer-box {{ 
                background: linear-gradient(135deg, #fee2e2 0%, #fecaca 100%); 
                border: 2px solid #ef4444; 
                color: #b91c1c !important; 
                padding: 12px 0; 
                border-radius: 12px; 
                font-size: 24px; 
                font-weight: 800; 
                text-align: center; 
                box-shadow: 0 4px 6px rgba(239, 68, 68, 0.2); 
                margin-bottom: 10px; 
                letter-spacing: 1px;
            }}
            .timer-box span {{ color: #b91c1c !important; }}
            .no-timer {{ background: linear-gradient(135deg, #e0f2fe 0%, #bae6fd 100%); border-color: #38bdf8; color: #0369a1 !important; }}
        </style>
    </head>
    <body>
        {ui_code}
        <script>
            // 1. Timer Logic
            {js_timer_logic}
            
            // 2. Auto-Pause (Inactivity Tracker) Logic
            let idleTime = 0;
            const maxIdle = 300; // 5 minutes (300 seconds)
            
            function resetIdle() {{ idleTime = 0; }}
            
            try {{
                window.parent.document.addEventListener('mousemove', resetIdle, true);
                window.parent.document.addEventListener('keypress', resetIdle, true);
                window.parent.document.addEventListener('touchstart', resetIdle, true);
                window.parent.document.addEventListener('scroll', resetIdle, true);
                window.parent.document.addEventListener('click', resetIdle, true);
            }} catch(e) {{}}
            
            var inactivityInterval = setInterval(function() {{
                idleTime++;
                if (idleTime >= maxIdle || !navigator.onLine) {{
                    clearInterval(inactivityInterval); // Stop checking once triggered
                    var btns = window.parent.document.querySelectorAll('button');
                    for(var i=0; i<btns.length; i++) {{ 
                        if(btns[i].innerText.includes('AutoPauseTrigger')) {{ 
                            btns[i].click(); 
                            break; 
                        }} 
                    }}
                }}
            }}, 1000);
            
            // 3. Responsive Sticky Panel Logic & Hide Trigger Button
            setTimeout(function() {{
                try {{
                    // Hide the AutoPauseTrigger button instantly
                    var btns = window.parent.document.querySelectorAll('button');
                    for(var i=0; i<btns.length; i++) {{
                        if(btns[i].innerText.includes('AutoPauseTrigger')) {{
                            var wrap = btns[i].closest('div[data-testid="stVerticalBlock"]');
                            if(wrap) wrap.style.display = 'none';
                        }}
                    }}

                    var frame = window.frameElement;
                    var col = frame.closest('div[data-testid="column"]');
                    if(!col) col = frame.parentElement.parentElement.parentElement;
                    
                    if (col) {{
                        // Apply Sticky ONLY on Desktop (Width > 768px)
                        if (window.innerWidth > 768) {{
                            col.style.position = '-webkit-sticky';
                            col.style.position = 'sticky';
                            col.style.top = '15px';
                            col.style.height = '88vh'; 
                            col.style.overflowY = 'auto'; 
                            col.style.borderLeft = '2px solid #e2e8f0';
                            col.style.paddingLeft = '15px';
                            col.style.paddingRight = '5px';
                        }}
                        
                        col.classList.add('my-palette');
                        
                        var main = window.parent.document.querySelector('section[data-testid="stMain"]');
                        if(main) main.style.overflow = 'visible';
                        var block = window.parent.document.querySelector('.block-container');
                        if(block) block.style.overflow = 'visible';
                        
                        if (!window.parent.document.getElementById('palette-css')) {{
                            var style = window.parent.document.createElement('style');
                            style.id = 'palette-css';
                            style.innerHTML = `
                                .my-palette::-webkit-scrollbar {{ width: 6px; }}
                                .my-palette::-webkit-scrollbar-thumb {{ background: #94a3b8; border-radius: 6px; }}
                                .my-palette div[data-testid="column"] {{ padding: 3px !important; }}
                            `;
                            window.parent.document.head.appendChild(style);
                        }}
                    }}
                }} catch(e) {{}}
            }}, 100);
        </script>
    </body>
    </html>
    """
    components.html(html_code, height=75)


# ==========================================
# 5. PAGE RENDERING FUNCTIONS
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
    """Renders the simplified workflow navigation sidebar."""
    try:
        st.sidebar.image("logo.png", use_container_width=True)
    except:
        st.sidebar.markdown("<h2 style='text-align: center; color: #4F46E5;'>🎓 Study Booster</h2>", unsafe_allow_html=True)

    st.sidebar.markdown(f"### 👤 {st.session_state.current_user}")
    st.sidebar.divider()
    
    # Workflow Navigation
    if st.sidebar.button("📚 Dashboard", use_container_width=True):
        st.session_state.active_page = "Dashboard"
        st.rerun()
        
    st.sidebar.divider()
    if st.sidebar.button("🚪 Logout", type="secondary", use_container_width=True):
        st.session_state.auth = False
        st.rerun()

def render_dashboard():
    """Renders the main dashboard for loading tests."""
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
                        
    # Display start button if a test is successfully loaded
    if st.session_state.quiz_ready:
        st.divider()
        st.success(f"✅ **{st.session_state.topic}** Loaded Successfully!")
        col_space1, col_start, col_space2 = st.columns([1, 2, 1])
        with col_start:
            if st.button("🚀 Start Live Test", type="primary", use_container_width=True):
                st.session_state.active_page = "Instructions"
                st.rerun()

def render_instructions():
    """Renders the instructions page before the exam."""
    st.markdown(f"<h1 style='color: #4F46E5; text-align: center;'>📜 Instructions</h1>", unsafe_allow_html=True)
    st.markdown(f"<h3 style='text-align: center; color: #475569;'>{st.session_state.topic}</h3>", unsafe_allow_html=True)
    st.divider()
    
    col1, col2, col3 = st.columns([1, 3, 1])
    with col2:
        with st.container(border=True):
            st.markdown("""
            ### Please read carefully before starting:
            """)
            st.markdown(f"🔹 **Total Questions:** {len(st.session_state.questions)}")
            st.markdown(f"🔹 **Time Limit:** {'No Time Limit' if st.session_state.timer_mode == 'No Timer' else f'{st.session_state.time_val} Minutes'}")
            st.markdown("""
            🔹 **Navigation:** You can jump to any question using the Question Palette on the right.
            🔹 **Auto-Pause:** If you become inactive for 5 minutes or lose internet, the exam will pause automatically.
            🔹 **Marking Scheme:** Every correct answer adds to your score. No negative marking.
            🔹 **Submission:** Exam submits automatically when timer hits zero.
            """)
            
            st.write("<br>", unsafe_allow_html=True)
            if st.button("✅ I have read the instructions. Begin Exam.", type="primary", use_container_width=True):
                st.session_state.exam_started = True
                st.session_state.is_paused = False
                if st.session_state.timer_mode == "Total Time (Minutes)":
                    st.session_state.end_time = time.time() + (st.session_state.time_val * 60)
                st.session_state.active_page = "Exam"
                st.rerun()

def render_paused_screen():
    """Renders the screen when the exam is manually or automatically paused."""
    st.write("<br><br>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        with st.container(border=True):
            st.markdown("<h1 style='text-align: center; color: #b91c1c;'>⏸ Exam Paused</h1>", unsafe_allow_html=True)
            st.markdown("<p style='text-align: center; color: #475569; font-size: 1.1rem;'>Your timer has been stopped and answers are safely saved.</p>", unsafe_allow_html=True)
            st.write("---")
            if st.button("▶️ Resume Test", type="primary", use_container_width=True):
                resume_exam()
                st.rerun()

def render_exam():
    """Renders the active examination layout."""
    
    # Catch Pause State First
    if st.session_state.is_paused:
        render_paused_screen()
        return

    # Hidden auto-pause trigger button wrapper
    st.markdown('<div class="hidden-trigger-container">', unsafe_allow_html=True)
    if st.button("AutoPauseTrigger", key="auto_pause_trigger_btn"):
        pause_exam()
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

    # Server-side timeout check
    if st.session_state.timer_mode == "Total Time (Minutes)":
        if (st.session_state.end_time - time.time()) <= 0:
            st.session_state.quiz_completed = True
            st.session_state.active_page = "Result"
            st.rerun()

    q_idx = st.session_state.current_q
    st.session_state.visited_questions.add(q_idx)
    total_q = len(st.session_state.questions)
    q_data = st.session_state.questions[q_idx]

    # Responsive Grid Layout: Left Panel (Question), Right Panel (Palette)
    col_main, col_pal = st.columns([7, 3]) 
    
    # ================== RIGHT PANEL (Timer + Palette) ==================
    with col_pal:
        is_timed = (st.session_state.timer_mode == "Total Time (Minutes)")
        rem_sec = int(st.session_state.end_time - time.time()) if is_timed else 0
        
        # Inject Timer and Autopause JS
        inject_timer_and_autopause_js(rem_sec, is_timed)
        
        st.markdown("<h4 style='text-align:center; margin-top:10px;'>Question Palette</h4>", unsafe_allow_html=True)
        st.markdown(
            "<p style='text-align:center; font-size:13px; font-weight:600; margin-bottom:15px; color:#475569;'>"
            "🔵 Curr &nbsp;|&nbsp; 🟢 Ans &nbsp;|&nbsp; 🔴 Skip &nbsp;|&nbsp; ⚪ Unvisit"
            "</p>", unsafe_allow_html=True
        )
        
        # Render Palette Grid
        grid_cols = st.columns(5)
        for i in range(total_q):
            if i == q_idx: 
                icon = "🔵"
            elif st.session_state.user_answers.get(i) is not None: 
                icon = "🟢"
            elif i in st.session_state.visited_questions: 
                icon = "🔴"
            else: 
                icon = "⚪"
                
            with grid_cols[i % 5]:
                # Add CSS class helper for tight palette styling
                st.markdown("<div class='palette-btn'>", unsafe_allow_html=True)
                if st.button(f"{icon}\n{i+1}", key=f"pal_{i}"):
                    st.session_state.current_q = i
                    st.rerun()
                st.markdown("</div>", unsafe_allow_html=True)

    # ================== LEFT PANEL (Main Question Area) ==================
    with col_main:
        st.markdown(f"<h2 style='color:#4F46E5 !important; margin-top:0;'>{st.session_state.topic}</h2>", unsafe_allow_html=True)
        st.write("---")
        
        st.markdown(f"<h3 style='line-height: 1.6;'>Q{q_idx + 1}. {q_data['q']}</h3>", unsafe_allow_html=True)
        
        # Determine pre-selected option safely
        saved_ans = st.session_state.user_answers.get(q_idx)
        try: 
            def_idx = q_data['options'].index(saved_ans)
        except ValueError: 
            def_idx = None
        
        # Radio buttons for options
        clear_key = st.session_state.get(f"clear_{q_idx}", 0)
        choice = st.radio(
            "Options:", 
            q_data['options'], 
            index=def_idx, 
            key=f"rad_{q_idx}_{clear_key}", 
            label_visibility="collapsed"
        )
        if choice: 
            st.session_state.user_answers[q_idx] = choice
            
        st.write("<br><br>", unsafe_allow_html=True)
        
        # Bottom Navigation Control Panel
        b_col1, b_col2, b_col3, b_col4, b_col5 = st.columns([2, 2, 2, 2, 2])
        
        with b_col1:
            if st.button("⏪ Previous", use_container_width=True):
                if q_idx > 0: 
                    st.session_state.current_q -= 1
                st.rerun()
                
        with b_col2:
            if st.button("🧹 Clear", use_container_width=True):
                st.session_state.user_answers.pop(q_idx, None)
                st.session_state[f"clear_{q_idx}"] = clear_key + 1
                st.rerun()
                
        with b_col3:
            is_last = (q_idx == total_q - 1)
            btn_txt = "Finish" if is_last else "Next ⏩"
            if st.button(btn_txt, type="primary" if not is_last else "secondary", use_container_width=True):
                if not is_last:
                    st.session_state.current_q += 1
                    st.rerun()
                    
        with b_col4:
            if st.button("⏸ Pause", type="secondary", use_container_width=True):
                pause_exam()
                st.rerun()
                
        with b_col5:
            if st.button("🚀 Final Submit", type="primary", use_container_width=True):
                st.session_state.quiz_completed = True
                st.session_state.active_page = "Result"
                st.rerun()


def render_result():
    """Renders the detailed post-exam result analysis."""
    # Reset layout restrictions from the active exam
    components.html("""
    <script>
    try{
      let p=window.parent.document;
      p.querySelectorAll('.my-palette').forEach(e=>{
        e.style.position='static';
        e.style.height='auto';
        e.style.overflowY='visible';
        e.style.borderLeft='none';
      });
      let m=p.querySelector('section[data-testid="stMain"]');
      if(m){m.style.overflow='auto';}
      let b=p.querySelector('.block-container');
      if(b){b.style.overflow='visible';}
    }catch(e){}
    </script>
    """, height=0)
    
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
        correct_ans = q['options'][q['ans']]
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
# 6. MAIN APPLICATION LOOP
# ==========================================
def main():
    init_session()
    inject_custom_css()
    
    if not st.session_state.auth:
        render_login()
    else:
        render_sidebar()
        
        # Linear Application Workflow Router
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
