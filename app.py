import streamlit as st
import streamlit.components.v1 as components
import csv
import os
import time
import base64
import re
import json
import pickle

# ==========================================
# 1. CONFIGURATION & CONSTANTS
# ==========================================
st.set_page_config(
    page_title="Study Booster | Pro CBT Platform", 
    page_icon="🎓", 
    layout="wide", 
    initial_sidebar_state="collapsed"
)

# Feature 4: Restructure Question Bank Management (Basic & Advanced)
CSV_FOLDER = 'saved_csvs'
ADVANCED_CSV_FOLDER = 'advanced_csvs'

if not os.path.exists(CSV_FOLDER): 
    os.makedirs(CSV_FOLDER)

if not os.path.exists(ADVANCED_CSV_FOLDER):
    os.makedirs(ADVANCED_CSV_FOLDER)

# Initialize Session Folder for Persistence
SESSION_FOLDER = 'active_sessions'
if not os.path.exists(SESSION_FOLDER):
    os.makedirs(SESSION_FOLDER)

# Initialize Default Folder Structure for both banks
DEFAULT_STRUCTURE = {
    "Science": ["Physics", "Chemistry", "Biology", "Environment"],
    "Arts": ["History", "Polity", "Geography", "Economics"],
    "Statistics": [],
    "Current affairs": []
}

for base_folder in [CSV_FOLDER, ADVANCED_CSV_FOLDER]:
    for root_cat, sub_cats in DEFAULT_STRUCTURE.items():
        root_path = os.path.join(base_folder, root_cat)
        os.makedirs(root_path, exist_ok=True)
        for sub_cat in sub_cats:
            os.makedirs(os.path.join(root_path, sub_cat), exist_ok=True)

ATTEMPTS_FILE = 'attempts_data.json'
TIMERS_FILE = 'timers_data.json'
USERS_FILE = 'users_data.json'
HISTORY_FILE = 'history_data.json'
NEG_MARK_FILE = 'negative_marking_data.json'

# Existing Authentication mapping - Migrated to JSON for Persistence
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

def get_all_users():
    if not os.path.exists(USERS_FILE):
        with open(USERS_FILE, 'w') as f:
            json.dump(ALLOWED_USERS, f, indent=4)
        return ALLOWED_USERS
    with open(USERS_FILE, 'r') as f:
        try:
            return json.load(f)
        except:
            return ALLOWED_USERS

def save_users(users):
    with open(USERS_FILE, 'w') as f:
        json.dump(users, f, indent=4)

def load_history():
    if not os.path.exists(HISTORY_FILE):
        return {}
    with open(HISTORY_FILE, 'r') as f:
        try:
            return json.load(f)
        except:
            return {}

def save_history(data):
    with open(HISTORY_FILE, 'w') as f:
        json.dump(data, f, indent=4)

def load_neg_mark():
    if not os.path.exists(NEG_MARK_FILE):
        return {}
    with open(NEG_MARK_FILE, 'r') as f:
        try:
            return json.load(f)
        except:
            return {}

def save_neg_mark(data):
    with open(NEG_MARK_FILE, 'w') as f:
        json.dump(data, f, indent=4)

def get_neg_mark(test_key):
    return load_neg_mark().get(test_key, 0.0)

def set_neg_mark(test_key, value):
    data = load_neg_mark()
    data[test_key] = value
    save_neg_mark(data)

def get_all_csv_files(base_dir=CSV_FOLDER):
    """Recursively fetches all CSV files across folders and subfolders."""
    csv_files = []
    for root, dirs, files in os.walk(base_dir):
        for f in files:
            if f.endswith('.csv'):
                rel_path = os.path.relpath(os.path.join(root, f), base_dir)
                csv_files.append(rel_path.replace(os.sep, '/'))
    return sorted(csv_files)

def nav_admin_up():
    curr = st.session_state.admin_current_path
    if curr:
        parts = curr.split('/')
        st.session_state.admin_current_path = '/'.join(parts[:-1])

def nav_admin_down(folder):
    curr = st.session_state.admin_current_path
    if curr:
        st.session_state.admin_current_path = curr + '/' + folder
    else:
        st.session_state.admin_current_path = folder

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

def record_detailed_attempt(user, test_key, original_file):
    """Saves detailed breakdown of user progress for Feature 2"""
    history = load_history()
    if user not in history: 
        history[user] = []
        
    correct, incorrect, unanswered, negative, final_score = calculate_detailed_score(test_key)
    total_q = len(st.session_state.questions)
    
    q_details = []
    for i, q in enumerate(st.session_state.questions):
        is_match = (q.get('type') == 'match')
        user_ans = st.session_state.user_answers.get(i)
        
        q_num = i + 1
        raw_q = q['q']
        clean_q = re.sub(r'^[Qq]?(?:uestion)?\s*\d+[\.\)]\s*', '', raw_q)
        
        if user_ans is None or (is_match and not user_ans):
            status = "Unanswered"
            marks = 0
            neg = 0
            u_ans_str = "None"
            c_ans_str = str(q['ans']) if is_match else str(q['options'][q['ans']] if 0 <= q['ans'] < len(q['options']) else "N/A")
        else:
            if is_match:
                correct_ans = q['ans']
                c_ans_str = str(correct_ans)
                u_ans_str = str(user_ans)
                if isinstance(user_ans, dict) and user_ans == correct_ans:
                    status = "Correct"
                    marks = 1
                    neg = 0
                else:
                    status = "Incorrect"
                    marks = 0
                    neg = get_neg_mark(test_key)
            else:
                correct_ans = q['options'][q['ans']] if 0 <= q['ans'] < len(q['options']) else None
                c_ans_str = str(correct_ans)
                u_ans_str = str(user_ans)
                if user_ans == correct_ans:
                    status = "Correct"
                    marks = 1
                    neg = 0
                else:
                    status = "Incorrect"
                    marks = 0
                    neg = get_neg_mark(test_key)
                    
        q_details.append({
            "q_num": q_num,
            "question": clean_q,
            "user_ans": u_ans_str,
            "correct_ans": c_ans_str,
            "status": status,
            "marks": marks,
            "negative": neg
        })
        
    attempt_data = {
        "test_name": os.path.basename(original_file).replace('.csv', '').replace('_', ' '),
        "subject": st.session_state.topic,
        "folder": os.path.dirname(original_file) or 'Root',
        "attempt_number": get_attempt_data(user, test_key)['used'],
        "datetime": time.strftime("%Y-%m-%d %H:%M:%S"),
        "total_questions": total_q,
        "attempted": total_q - unanswered,
        "correct": correct,
        "incorrect": incorrect,
        "unanswered": unanswered,
        "marks_obtained": correct,
        "negative_marks": negative,
        "final_score": final_score,
        "percentage": round((final_score / total_q) * 100, 2) if total_q > 0 else 0,
        "q_details": q_details
    }
    history[user].append(attempt_data)
    save_history(history)

def record_attempt_usage():
    """Securely increments the attempt count once per active test session upon completion."""
    if not st.session_state.get('attempt_recorded', False):
        user = st.session_state.get('current_user')
        test_key = st.session_state.get('current_test_filename')
        if user and test_key:
            original_file = test_key.replace("ADVANCED|", "")
            increment_attempt(user, test_key)
            record_detailed_attempt(user, test_key, original_file)
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
    """Initialize all session state variables safely with refresh persistence support."""
    default_state = {
        'auth': False, 
        'current_user': "", 
        'questions': [], 
        'current_q': 0,
        'user_answers': {}, 
        'visited_questions': set(), 
        'marked_questions': set(),
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
        'attempt_recorded': False,
        'admin_current_path': "",
        'sid': "",
        'current_bank': "Basic",
        'last_admin_bank': "Basic"
    }

    query_params = st.query_params
    sid = query_params.get("sid", None)
    
    if sid and not st.session_state.get('auth', False):
        session_path = os.path.join(SESSION_FOLDER, f"{sid}.pkl")
        if os.path.exists(session_path):
            try:
                with open(session_path, "rb") as f:
                    saved_state = pickle.load(f)
                for k, v in saved_state.items():
                    if k in default_state:
                        st.session_state[k] = v
                return 
            except Exception:
                pass 
                
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

    if st.session_state.timer_mode == "Total Time (Minutes)":
        st.session_state.remaining_seconds -= elapsed
        if st.session_state.remaining_seconds <= 0:
            st.session_state.remaining_seconds = 0
            st.session_state.active_page = "Result"
            record_attempt_usage()
            st.rerun()

    inactive_duration = now - st.session_state.get('last_interaction_time', now)
    if inactive_duration > 300:
        st.session_state.is_paused = True
        if st.session_state.timer_mode == "Total Time (Minutes)":
            st.session_state.remaining_seconds += (inactive_duration - 300)
        st.session_state.last_interaction_time = now
        st.rerun()

def record_activity():
    """Callback wrapper applied to buttons/inputs to record user activity."""
    now = time.time()
    
    if not st.session_state.is_paused:
        elapsed = now - st.session_state.last_calc_time
        if st.session_state.timer_mode == "Total Time (Minutes)":
            st.session_state.remaining_seconds -= elapsed
    
    st.session_state.last_calc_time = now
    
    inactive_duration = now - st.session_state.last_interaction_time
    if inactive_duration > 300 and not st.session_state.is_paused:
        st.session_state.is_paused = True
        if st.session_state.timer_mode == "Total Time (Minutes)":
            st.session_state.remaining_seconds += (inactive_duration - 300)
        st.session_state.last_interaction_time = now
    else:
        st.session_state.last_interaction_time = now

# ==========================================
# 4. EXAM CONTROL & LOGIC FUNCTIONS
# ==========================================
def load_quiz(file_name):
    """Parses CSV correctly, supports both MCQ and Match the Following automatically (100% crash-proof)."""
    st.session_state.questions = []
    
    # Restructure Check
    bank = st.session_state.get('current_bank', 'Basic')
    base_dir = CSV_FOLDER if bank == 'Basic' else ADVANCED_CSV_FOLDER
    file_path = os.path.join(base_dir, file_name.replace('/', os.sep))
    
    test_key = file_name if bank == 'Basic' else f"ADVANCED|{file_name}"
    
    with open(file_path, 'r', encoding='utf-8-sig', errors='ignore') as f:
        reader = csv.DictReader(f)
        for row in reader:
            raw_type = row.get('Type')
            q_type = str(raw_type).strip().lower() if raw_type else ''
            
            # Feature: Match the Following Parser
            if q_type == 'match':
                left_items = []
                right_items = []
                for i in range(1, 11): # Dynamic Support for 2 to 10 pairs
                    l_val = row.get(f'Left{i}')
                    r_val = row.get(f'Right{i}')
                    
                    l_str = str(l_val).strip() if l_val else ''
                    r_str = str(r_val).strip() if r_val else ''
                    
                    if l_str and r_str:
                        left_items.append(l_str)
                        right_items.append(r_str)
                
                if left_items:
                    q_text = row.get('Question')
                    q_text_str = str(q_text).strip() if q_text else ''
                    st.session_state.questions.append({
                        'type': 'match',
                        'q': q_text_str,
                        'left': left_items,
                        'right': right_items,
                        'options': sorted(right_items), # Shuffle right items for dropdowns
                        'ans': {l: r for l, r in zip(left_items, right_items)} # Correct pairings dict
                    })
            
            # Existing Feature: Standard MCQ Parser
            else:
                opts = []
                for i in range(1, 6):
                    col_name = f'Option{i}'
                    val = row.get(col_name)
                    # Safe checking for None to avoid AttributeError
                    if val and str(val).strip():
                        opts.append(str(val).strip())
                
                q_text = row.get('Question')
                q_text_str = str(q_text).strip() if q_text else ''
                
                ans_val = row.get('Answer')
                ans_str = str(ans_val).strip() if ans_val else ''
                
                st.session_state.questions.append({
                    'type': 'mcq',
                    'q': q_text_str, 
                    'options': opts, 
                    'ans': int(ans_str) - 1 if ans_str.isdigit() else -1
                })
            
    timers_data = load_timers_data()
    t_config = timers_data.get(test_key, {"mode": "Total Time", "value": 30})
    
    if t_config["mode"] == "No Timer":
        t_mode = "No Timer"
        t_val = 0
        rem_sec = 0
    elif t_config["mode"] == "Per Question":
        t_mode = "Total Time (Minutes)" 
        total_seconds = len(st.session_state.questions) * t_config["value"]
        t_val = round(total_seconds / 60, 2)
        rem_sec = total_seconds
    else: 
        t_mode = "Total Time (Minutes)"
        t_val = t_config["value"]
        rem_sec = t_val * 60
            
    st.session_state.topic = os.path.basename(file_name).replace('.csv', '').replace("_", " ")
    st.session_state.quiz_ready = True
    st.session_state.current_q = 0
    st.session_state.user_answers = {}
    st.session_state.visited_questions = {0}
    st.session_state.marked_questions = set() 
    st.session_state.timer_mode = t_mode
    st.session_state.time_val = t_val
    st.session_state.remaining_seconds = rem_sec
    st.session_state.is_paused = False
    
    st.session_state.current_test_filename = test_key
    st.session_state.attempt_recorded = False

def calculate_score():
    """Preserved for strict backward compatibility."""
    score = 0
    for i, q in enumerate(st.session_state.questions):
        if q.get('type') == 'match':
            user_ans = st.session_state.user_answers.get(i, {})
            correct_ans = q['ans']
            if isinstance(user_ans, dict) and user_ans == correct_ans:
                score += 1
        else:
            correct_ans = q['options'][q['ans']] if 0 <= q['ans'] < len(q['options']) else None
            if st.session_state.user_answers.get(i) == correct_ans:
                score += 1
    return score

def calculate_detailed_score(test_key):
    """Calculates detailed score metrics including Feature 3: Negative Marking."""
    score = 0
    incorrect = 0
    unanswered = 0
    neg_mark_value = get_neg_mark(test_key)

    for i, q in enumerate(st.session_state.questions):
        is_match = (q.get('type') == 'match')
        user_ans = st.session_state.user_answers.get(i)

        if user_ans is None or (is_match and not user_ans):
            unanswered += 1
        else:
            if is_match:
                correct_ans = q['ans']
                if isinstance(user_ans, dict) and user_ans == correct_ans:
                    score += 1
                else:
                    incorrect += 1
            else:
                correct_ans = q['options'][q['ans']] if 0 <= q['ans'] < len(q['options']) else None
                if user_ans == correct_ans:
                    score += 1
                else:
                    incorrect += 1

    negative_marks = incorrect * neg_mark_value
    final_score = score - negative_marks
    return score, incorrect, unanswered, negative_marks, final_score

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
        
        if q_idx < len(st.session_state.questions):
            q_data = st.session_state.questions[q_idx]
            if q_data.get('type') == 'match':
                for l in q_data.get('left', []):
                    w_key = f"match_{q_idx}_{l}"
                    if w_key in st.session_state:
                        st.session_state[w_key] = "-- Select --"
            else:
                if f"radio_ans_{q_idx}" in st.session_state:
                    st.session_state[f"radio_ans_{q_idx}"] = None

def toggle_mark(q_idx):
    record_activity()
    if not st.session_state.is_paused:
        if q_idx in st.session_state.marked_questions:
            st.session_state.marked_questions.remove(q_idx)
        else:
            st.session_state.marked_questions.add(q_idx)

def on_radio_change(q_idx):
    record_activity()
    if not st.session_state.is_paused:
        selected = st.session_state.get(f"radio_ans_{q_idx}")
        if selected is not None:
            st.session_state.user_answers[q_idx] = selected
        else:
            st.session_state.user_answers.pop(q_idx, None)

def on_match_change(q_idx, left_items):
    """Callback safely storing match combinations."""
    record_activity()
    if not st.session_state.is_paused:
        current_match = {}
        for l in left_items:
            val = st.session_state.get(f"match_{q_idx}_{l}")
            if val and val != "-- Select --":
                current_match[l] = val
        
        if current_match:
            st.session_state.user_answers[q_idx] = current_match
        else:
            st.session_state.user_answers.pop(q_idx, None)

# ==========================================
# 5. CSS & JAVASCRIPT INJECTION
# ==========================================
def inject_custom_css():
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
        
        .block-container {{ 
            max-width: 98% !important; 
            padding: 1.5rem !important; 
            background-color: rgba(255, 255, 255, 0.98) !important; 
            border-radius: 16px;
            margin-top: 15px;
            box-shadow: 0 8px 32px rgba(0,0,0,0.15);
            transition: all 0.3s ease;
        }}
        
        header[data-testid="stHeader"] {{ background-color: transparent !important; }}
        
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

        div.stButton > button[kind="secondary"] {{
            background-color: #fff1f2 !important;
            border-color: #fecdd3 !important;
            color: #be123c !important;
        }}
        div.stButton > button[kind="secondary"] * {{
            color: #be123c !important;
        }}
        </style>
    """, unsafe_allow_html=True)

def render_visual_timer():
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
    users = get_all_users()
    
    st.write("<br><br><br>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 1.5, 1]) 
    with col2:
        with st.container():
            st.markdown("<h1 style='text-align: center; color:#4F46E5 !important; font-weight: 800;'>🎓 Study Booster</h1>", unsafe_allow_html=True)
            st.markdown("<p style='text-align: center; font-size: 1.1rem; color: #64748b !important;'>Sign in to access your dashboard</p>", unsafe_allow_html=True)
            st.divider()
            
            username = st.selectbox("👤 Select Profile", ["-- Select User --"] + list(users.keys()))
            pwd = st.text_input("🔑 Enter Passcode", type="password")
            
            st.write("")
            if st.button("Secure Login 🚀", type="primary", use_container_width=True):
                if username != "-- Select User --" and users.get(username) == pwd:
                    st.session_state.auth = True
                    st.session_state.current_user = username
                    st.session_state.active_page = "Dashboard"
                    
                    new_sid = base64.urlsafe_b64encode(os.urandom(12)).decode()
                    st.session_state.sid = new_sid
                    st.query_params["sid"] = new_sid
                    
                    st.rerun()
                else:
                    st.error("❌ Invalid Credentials! Please try again.")

def render_sidebar():
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
        if st.session_state.get("sid"):
            session_path = os.path.join(SESSION_FOLDER, f"{st.session_state.sid}.pkl")
            if os.path.exists(session_path):
                try: os.remove(session_path)
                except Exception: pass
        
        if "sid" in st.query_params:
            del st.query_params["sid"]
            
        for key in list(st.session_state.keys()):
            del st.session_state[key]
            
        st.rerun()

def render_dashboard():
    st.markdown("<h1 style='color: #1e293b;'>Welcome to Study Booster! 🚀</h1>", unsafe_allow_html=True)
    st.markdown("<p style='font-size: 1.1rem; color: #475569;'>Select a test series below to begin.</p>", unsafe_allow_html=True)
    st.write("---")
    
    if "Admin" in st.session_state.current_user:
        # Feature 4: Basic and Advanced banks isolated routing
        with st.expander("📁 Admin Panel: Question Bank Management", expanded=False):
            admin_bank = st.radio("Select Question Bank", ["Basic", "Advanced"], horizontal=True, key="admin_bank_radio")
            if st.session_state.get('last_admin_bank') != admin_bank:
                st.session_state.admin_current_path = ""
                st.session_state.last_admin_bank = admin_bank
            
            active_admin_base = CSV_FOLDER if admin_bank == "Basic" else ADVANCED_CSV_FOLDER
            current_admin_path = st.session_state.get('admin_current_path', '')
            full_admin_path = os.path.join(active_admin_base, current_admin_path.replace('/', os.sep))
            
            st.markdown(f"**Current Folder ({admin_bank}):** `Question Bank / {current_admin_path.replace('/', ' / ')}`")
            
            c_up, c_newf, c_upld = st.columns(3)
            with c_up:
                if current_admin_path != '':
                    st.button("⬅️ Back / Up", on_click=nav_admin_up, use_container_width=True)
            with c_newf:
                new_f = st.text_input("New Folder", key="new_f_input", label_visibility="collapsed", placeholder="Folder Name")
                if st.button("Create Folder", use_container_width=True):
                    if new_f:
                        os.makedirs(os.path.join(full_admin_path, new_f), exist_ok=True)
                        st.rerun()
            with c_upld:
                uploaded_file = st.file_uploader("Upload CSV", type=['csv'], label_visibility="collapsed")
                if uploaded_file:
                    save_path = os.path.join(full_admin_path, uploaded_file.name)
                    with open(save_path, "wb") as f:
                        f.write(uploaded_file.getbuffer())
                    st.success("Uploaded!")
                    time.sleep(1)
                    st.rerun()
                    
            st.write("---")
            
            items = sorted(os.listdir(full_admin_path)) if os.path.exists(full_admin_path) else []
            folders = [f for f in items if os.path.isdir(os.path.join(full_admin_path, f))]
            files = [f for f in items if f.endswith('.csv')]
            
            st.markdown("#### Folders")
            if not folders: st.info("No subfolders.")
            for folder in folders:
                fc1, fc2 = st.columns([8, 2])
                fc1.button(f"📁 {folder}", key=f"nav_{current_admin_path}_{folder}", on_click=nav_admin_down, args=(folder,), use_container_width=True)
                if current_admin_path == "" and folder in ["Arts", "Computer", "Current affairs", "Science", "Statistics"]:
                    fc2.markdown("<div style='padding-top:10px; color:#94a3b8; font-size:12px; font-weight:bold;'>System Folder</div>", unsafe_allow_html=True)
                else:
                    if fc2.button("🗑️ Delete", key=f"del_f_{current_admin_path}_{folder}", use_container_width=True):
                        try:
                            os.rmdir(os.path.join(full_admin_path, folder))
                            st.rerun()
                        except OSError:
                            st.error("Folder not empty! Delete files inside first.")
                            
            st.write("---")
            st.markdown("#### Files")
            if not files: st.info("No files in this folder.")
            
            all_folders = []
            for root, dirs, _ in os.walk(active_admin_base):
                for d in dirs:
                    rel = os.path.relpath(os.path.join(root, d), active_admin_base).replace(os.sep, '/')
                    all_folders.append(rel)
            all_folders.insert(0, "Root")
            
            for f_name in files:
                file_p = os.path.join(full_admin_path, f_name)
                f_size = os.path.getsize(file_p) / 1024
                
                c1, c2, c3, c4 = st.columns([4, 2, 3, 2])
                c1.markdown(f"📄 **{f_name}**")
                c2.markdown(f"{f_size:.1f} KB")
                
                move_target = c3.selectbox("Move to", ["-- Select --"] + all_folders, key=f"mov_{current_admin_path}_{f_name}", label_visibility="collapsed")
                if move_target != "-- Select --":
                    tgt = active_admin_base if move_target == "Root" else os.path.join(active_admin_base, move_target.replace('/', os.sep))
                    os.rename(file_p, os.path.join(tgt, f_name))
                    st.rerun()
                    
                if c4.button("🗑️ Delete", key=f"del_{current_admin_path}_{f_name}", use_container_width=True):
                    os.remove(file_p)
                    st.rerun()

        # Combine options for all Administrative forms to allow unified settings for both Banks
        all_basic = get_all_csv_files(CSV_FOLDER)
        all_adv = get_all_csv_files(ADVANCED_CSV_FOLDER)
        admin_file_options = {}
        for f in all_basic: admin_file_options[f"Basic | {f}"] = f
        for f in all_adv: admin_file_options[f"Advanced | {f}"] = f"ADVANCED|{f}"

        with st.expander("⏱️ Admin Panel: Timer Management", expanded=False):
            st.markdown("Configure timer rules for each test individually.")
            if admin_file_options:
                sel_display = st.selectbox("Select Test to Configure Timer", list(admin_file_options.keys()), key="tmr_test")
                t_file = admin_file_options[sel_display]
                
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
                        new_val = 0 
                    
                    if st.button("Save Timer Settings", type="primary"):
                        timers_data[t_file] = {"mode": new_mode, "value": new_val}
                        save_timers_data(timers_data)
                        st.success(f"✅ Timer settings saved for {sel_display}!")
            else:
                st.info("No tests available to configure.")

        with st.expander("⚙️ Admin Panel: Attempt Management", expanded=False):
            st.markdown("Select a user and a test to modify attempt limits.")
            a_col1, a_col2 = st.columns(2)
            users = get_all_users()
            with a_col1:
                sel_user = st.selectbox("Select User", list(users.keys()), key="adm_user")
            with a_col2:
                if admin_file_options:
                    sel_test_display = st.selectbox("Select Test", list(admin_file_options.keys()), key="adm_test")
                    sel_test = admin_file_options[sel_test_display]
                else:
                    sel_test = None
            
            if sel_user and sel_test:
                curr_data = get_attempt_data(sel_user, sel_test)
                new_limit = st.number_input("Allowed Attempts", min_value=1, value=curr_data['allowed'], key="adm_limit")
                if st.button("Update Limit", type="primary", key="btn_update_limit"):
                    set_allowed_attempts(sel_user, sel_test, new_limit)
                    st.success(f"✅ Updated! {sel_user.split()[0]} now has {new_limit} allowed attempts for {sel_test_display}.")

        # Feature 3: Negative Marking Configuration
        with st.expander("⚖️ Admin Panel: Negative Marking Configuration", expanded=False):
            st.markdown("Set negative marking (Range 0.00 to 0.33) deducted for incorrect answers.")
            if admin_file_options:
                sel_display_nm = st.selectbox("Select Test for Negative Marking", list(admin_file_options.keys()), key="nm_sel_test")
                nm_test_key = admin_file_options[sel_display_nm]
                
                curr_val = get_neg_mark(nm_test_key)
                new_val = st.number_input("Negative Marks per Incorrect Answer", min_value=0.0, max_value=0.33, value=float(curr_val), step=0.01)
                
                if st.button("Save Negative Marking", type="primary"):
                    set_neg_mark(nm_test_key, new_val)
                    st.success(f"✅ Negative marking updated to {new_val} for {sel_display_nm}!")
            else:
                st.info("No tests available to configure.")

        # Feature 1: Complete User Management Panel
        with st.expander("👥 Admin Panel: User Management", expanded=False):
            users = get_all_users()
            um_tabs = st.tabs(["Add User", "Remove User", "Change Password"])
            
            with um_tabs[0]:
                new_u = st.text_input("New Username (Format: Name (Role))")
                new_p = st.text_input("Password", type="password")
                if st.button("Add User", type="primary"):
                    if new_u in users:
                        st.error("Username already exists!")
                    elif new_u and new_p:
                        users[new_u] = new_p
                        save_users(users)
                        st.success(f"Added user: {new_u}")
                        st.rerun()
                        
            with um_tabs[1]:
                del_u = st.selectbox("Select User to Remove", [u for u in users if "Admin" not in u])
                confirm_del = st.checkbox(f"I confirm I want to permanently delete {del_u}")
                if st.button("Delete User", type="primary"):
                    if confirm_del and del_u:
                        del users[del_u]
                        save_users(users)
                        st.success("User deleted!")
                        st.rerun()
                    elif not confirm_del:
                        st.warning("Please confirm deletion.")
                        
            with um_tabs[2]:
                ch_u = st.selectbox("Select User", list(users.keys()), key="ch_u")
                ch_p = st.text_input("New Password", type="password", key="ch_p")
                if st.button("Change Password", type="primary"):
                    if ch_p:
                        users[ch_u] = ch_p
                        save_users(users)
                        st.success("Password updated immediately!")

        # Feature 2: User Progress Report Dashboard
        with st.expander("📊 Admin Panel: User Progress Report", expanded=False):
            users = get_all_users()
            rep_u = st.selectbox("Select User for Report", list(users.keys()))
            if rep_u:
                history = load_history().get(rep_u, [])
                if not history:
                    st.info(f"No attempt history found for {rep_u}.")
                else:
                    total_tests = len(set(h['test_name'] for h in history))
                    total_attempts = len(history)
                    scores = [h['final_score'] for h in history]
                    percentages = [h['percentage'] for h in history]
                    avg_score = sum(scores) / len(scores) if scores else 0
                    avg_perc = sum(percentages) / len(percentages) if percentages else 0
                    high_score = max(scores) if scores else 0
                    low_score = min(scores) if scores else 0
                    last_attempt = history[-1]['datetime'] if history else "N/A"
                    
                    st.markdown("#### Overall Summary")
                    c1, c2, c3, c4 = st.columns(4)
                    c1.metric("Total Tests", total_tests)
                    c2.metric("Total Attempts", total_attempts)
                    c3.metric("Highest Score", f"{high_score:.2f}")
                    c4.metric("Lowest Score", f"{low_score:.2f}")
                    
                    c5, c6, c7, c8 = st.columns(4)
                    c5.metric("Avg Score", f"{avg_score:.2f}")
                    c6.metric("Avg Percentage", f"{avg_perc:.2f}%")
                    c7.metric("Last Attempt", last_attempt)
                    
                    st.write("---")
                    st.markdown("#### Attempt History")
                    for att in reversed(history):
                        result_status = "Pass" if att['percentage'] >= 33 else "Fail"
                        with st.expander(f"Attempt {att['attempt_number']} - {att['test_name']} ({att['datetime']}) | Score: {att['final_score']:.2f} | {result_status}"):
                            st.write(f"**Subject:** {att['subject']} | **Folder:** {att['folder']}")
                            st.write(f"**Total Qs:** {att['total_questions']} | **Attempted:** {att['attempted']} | **Correct:** {att['correct']} | **Incorrect:** {att['incorrect']} | **Unanswered:** {att['unanswered']}")
                            st.write(f"**Marks Obtained:** {att['marks_obtained']} | **Negative Marks:** {att['negative_marks']:.2f} | **Final Score:** {att['final_score']:.2f} | **Percentage:** {att['percentage']}%")
                            
                            st.markdown("##### Detailed Question Report")
                            for qd in att['q_details']:
                                st.markdown(f"**Q{qd['q_num']}. {qd['question']}**")
                                c_a, c_b, c_c = st.columns(3)
                                c_a.write(f"**Selected:** {qd['user_ans']}")
                                c_b.write(f"**Correct:** {qd['correct_ans']}")
                                status_color = "green" if qd['status'] == "Correct" else "red" if qd['status'] == "Incorrect" else "orange"
                                c_c.markdown(f"**Status:** <span style='color:{status_color}'>{qd['status']}</span>", unsafe_allow_html=True)
                                st.write(f"**Marks:** {qd['marks']} | **Negative:** {qd['negative']:.2f}")
                                st.write("---")

    col_space1, col_tests, col_space2 = st.columns([1, 4, 1])
    
    with col_tests:
        col_tests_head1, col_tests_head2 = st.columns([1, 1])
        with col_tests_head1:
            st.markdown("### 📋 Available Test Series")
        with col_tests_head2:
            st.session_state.current_bank = st.radio("Question Bank", ["Basic", "Advanced"], horizontal=True, label_visibility="collapsed")
        
        active_user_base = CSV_FOLDER if st.session_state.current_bank == "Basic" else ADVANCED_CSV_FOLDER
        
        search_query = st.text_input("🔍 Search Test, Subject, or Folder...", "").strip()
        
        all_files = get_all_csv_files(active_user_base)
        files_to_display = []
        
        if search_query:
            files_to_display = [f for f in all_files if search_query.lower() in f.lower()]
        else:
            cat_col1, cat_col2 = st.columns(2)
            root_folders = sorted([d for d in os.listdir(active_user_base) if os.path.isdir(os.path.join(active_user_base, d))])
            
            with cat_col1:
                sel_cat = st.selectbox("Category", root_folders) if root_folders else None
            
            if sel_cat:
                cat_path = os.path.join(active_user_base, sel_cat)
                sub_folders = sorted([d for d in os.listdir(cat_path) if os.path.isdir(os.path.join(cat_path, d))])
                with cat_col2:
                    if sub_folders:
                        sel_sub = st.selectbox("Subcategory", ["All"] + sub_folders)
                    else:
                        sel_sub = "All"
                        
                filter_prefix = sel_cat if sel_sub == "All" else f"{sel_cat}/{sel_sub}"
                
                files_to_display = [f for f in all_files if f.startswith(filter_prefix)]
        
        if not files_to_display: 
            st.info("No tests found matching your criteria.")
        else:
            with st.container(border=True):
                for file in files_to_display:
                    user = st.session_state.current_user
                    test_key = file if st.session_state.current_bank == "Basic" else f"ADVANCED|{file}"
                    
                    attempt_data = get_attempt_data(user, test_key)
                    allowed = attempt_data['allowed']
                    used = attempt_data['used']
                    remaining = allowed - used

                    base_name = os.path.basename(file).replace('.csv', '').replace('_', ' ')
                    folder_context = os.path.dirname(file) or 'Root'

                    c1, c2 = st.columns([3, 1])
                    c1.markdown(f"<h5 style='margin-top: 10px; margin-bottom: 2px;'>📄 {base_name}</h5>", unsafe_allow_html=True)
                    c1.markdown(f"<p style='font-size: 0.8rem; color: #94a3b8; margin-top: 0; margin-bottom: 2px;'>📂 {folder_context.replace('/', ' / ')}</p>", unsafe_allow_html=True)
                    
                    c1.markdown(f"<p style='font-size: 0.85rem; color: #64748b; margin-top: 0;'>Attempts: {used} / {allowed} &nbsp;|&nbsp; Remaining: {remaining}</p>", unsafe_allow_html=True)
                    
                    if remaining > 0:
                        if c2.button("Load Test", key=f"load_{test_key}"):
                            load_quiz(file)
                    else:
                        c2.button("Limit Reached", key=f"limit_{test_key}", disabled=True, help="You have reached the maximum number of attempts allowed for this test. Please contact the administrator.")
                        
    if st.session_state.quiz_ready:
        st.divider()
        st.success(f"✅ **{st.session_state.topic}** is loaded and ready.")
        col_space1, col_start, col_space2 = st.columns([1, 2, 1])
        with col_start:
            if st.button("🚀 Proceed to Instructions", type="primary", use_container_width=True):
                st.session_state.active_page = "Instructions"
                st.rerun()

def render_instructions():
    st.markdown(f"<h1 style='color: #4F46E5; text-align: center;'>📜 Instructions</h1>", unsafe_allow_html=True)
    st.markdown(f"<h3 style='text-align: center; color: #475569;'>{st.session_state.topic}</h3>", unsafe_allow_html=True)
    st.divider()
    
    col1, col2, col3 = st.columns([1, 3, 1])
    with col2:
        with st.container(border=True):
            st.markdown("### Please read carefully before starting:")
            st.markdown(f"🔹 **Total Questions:** {len(st.session_state.questions)}")
            
            time_display_str = "No Time Limit"
            if st.session_state.timer_mode != "No Timer":
                time_display_str = f"{st.session_state.time_val} Minutes"

            st.markdown(f"🔹 **Time Limit:** {time_display_str}")
            
            neg_mark_display = get_neg_mark(st.session_state.current_test_filename)
            if neg_mark_display > 0:
                st.markdown(f"🔹 **Negative Marking:** -{neg_mark_display} for every incorrect answer.")
            
            st.markdown("""
            🔹 **Navigation:** You can jump to any question using the Question Palette on the right.
            🔹 **Auto-Pause:** If you become completely inactive for **5 minutes**, the exam will pause itself to save your time safely.
            🔹 **Marking Scheme:** Every correct answer adds to your score.
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
    if st.session_state.is_paused:
        render_paused_screen()
        return

    q_idx = st.session_state.current_q
    st.session_state.visited_questions.add(q_idx)
    total_q = len(st.session_state.questions)
    q_data = st.session_state.questions[q_idx]

    # STANDARD LAYOUT CSS
    st.markdown("""
    <style>
    div[data-testid="column"]:nth-of-type(2) {
        background-color: #f0f8ff !important;
        border: 1px solid #bfdbfe !important;
        border-radius: 8px !important;
        padding-bottom: 15px !important;
        overflow: hidden; 
    }
    div[data-testid="column"]:nth-of-type(2) > div[data-testid="stVerticalBlock"] > div[data-testid="stHorizontalBlock"] div.stButton > button {
        background-color: #dbeafe !important;
        color: #1e40af !important;
        border: none !important;
        font-size: 13px !important;
        border-radius: 4px !important;
    }
    div[data-testid="column"]:nth-of-type(2) > div[data-testid="stVerticalBlock"] > div:last-child div.stButton > button {
        background-color: #0ea5e9 !important;
        color: white !important;
        border: none !important;
        font-size: 14px !important;
        border-radius: 4px !important;
        margin-top: 5px !important;
    }
    </style>
    """, unsafe_allow_html=True)

    col_main, col_pal = st.columns([7, 3]) 
    
    ans_count = 0
    ans_marked_count = 0
    marked_count = 0
    not_ans_count = 0
    not_visit_count = 0
    
    for i in range(total_q):
        is_ans = st.session_state.user_answers.get(i) is not None
        is_vis = i in st.session_state.visited_questions
        is_mark = i in st.session_state.marked_questions
        
        if is_ans and is_mark:
            ans_marked_count += 1
        elif is_ans and not is_mark:
            ans_count += 1
        elif not is_ans and is_mark:
            marked_count += 1
        elif not is_ans and is_vis and not is_mark:
            not_ans_count += 1
        else:
            not_visit_count += 1
            
    # ================== RIGHT PANEL ==================
    with col_pal:
        render_visual_timer()
        st.button("⏸ Pause", type="secondary", on_click=pause_exam, use_container_width=True, key="btn_pause_top")
        
        username_display = st.session_state.current_user.split()[0]
        avatar_letter = username_display[0].upper() if username_display else "U"
        
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
<div style="width: 18px; height: 18px; background-color: #2bc765; color: white; border-radius: 50% 50% 0 0; display: flex; align-items: center; justify-content: center; font-weight: bold; font-size: 10px;">{ans_count}</div>
<span>Answered</span>
</div>
<div style="display: flex; align-items: center; gap: 4px;">
<div style="width: 18px; height: 18px; background-color: #9d48b1; color: white; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-weight: bold; font-size: 10px;">{marked_count}</div>
<span>Marked</span>
</div>
<div style="display: flex; align-items: center; gap: 4px;">
<div style="width: 18px; height: 18px; background-color: #ffffff; border: 1px solid #cbd5e1; color: #333; border-radius: 4px; display: flex; align-items: center; justify-content: center; font-weight: bold; font-size: 10px;">{not_visit_count}</div>
<span>Not Visited</span>
</div>
<div style="display: flex; align-items: center; gap: 4px; grid-column: span 2;">
<div style="width: 18px; height: 18px; background-color: #9d48b1; color: white; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-weight: bold; font-size: 10px; position: relative; overflow: visible;">{ans_marked_count}<div style="position: absolute; bottom: -2px; right: -2px; width: 8px; height: 8px; background-color: #2bc765; border-radius: 50%; border: 1px solid white;"></div></div>
<span>Marked and answered</span>
</div>
<div style="display: flex; align-items: center; gap: 4px;">
<div style="width: 18px; height: 18px; background-color: #e55a45; color: white; border-radius: 0 0 50% 50%; display: flex; align-items: center; justify-content: center; font-weight: bold; font-size: 10px;">{not_ans_count}</div>
<span>Not Answered</span>
</div>
</div>
</div>
"""
        st.markdown(html_legend, unsafe_allow_html=True)
        
        st.markdown(
            f"""<div style='background-color:#dbeafe; padding:8px 15px; font-weight:700; color:#1e3a8a; font-size:12px; text-transform: uppercase; margin: 0 -1.5rem 10px -1.5rem; border-bottom: 1px solid #bfdbfe;'>
            SECTION : {st.session_state.topic}
            </div>""", 
            unsafe_allow_html=True
        )

        with st.expander("System Engine", expanded=False):
            st.markdown("<div id='hidden-engine-marker'></div>", unsafe_allow_html=True)
            for i in range(total_q):
                st.button(f"HBTN_{i}", key=f"hbtn_{i}", on_click=nav_goto, args=(i,))

        grid_html = ""
        for i in range(total_q):
            is_ans = st.session_state.user_answers.get(i) is not None
            is_vis = i in st.session_state.visited_questions
            is_mark = i in st.session_state.marked_questions
            is_curr = (i == q_idx)
            
            classes = ["q-btn"]
            if is_ans and is_mark:
                classes.append("answeredmarked")
            elif is_ans:
                classes.append("answered")
            elif is_mark:
                classes.append("marked")
            elif is_vis:
                classes.append("notanswered")
            else:
                classes.append("notvisited")
                
            if is_curr:
                classes.append("current")
                
            grid_html += f'<div class="{" ".join(classes)}" data-idx="{i}">{i+1}</div>\n'
            
        full_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
        <style>
        body {{ margin: 0; padding: 0; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: transparent; }}
        .palette-grid {{
            display: grid;
            grid-template-columns: repeat(5, 1fr);
            gap: 8px;
            padding: 5px;
        }}
        .q-btn {{
            aspect-ratio: 1 / 1;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 13px;
            font-weight: 600;
            cursor: pointer;
            border-radius: 4px;
            border: 1px solid #cbd5e1;
            user-select: none;
            transition: transform 0.1s ease;
        }}
        .q-btn:hover {{ transform: scale(1.05); }}
        .notvisited {{ background: #ffffff; color: #000000; border-color: #cbd5e1; }}
        .notanswered {{ background: #e55a45; color: #ffffff; border-color: #e55a45; border-radius: 0 0 15px 15px; }}
        .answered {{ background: #2bc765; color: #ffffff; border-color: #2bc765; border-radius: 15px 15px 0 0; }}
        .marked {{ background: #9d48b1; color: #ffffff; border-color: #9d48b1; border-radius: 50%; }}
        .answeredmarked {{ background: #9d48b1; color: #ffffff; border-color: #9d48b1; border-radius: 50%; position: relative; overflow: visible; }}
        .answeredmarked::after {{
            content: ''; position: absolute; bottom: -2px; right: -2px; width: 8px; height: 8px;
            background-color: #2bc765; border-radius: 50%; border: 1px solid white; z-index: 3;
        }}
        .current {{ outline: 3px solid #2563eb; outline-offset: 2px; transform: scale(1.05); z-index: 2; }}
        </style>
        </head>
        <body>
        <div class="palette-grid">
            {grid_html}
        </div>
        
        <script>
            function mapAndHide() {{
                try {{
                    const parentDoc = window.parent.document;
                    
                    const marker = parentDoc.getElementById('hidden-engine-marker');
                    if (marker) {{
                        const details = marker.closest('details'); 
                        if (details) details.style.display = 'none';
                        const expDiv = marker.closest('div[data-testid="stExpander"]');
                        if (expDiv) expDiv.style.display = 'none';
                    }}

                    const stButtons = parentDoc.querySelectorAll('button');
                    stButtons.forEach(b => {{
                        if (b.innerText && b.innerText.includes('HBTN_')) {{
                            let idx = b.innerText.split('_')[1].trim(); 
                            window.hiddenMap[idx] = b;
                        }}
                    }});
                }} catch (e) {{
                    console.error("Iframe bridging blocked:", e);
                }}
            }}

            window.hiddenMap = {{}};

            document.addEventListener("DOMContentLoaded", function() {{
                mapAndHide();
                setTimeout(mapAndHide, 50);
                setTimeout(mapAndHide, 200);

                const gridItems = document.querySelectorAll('.q-btn');
                gridItems.forEach(item => {{
                    item.addEventListener('click', function() {{
                        let idx = this.getAttribute('data-idx');
                        if(window.hiddenMap[idx]) {{
                            window.hiddenMap[idx].click();
                        }} else {{
                            mapAndHide();
                            if(window.hiddenMap[idx]) window.hiddenMap[idx].click();
                        }}
                    }});
                }});
            }});
        </script>
        </body>
        </html>
        """
        
        components.html(full_html, height=350, scrolling=True)

        st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)
        b1, b2 = st.columns(2)
        with b1:
            st.button("Question Paper", use_container_width=True, key="btn_qp")
        with b2:
            st.button("Instructions", use_container_width=True, key="btn_inst")
            
        st.button("🚀 Final Submit", type="primary", use_container_width=True, key="btn_sub_right", on_click=nav_submit)

    # ================== LEFT PANEL ==================
    with col_main:
        st.markdown(f"<h2 style='color:#4F46E5 !important; margin-top:0;'>{st.session_state.topic}</h2>", unsafe_allow_html=True)
        st.write("---")
        
        raw_q = q_data['q']
        clean_q = re.sub(r'^[Qq]?(?:uestion)?\s*\d+[\.\)]\s*', '', raw_q)
        
        st.markdown(f"<div style='font-size: 1.3rem; font-weight: 600; line-height: 1.6; color: #1e293b; margin-bottom: 15px;'>Q{q_idx + 1}. {clean_q}</div>", unsafe_allow_html=True)
        
        # --- FEATURE: DYNAMIC QUESTION TYPE RENDERING ---
        if q_data.get('type') == 'match':
            saved_ans = st.session_state.user_answers.get(q_idx, {})
            
            m_col1, m_col2 = st.columns([1, 1])
            m_col1.markdown("<div style='color: #475569; font-weight: 700; margin-bottom: 10px;'>Column A (Fixed)</div>", unsafe_allow_html=True)
            m_col2.markdown("<div style='color: #475569; font-weight: 700; margin-bottom: 10px;'>Column B (Select Match)</div>", unsafe_allow_html=True)
            
            for l_item in q_data['left']:
                r_c1, r_c2 = st.columns([1, 1])
                r_c1.markdown(f"<div style='padding-top: 8px; font-weight: 500; font-size: 1.1rem;'>{l_item}</div>", unsafe_allow_html=True)
                
                w_key = f"match_{q_idx}_{l_item}"
                options = ["-- Select --"] + q_data['options']
                current_val = saved_ans.get(l_item, "-- Select --")
                try:
                    idx = options.index(current_val)
                except ValueError:
                    idx = 0
                
                r_c2.selectbox("Match", options, index=idx, key=w_key, on_change=on_match_change, args=(q_idx, q_data['left']), label_visibility="collapsed")
                
        else: # Standard MCQ fallback
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
        
        b_col1, b_col2, b_col3, b_col4 = st.columns([1.5, 1.5, 2.5, 1.5])
        
        with b_col1:
            st.button("⏪ Previous", on_click=nav_prev, use_container_width=True)
                
        with b_col2:
            st.button("🧹 Clear", on_click=clear_answer, args=(q_idx,), use_container_width=True)
            
        with b_col3:
            is_cur_marked = q_idx in st.session_state.marked_questions
            st.button("🚩 Unmark" if is_cur_marked else "🚩 Mark for Review", on_click=toggle_mark, args=(q_idx,), use_container_width=True)
                
        with b_col4:
            is_last = (q_idx == total_q - 1)
            if not is_last:
                st.button("Next ⏩", type="primary", on_click=nav_next, use_container_width=True)
            else:
                st.button("Finish", type="secondary", disabled=True, use_container_width=True)

def render_result():
    total_q = len(st.session_state.questions)
    test_key = st.session_state.current_test_filename
    
    correct, incorrect, unanswered, negative, final_score = calculate_detailed_score(test_key)
    attempted = total_q - unanswered
    
    st.markdown("<h1 style='color: #4F46E5; text-align: center;'>🏆 Performance Analysis</h1>", unsafe_allow_html=True)
    st.divider()
    
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.info(f"### 📝 Attempted\n# {attempted} / {total_q}")
    with c2:
        st.success(f"### ✅ Correct\n# {correct} / {total_q}")
    with c3:
        st.error(f"### ⛔ Penalty\n# -{negative:.2f}")
    with c4:
        accuracy = round((correct / attempted * 100) if attempted > 0 else 0, 1)
        st.warning(f"### 🎯 Final Score\n# {final_score:.2f}")
        
    st.write("<br><br>", unsafe_allow_html=True)
    st.markdown("### 📋 Detailed Answer Key")
    st.write("---")
    
    for i, q in enumerate(st.session_state.questions):
        st.markdown(f"**Q{i+1}: {q['q']}**")
        
        # --- FEATURE: DYNAMIC RESULT RENDERING ---
        if q.get('type') == 'match':
            user_ans = st.session_state.user_answers.get(i, {})
            correct_ans = q['ans']
            
            if user_ans == correct_ans: 
                st.success("**Your Answer:** Fully Correct ✅")
                for l, r in correct_ans.items():
                    st.write(f"- **{l}** ➔ {r}")
            elif not user_ans: 
                st.warning("**Not Attempted.**")
                st.info("**Correct Answer Matching:**")
                for l, r in correct_ans.items():
                    st.write(f"- **{l}** ➔ {r}")
            else: 
                st.error("**Your Answer:** Incorrect ❌")
                st.markdown("*Your Mapping:*")
                for l in q['left']:
                    u_r = user_ans.get(l, "Not Selected")
                    st.write(f"- **{l}** ➔ {u_r}")
                    
                st.info("**Correct Answer Matching:**")
                for l, r in correct_ans.items():
                    st.write(f"- **{l}** ➔ {r}")
        else:
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
    
    passive_time_check()
    
    inject_custom_css()
    
    if not st.session_state.auth:
        render_login()
    else:
        render_sidebar()
        
        if st.session_state.active_page == "Dashboard":
            render_dashboard()
        elif st.session_state.active_page == "Instructions":
            render_instructions()
        elif st.session_state.active_page == "Exam":
            render_exam()
        elif st.session_state.active_page == "Result":
            render_result()

    if st.session_state.get("auth") and st.session_state.get("sid"):
        try:
            session_path = os.path.join(SESSION_FOLDER, f"{st.session_state.sid}.pkl")
            
            safe_keys = [
                'auth', 'current_user', 'questions', 'current_q', 'user_answers', 
                'visited_questions', 'marked_questions', 'quiz_ready', 'topic', 
                'timer_mode', 'time_val', 'remaining_seconds', 'last_calc_time', 
                'last_interaction_time', 'active_page', 'is_paused', 
                'current_test_filename', 'attempt_recorded', 'admin_current_path', 'sid',
                'current_bank', 'last_admin_bank'
            ]
            
            safe_state = {k: st.session_state[k] for k in safe_keys if k in st.session_state}
            
            with open(session_path, "wb") as f:
                pickle.dump(safe_state, f)
        except Exception:
            pass

if __name__ == "__main__":
    main()
