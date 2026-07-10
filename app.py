import streamlit as st
import streamlit.components.v1 as components
import csv
import os
import time
import base64
import re
import json
import pickle
import uuid

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
QUERIES_FILE = 'queries_data.json'  # Added for Ask Query Feature

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

def load_queries():
    if not os.path.exists(QUERIES_FILE):
        return []
    with open(QUERIES_FILE, 'r') as f:
        try:
            return json.load(f)
        except:
            return []

def save_queries(data):
    with open(QUERIES_FILE, 'w') as f:
        json.dump(data, f, indent=4)

@st.cache_data(ttl=2)
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
        'last_admin_bank': "Basic",
        'query_input': ""
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
    with st.spinner(f"Loading {os.path.basename(file_name)} environment..."):
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
UI_COLORS = {
    "primary": "#4F46E5",
    "primary_dark": "#4338ca",
    "ink": "#0f172a",
    "muted": "#64748b",
    "surface": "#ffffff",
    "surface_subtle": "#f8fafc",
    "border": "#e2e8f0",
    "success": "#16a34a",
    "warning": "#d97706",
    "danger": "#dc2626",
}

def render_page_header(title, subtitle=None, eyebrow=None):
    """Render a consistent, presentation-only page header."""
    eyebrow_html = f"<p class='page-eyebrow'>{eyebrow}</p>" if eyebrow else ""
    subtitle_html = f"<p class='page-subtitle'>{subtitle}</p>" if subtitle else ""
    st.markdown(
        f"""
        <section class="page-header">
            {eyebrow_html}
            <h1>{title}</h1>
            {subtitle_html}
        </section>
        """,
        unsafe_allow_html=True,
    )

def render_metric_card(label, value, accent="blue", helper_text=None):
    """Render a reusable result or reporting metric without changing its value."""
    helper_html = f"<p>{helper_text}</p>" if helper_text else ""
    st.markdown(
        f"""
        <div class="metric-card metric-{accent}">
            <span>{label}</span>
            <strong>{value}</strong>
            {helper_html}
        </div>
        """,
        unsafe_allow_html=True,
    )

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
        bg_css = ".stApp { background-color: #f1f5f9; }"

    st.markdown(f"""
        <style>
        {bg_css}

        :root {{
            --sb-primary: {UI_COLORS['primary']};
            --sb-primary-dark: {UI_COLORS['primary_dark']};
            --sb-ink: {UI_COLORS['ink']};
            --sb-muted: {UI_COLORS['muted']};
            --sb-surface: {UI_COLORS['surface']};
            --sb-surface-subtle: {UI_COLORS['surface_subtle']};
            --sb-border: {UI_COLORS['border']};
            --sb-success: {UI_COLORS['success']};
            --sb-warning: {UI_COLORS['warning']};
            --sb-danger: {UI_COLORS['danger']};
        }}

        html {{ font-size: 16px; font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif; }}
        .stApp {{
            color: var(--sb-ink);
            background-color: #f1f5f9;
            color-scheme: light;
        }}
        header[data-testid="stHeader"] {{ background: transparent !important; }}
        .block-container {{
            max-width: 1380px !important;
            padding: clamp(1rem, 2vw, 2.5rem) !important;
            margin: 1.5rem auto !important;
            min-height: calc(100vh - 4rem);
            border: 1px solid rgba(226, 232, 240, 0.95);
            border-radius: 24px;
            background: rgba(255, 255, 255, 0.98) !important;
            box-shadow: 0 20px 50px -12px rgba(15, 23, 42, 0.1);
        }}
        
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
            color: var(--sb-ink) !important;
        }}

        .active-sidebar-btn {{
            background: #eff6ff !important;
            color: #2563eb !important;
            border-left: 4px solid #2563eb !important;
            border-radius: 0 10px 10px 0 !important;
        }}

        /* Shared page structure */
        .page-header {{
            margin: 0 0 2rem;
            padding: 1.75rem 2rem;
            border: 1px solid rgba(226, 232, 240, 0.8);
            border-radius: 16px;
            background: linear-gradient(135deg, #ffffff 0%, #f8fafc 100%);
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -1px rgba(0, 0, 0, 0.03);
        }}
        .page-header h1 {{
            margin: 0 !important;
            color: var(--sb-ink) !important;
            font-size: clamp(1.75rem, 3.5vw, 2.5rem) !important;
            letter-spacing: -0.025em;
            line-height: 1.2;
            font-weight: 800;
        }}
        .page-eyebrow {{
            margin: 0 0 0.5rem !important;
            color: var(--sb-primary) !important;
            font-size: 0.85rem;
            font-weight: 700;
            letter-spacing: 0.1em;
            text-transform: uppercase;
        }}
        .page-subtitle {{
            margin: 0.5rem 0 0 !important;
            color: var(--sb-muted) !important;
            font-size: 1.05rem;
            line-height: 1.5;
        }}
        
        /* Dashboard & Exam Cards */
        .test-card-title {{ margin: 0; font-size: 1.15rem; font-weight: 700; color: #1e293b; line-height: 1.3; }}
        .test-card-folder {{ font-size: 0.85rem; color: #64748b; font-weight: 500; margin: 4px 0 8px 0; display:flex; align-items:center; gap: 4px; }}
        .test-card-stats {{ font-size: 0.85rem; color: #475569; background: #f1f5f9; padding: 4px 10px; border-radius: 6px; display: inline-block; font-weight: 600; border: 1px solid #e2e8f0; }}
        
        .metric-card {{
            min-height: 130px;
            padding: 1.25rem 1.5rem;
            border: 1px solid var(--sb-border);
            border-top: 4px solid var(--metric-accent, var(--sb-primary));
            border-radius: 16px;
            background: var(--sb-surface);
            box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.05);
            transition: transform 0.2s ease, box-shadow 0.2s ease;
        }}
        .metric-card:hover {{ transform: translateY(-4px); box-shadow: 0 12px 20px -5px rgba(0, 0, 0, 0.08); }}
        .metric-card span {{ display: block; color: #64748b !important; font-size: 0.8rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; }}
        .metric-card strong {{ display: block; margin-top: 0.4rem; color: #0f172a; font-size: clamp(1.4rem, 2vw, 1.8rem); font-weight: 800; }}
        .metric-card p {{ margin: 0.5rem 0 0 !important; color: #64748b !important; font-size: 0.85rem; }}
        
        .metric-blue {{ --metric-accent: #3b82f6; }}
        .metric-green {{ --metric-accent: #10b981; }}
        .metric-red {{ --metric-accent: #ef4444; }}
        .metric-amber {{ --metric-accent: #f59e0b; }}
        .metric-purple {{ --metric-accent: #8b5cf6; }}
        
        /* Motivational Banner */
        .motivational-banner {{
            background: linear-gradient(135deg, #eef2ff 0%, #f3e8ff 100%);
            border: 1px solid #c7d2fe;
            border-radius: 16px;
            padding: 2rem 1.5rem;
            text-align: center;
            box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.05);
            margin-bottom: 2rem;
            animation: fadeIn 0.8s ease-out;
        }}
        .motivational-banner h2 {{
            color: #4338ca !important;
            font-size: clamp(1.4rem, 3vw, 1.8rem) !important;
            font-weight: 800;
            margin-bottom: 1rem !important;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 10px;
        }}
        .motivational-banner p {{
            color: #475569 !important;
            font-size: 1.1rem;
            font-weight: 600;
            margin: 0.4rem 0 !important;
            line-height: 1.5;
        }}
        .motivational-banner .highlight-text {{
            color: #3730a3 !important;
            font-weight: 700;
            margin-top: 1.2rem !important;
            font-size: 1.15rem;
        }}
        .motivational-banner .emojis {{
            font-size: 1.8rem;
            margin-top: 1rem;
            display: inline-block;
            animation: floatEmoji 3s ease-in-out infinite;
        }}
        @keyframes fadeIn {{
            from {{ opacity: 0; transform: translateY(10px); }}
            to {{ opacity: 1; transform: translateY(0); }}
        }}
        @keyframes floatEmoji {{
            0% {{ transform: translateY(0px); }}
            50% {{ transform: translateY(-8px); }}
            100% {{ transform: translateY(0px); }}
        }}
        
        .exam-kicker {{ margin: 0 0 0.5rem; color: var(--sb-primary) !important; font-size: 0.85rem; font-weight: 700; letter-spacing: 0.08em; text-transform: uppercase; }}
        .exam-title {{ margin: 0 0 1rem; color: var(--sb-ink) !important; font-size: clamp(1.5rem, 2.5vw, 2rem); font-weight: 800; letter-spacing: -0.025em; }}
        
        .question-card {{ margin: 1rem 0 1.5rem; padding: 1.75rem; border: 1px solid #e2e8f0; border-radius: 16px; background: #ffffff; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05); }}
        .question-card__number {{ display: inline-flex; align-items: center; min-height: 30px; padding: 0 0.8rem; border-radius: 99px; background: #eff6ff; color: #1d4ed8 !important; font-size: 0.85rem; font-weight: 700; letter-spacing: 0.03em; border: 1px solid #bfdbfe; }}
        .question-card__text {{ margin: 1rem 0 0 !important; color: var(--sb-ink) !important; font-size: clamp(1.1rem, 1.8vw, 1.3rem); font-weight: 600; line-height: 1.7; }}
        
        /* Badges for Queries */
        .status-badge {{ padding: 4px 10px; border-radius: 99px; font-size: 0.75rem; font-weight: 700; text-transform: uppercase; display: inline-block; }}
        .badge-pending {{ background: #fef3c7; color: #b45309; border: 1px solid #fde68a; }}
        .badge-resolved {{ background: #dcfce7; color: #15803d; border: 1px solid #bbf7d0; }}
        
        /* Controls, forms and feedback */
        div.stButton > button {{
            min-height: 2.8rem !important;
            padding: 0.5rem 1.2rem !important;
            border: 1px solid #cbd5e1 !important;
            border-radius: 12px !important;
            background: #ffffff !important;
            color: var(--sb-ink) !important;
            font-size: 0.95rem !important;
            font-weight: 600 !important;
            transition: all 0.2s ease !important;
        }}
        div.stButton > button:hover:not(:disabled) {{
            border-color: #93c5fd !important;
            background: #f8fafc !important;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05) !important;
            transform: translateY(-1px);
        }}
        div.stButton > button:disabled {{ opacity: 0.6 !important; cursor: not-allowed !important; }}
        
        div.stButton > button[kind="primary"] {{
            border-color: var(--sb-primary) !important;
            background: var(--sb-primary) !important;
            color: #ffffff !important;
            box-shadow: 0 4px 6px -1px rgba(37, 99, 235, 0.2) !important;
        }}
        div.stButton > button[kind="primary"] * {{ color: #ffffff !important; }}
        div.stButton > button[kind="primary"]:hover:not(:disabled) {{ 
            background: var(--sb-primary-dark) !important;
            box-shadow: 0 10px 15px -3px rgba(37, 99, 235, 0.3) !important; 
        }}
        
        div[data-baseweb="input"] > div,
        div[data-baseweb="select"] > div,
        div[data-baseweb="textarea"] > div {{ border-radius: 12px !important; border-color: #cbd5e1 !important; background-color: #f8fafc !important; }}
        
        div[data-testid="stExpander"] {{ border: 1px solid var(--sb-border) !important; border-radius: 16px !important; background: #ffffff !important; overflow: hidden; box-shadow: 0 1px 3px 0 rgba(0,0,0,0.05); }}
        div[data-testid="stExpander"] details summary {{ padding: 0.5rem 0.25rem; font-weight: 700; color: #1e293b; font-size: 1.05rem; }}
        div[data-testid="stDivider"] {{ margin: 1.5rem 0 !important; border-color: #e2e8f0; }}

        /* Option cards keep native radio behavior while making choices easier to scan. */
        div[data-testid="stRadio"] [role="radiogroup"] {{ gap: 0.75rem; }}
        div[data-testid="stRadio"] label {{
            align-items: center !important;
            min-height: 3.5rem;
            padding: 0.75rem 1.25rem !important;
            border: 1px solid #cbd5e1;
            border-radius: 12px;
            background: #ffffff;
            transition: all 0.2s ease;
            box-shadow: 0 1px 2px 0 rgba(0,0,0,0.02);
            font-size: 1.05rem;
        }}
        div[data-testid="stRadio"] label:hover {{ border-color: #93c5fd; background: #f8fafc; transform: translateX(3px); box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05); }}
        div[data-testid="stRadio"] label:has(input:checked) {{ 
            border-color: var(--sb-primary); 
            background: #eff6ff; 
            box-shadow: 0 0 0 1.5px var(--sb-primary); 
        }}

        /* Navigation */
        section[data-testid="stSidebar"] {{ background: #0f172a !important; border-right: 1px solid #1e293b; }}
        section[data-testid="stSidebar"] * {{ color: #e2e8f0 !important; }}
        section[data-testid="stSidebar"] div.stButton > button,
        section[data-testid="stSidebar"] div.stButton > button * {{ background: transparent !important; border-color: transparent !important; color: #cbd5e1 !important; text-align: left !important; box-shadow: none !important; font-size: 1.05rem !important; padding: 0.75rem !important; }}
        section[data-testid="stSidebar"] div.stButton > button:hover:not(:disabled),
        section[data-testid="stSidebar"] div.stButton > button:hover:not(:disabled) * {{ background: rgba(51, 65, 85, 0.5) !important; color: #ffffff !important; transform: none; border-radius: 8px !important; }}
        section[data-testid="stSidebar"] [data-testid="stSidebarContent"] {{ padding-top: 1.5rem; }}
        
        .sidebar-brand {{ margin: 0.5rem 0 1.5rem; padding: 1rem; border-radius: 12px; background: linear-gradient(135deg, rgba(37, 99, 235, 0.4), rgba(79, 70, 229, 0.2)); border: 1px solid rgba(147, 197, 253, 0.2); }}
        .sidebar-brand strong {{ display: block; color: #ffffff !important; font-size: 1.2rem; letter-spacing: -0.02em; font-weight: 800; }}
        .sidebar-brand span {{ color: #bfdbfe !important; font-size: 0.8rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em; }}
        
        .nav-current {{ margin: 0.5rem 0 1.5rem; padding: 0.75rem 1rem; border-radius: 8px; background: rgba(59, 130, 246, 0.2); border: 1px solid rgba(96, 165, 250, 0.3); color: #bfdbfe !important; font-size: 0.85rem; font-weight: 600; display: flex; align-items: center; gap: 8px; }}

        /* Container specific overrides */
        [data-testid="stContainer"] {{ border-radius: 16px; border-color: #e2e8f0; }}
        
        @media (max-width: 768px) {{
            .block-container {{ padding: 1rem !important; border-radius: 0; border: none; margin: 0 !important; }}
            .page-header {{ padding: 1.25rem; border-radius: 12px; }}
            div[data-testid="stHorizontalBlock"] {{ flex-wrap: wrap !important; gap: 1rem !important; }}
            div[data-testid="stHorizontalBlock"] > div[data-testid="column"] {{ flex: 1 1 100% !important; width: 100% !important; min-width: 0 !important; }}
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
            body {{ margin:0; padding:0; font-family: Inter, -apple-system, sans-serif; background: transparent; }}
            .timer-box {{
                box-sizing: border-box;
                min-height: 60px;
                padding: 12px;
                border: 2px solid #fecaca;
                border-radius: 14px;
                background: linear-gradient(135deg, #fff5f5 0%, #fff1f2 100%);
                color: #e11d48;
                font-size: 24px;
                font-weight: 800;
                text-align: center;
                box-shadow: 0 4px 6px -1px rgba(225, 29, 72, 0.1);
                letter-spacing: 0.05em;
                display: flex;
                align-items: center;
                justify-content: center;
                gap: 8px;
            }}
            .no-timer {{
                background: linear-gradient(135deg, #f0f9ff 0%, #e0f2fe 100%);
                border-color: #bae6fd;
                color: #0284c7;
                font-size: 18px;
                letter-spacing: 0;
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
                display.innerHTML = "Practice Mode - No Time Limit";
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
    components.html(html_code, height=85)

# ==========================================
# 6. PAGE RENDERING FUNCTIONS
# ==========================================

def render_login():
    users = get_all_users()
    
    st.write("<br><br>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 1.5, 1]) 
    with col2:
        with st.container(border=True):
            st.markdown("<h1 style='text-align: center; color:#1e293b !important; font-weight:800; margin-bottom:0.5rem;'>Study Booster</h1>", unsafe_allow_html=True)
            st.markdown("<p style='text-align:center; font-size:1.1rem; color:#64748b !important; margin-top:0;'>Your focused space for practice, progress, and performance.</p>", unsafe_allow_html=True)
            st.divider()
            
            username = st.selectbox("👤 Select Profile", ["-- Select User --"] + list(users.keys()))
            pwd = st.text_input("🔑 Enter Passcode", type="password")
            
            st.write("<br>", unsafe_allow_html=True)
            if st.button("Secure Login 🚀", type="primary", use_container_width=True):
                if username != "-- Select User --" and users.get(username) == pwd:
                    with st.spinner("Authenticating secure session..."):
                        time.sleep(0.5)  # Smooth transition effect
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
        st.sidebar.markdown("<div class='sidebar-brand'><strong>Study Booster</strong><span>EdTech Platform</span></div>", unsafe_allow_html=True)

    st.sidebar.markdown(f"### 👤 {st.session_state.current_user}")
    st.sidebar.markdown(
        f"<div class='nav-current'>🟢 Workspace &middot; {st.session_state.active_page}</div>",
        unsafe_allow_html=True,
    )
    st.sidebar.divider()
    
    if st.sidebar.button("📚 Dashboard", use_container_width=True):
        st.session_state.active_page = "Dashboard"
        st.rerun()
        
    if "Admin" in st.session_state.current_user:
        if st.sidebar.button("⚙️ Admin Control Panel", use_container_width=True):
            with st.spinner("Loading Admin Modules..."):
                st.session_state.active_page = "Admin"
                st.rerun()
        if st.sidebar.button("💬 User Queries", use_container_width=True):
            with st.spinner("Fetching queries..."):
                st.session_state.active_page = "UserQueries"
                st.rerun()
                
    st.sidebar.divider()
    if st.sidebar.button("🚪 Logout", type="secondary", use_container_width=True):
        with st.spinner("Logging out safely..."):
            if st.session_state.get("sid"):
                session_path = os.path.join(SESSION_FOLDER, f"{st.session_state.sid}.pkl")
                if os.path.exists(session_path):
                    try: os.remove(session_path)
                    except Exception: pass
            
            if "sid" in st.query_params:
                del st.query_params["sid"]
                
            for key in list(st.session_state.keys()):
                del st.session_state[key]
                
            time.sleep(0.5)
            st.rerun()

def render_user_queries():
    if "Admin" not in st.session_state.current_user:
        st.error("Unauthorized access!")
        return
        
    render_page_header(
        "User Queries Management",
        "View and respond to student doubts and technical queries.",
        "Support Center",
    )
    
    queries = load_queries()
    
    col1, col2 = st.columns([2, 1])
    search_u = col1.text_input("🔍 Search by Username", placeholder="Type username...", key="admin_search_query")
    filter_s = col2.selectbox("📁 Filter by Status", ["All", "Pending", "Resolved"], key="admin_filter_query")
    
    st.write("---")
    
    filtered = queries
    if search_u: filtered = [q for q in filtered if search_u.lower() in q["user"].lower()]
    if filter_s != "All": filtered = [q for q in filtered if q["status"] == filter_s]
    
    if not filtered:
        st.info("No queries found matching the criteria.")
        return
        
    for q in reversed(filtered):
        with st.container(border=True):
            q_date = q.get("datetime", "Unknown Date")
            q_user = q.get("user", "Unknown")
            q_status = q.get("status", "Pending")
            q_text = q.get("text", "")
            q_reply = q.get("reply", "")
            
            badge_class = "badge-pending" if q_status == "Pending" else "badge-resolved"
            
            st.markdown(f"**{q_user}** &middot; <span style='color:#64748b; font-size:0.85rem;'>{q_date}</span> &middot; <span class='status-badge {badge_class}'>{q_status}</span>", unsafe_allow_html=True)
            st.markdown(f"<div style='margin-top:8px; padding:12px; background:#f8fafc; border-radius:8px; border-left: 4px solid #cbd5e1; font-size:1rem; color:#1e293b;'>{q_text}</div>", unsafe_allow_html=True)
            
            if q_status == "Pending":
                st.write("<br>", unsafe_allow_html=True)
                reply_input = st.text_area("Write your reply:", key=f"reply_input_{q['id']}", placeholder="Enter a professional response here...")
                if st.button("Mark as Resolved & Send", key=f"btn_resolve_{q['id']}", type="primary"):
                    if reply_input.strip():
                        with st.spinner("Updating query status..."):
                            for i, item in enumerate(queries):
                                if item["id"] == q["id"]:
                                    queries[i]["reply"] = reply_input
                                    queries[i]["status"] = "Resolved"
                                    break
                            save_queries(queries)
                            st.toast("Reply sent and marked as resolved!", icon="✅")
                            time.sleep(0.5)
                            st.rerun()
                    else:
                        st.warning("Please enter a reply before marking resolved.")
            else:
                st.markdown(f"**Admin Reply:**")
                st.success(q_reply)

def render_admin():
    if "Admin" not in st.session_state.current_user:
        st.error("Unauthorized access!")
        return
        
    render_page_header(
        "Admin Control Panel",
        "Manage question banks, users, timers, attempts, and platform settings.",
        "Platform management",
    )
    
    # Feature 4: Basic and Advanced banks isolated routing
    with st.expander("📁 Question Bank Management", expanded=False):
        admin_bank = st.radio("Select Question Bank", ["Basic", "Advanced"], horizontal=True, key="admin_bank_radio")
        if st.session_state.get('last_admin_bank') != admin_bank:
            st.session_state.admin_current_path = ""
            st.session_state.last_admin_bank = admin_bank
        
        active_admin_base = CSV_FOLDER if admin_bank == "Basic" else ADVANCED_CSV_FOLDER
        current_admin_path = st.session_state.get('admin_current_path', '')
        full_admin_path = os.path.join(active_admin_base, current_admin_path.replace('/', os.sep))
        
        st.markdown(f"**Current Directory ({admin_bank}):** `Root / {current_admin_path.replace('/', ' / ')}`")
        
        c_up, c_newf, c_upld = st.columns(3)
        with c_up:
            if current_admin_path != '':
                st.button("⬅️ Back / Up", on_click=nav_admin_up, use_container_width=True)
        with c_newf:
            new_f = st.text_input("New Folder", key="new_f_input", label_visibility="collapsed", placeholder="Folder Name")
            if st.button("Create Folder", use_container_width=True):
                if new_f:
                    os.makedirs(os.path.join(full_admin_path, new_f), exist_ok=True)
                    st.toast(f"Folder '{new_f}' created!", icon="✅")
                    st.rerun()
        with c_upld:
            uploaded_file = st.file_uploader("Upload CSV", type=['csv'], label_visibility="collapsed")
            if uploaded_file:
                with st.spinner("Uploading..."):
                    save_path = os.path.join(full_admin_path, uploaded_file.name)
                    with open(save_path, "wb") as f:
                        f.write(uploaded_file.getbuffer())
                    st.toast("File uploaded successfully!", icon="✅")
                    time.sleep(0.5)
                    st.rerun()
                
        st.write("---")
        
        items = sorted(os.listdir(full_admin_path)) if os.path.exists(full_admin_path) else []
        folders = [f for f in items if os.path.isdir(os.path.join(full_admin_path, f))]
        files = [f for f in items if f.endswith('.csv')]
        admin_search = st.text_input(
            "Search folders or CSV files",
            key=f"admin_search_{admin_bank}_{current_admin_path}",
            placeholder="Search this folder...",
        ).strip().lower()
        if admin_search:
            folders = [folder for folder in folders if admin_search in folder.lower()]
            files = [file_name for file_name in files if admin_search in file_name.lower()]
        
        st.markdown("#### Folders")
        if not folders: st.info("No subfolders.")
        for folder in folders:
            with st.container(border=True):
                fc1, fc2, fc3, fc4 = st.columns([3, 4, 2, 2])
                fc1.button(f"📁 {folder}", key=f"nav_{current_admin_path}_{folder}", on_click=nav_admin_down, args=(folder,), use_container_width=True)
                if current_admin_path == "" and folder in ["Arts", "Computer", "Current affairs", "Science", "Statistics"]:
                    fc2.markdown("<div style='padding-top:10px; color:#94a3b8; font-size:12px; font-weight:bold;'>System Protected</div>", unsafe_allow_html=True)
                else:
                    new_folder_name = fc2.text_input("Rename Folder", value=folder, key=f"ren_fld_inp_{current_admin_path}_{folder}", label_visibility="collapsed")
                    if fc3.button("✏️ Rename", key=f"ren_fld_btn_{current_admin_path}_{folder}", use_container_width=True):
                        if new_folder_name and new_folder_name.strip() and new_folder_name.strip() != folder:
                            try:
                                os.rename(os.path.join(full_admin_path, folder), os.path.join(full_admin_path, new_folder_name.strip()))
                                st.toast(f"Renamed to {new_folder_name.strip()}", icon="✅")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error renaming folder: {e}")
                    if fc4.button("🗑️ Delete", key=f"del_f_{current_admin_path}_{folder}", use_container_width=True):
                        try:
                            os.rmdir(os.path.join(full_admin_path, folder))
                            st.toast("Folder deleted", icon="✅")
                            st.rerun()
                        except OSError:
                            st.error("Folder not empty! Delete files inside first.")
                        
        st.write("---")
        st.markdown("#### Assessment Files")
        if not files: st.info("No CSV files found in this directory.")
        
        all_folders = []
        for root, dirs, _ in os.walk(active_admin_base):
            for d in dirs:
                rel = os.path.relpath(os.path.join(root, d), active_admin_base).replace(os.sep, '/')
                all_folders.append(rel)
        all_folders.insert(0, "Root")
        
        for f_name in files:
            file_p = os.path.join(full_admin_path, f_name)
            f_size = os.path.getsize(file_p) / 1024
            
            with st.container(border=True):
                c1, c2 = st.columns([8, 2])
                c1.markdown(f"📄 **{f_name}**")
                c2.markdown(f"<span style='color:#64748b; font-size:0.9rem;'>{f_size:.1f} KB</span>", unsafe_allow_html=True)
                
                mc1, mc2, mc3, mc4 = st.columns([3, 4, 2, 2])
                move_target = mc1.selectbox("Move to", ["-- Select --"] + all_folders, key=f"mov_{current_admin_path}_{f_name}", label_visibility="collapsed")
                if move_target != "-- Select --":
                    tgt = active_admin_base if move_target == "Root" else os.path.join(active_admin_base, move_target.replace('/', os.sep))
                    os.rename(file_p, os.path.join(tgt, f_name))
                    st.toast(f"Moved {f_name}", icon="✅")
                    st.rerun()
                
                new_f_name = mc2.text_input("Rename File", value=f_name, key=f"ren_inp_{current_admin_path}_{f_name}", label_visibility="collapsed")
                if mc3.button("✏️ Rename", key=f"ren_btn_{current_admin_path}_{f_name}", use_container_width=True):
                    if new_f_name and new_f_name.strip() and new_f_name.strip() != f_name:
                        clean_name = new_f_name.strip()
                        if not clean_name.endswith('.csv'):
                            clean_name += '.csv'
                        try:
                            os.rename(file_p, os.path.join(full_admin_path, clean_name))
                            st.toast("File renamed successfully", icon="✅")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error renaming file: {e}")
                            
                if mc4.button("🗑️ Delete", key=f"del_{current_admin_path}_{f_name}", use_container_width=True):
                    os.remove(file_p)
                    st.toast("File deleted", icon="✅")
                    st.rerun()

    all_basic = get_all_csv_files(CSV_FOLDER)
    all_adv = get_all_csv_files(ADVANCED_CSV_FOLDER)
    admin_file_options = {}
    for f in all_basic: admin_file_options[f"Basic | {f}"] = f
    for f in all_adv: admin_file_options[f"Advanced | {f}"] = f"ADVANCED|{f}"

    with st.expander("⏱️ Timer Configuration", expanded=False):
        st.markdown("Set precise examination time constraints for tests.")
        if admin_file_options:
            sel_display = st.selectbox("Select Assessment", list(admin_file_options.keys()), key="tmr_test")
            t_file = admin_file_options[sel_display]
            
            if t_file:
                timers_data = load_timers_data()
                current_settings = timers_data.get(t_file, {"mode": "Total Time", "value": 30})
                
                new_mode = st.radio(
                    "Timing Rule", 
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
                
                if st.button("Save Configuration", type="primary"):
                    with st.spinner("Saving..."):
                        timers_data[t_file] = {"mode": new_mode, "value": new_val}
                        save_timers_data(timers_data)
                        st.toast("Timer settings updated!", icon="✅")
        else:
            st.info("No tests available to configure.")

    with st.expander("⚙️ Assessment Access Control", expanded=False):
        st.markdown("Control maximum attempt limits per user.")
        a_col1, a_col2 = st.columns(2)
        users = get_all_users()
        with a_col1:
            sel_user = st.selectbox("Select Learner", list(users.keys()), key="adm_user")
        with a_col2:
            if admin_file_options:
                sel_test_display = st.selectbox("Select Assessment", list(admin_file_options.keys()), key="adm_test")
                sel_test = admin_file_options[sel_test_display]
            else:
                sel_test = None
        
        if sel_user and sel_test:
            curr_data = get_attempt_data(sel_user, sel_test)
            new_limit = st.number_input("Allowed Attempts Limit", min_value=1, value=curr_data['allowed'], key="adm_limit")
            if st.button("Update Access Limit", type="primary", key="btn_update_limit"):
                with st.spinner("Processing..."):
                    set_allowed_attempts(sel_user, sel_test, new_limit)
                    st.toast(f"Updated! {sel_user.split()[0]} now has {new_limit} allowed attempts.", icon="✅")

    with st.expander("⚖️ Scoring & Penalty Configuration", expanded=False):
        st.markdown("Configure negative marking deductions for incorrect answers (0.00 to 0.33).")
        if admin_file_options:
            sel_display_nm = st.selectbox("Select Assessment for Modification", list(admin_file_options.keys()), key="nm_sel_test")
            nm_test_key = admin_file_options[sel_display_nm]
            
            curr_val = get_neg_mark(nm_test_key)
            new_val = st.number_input("Negative Penalty Value", min_value=0.0, max_value=0.33, value=float(curr_val), step=0.01)
            
            if st.button("Apply Penalty Rule", type="primary"):
                with st.spinner("Applying rule..."):
                    set_neg_mark(nm_test_key, new_val)
                    st.toast(f"Negative marking set to {new_val}", icon="✅")
        else:
            st.info("No tests available to configure.")

    with st.expander("👥 User Management", expanded=False):
        users = get_all_users()
        um_tabs = st.tabs(["Add New User", "Remove User", "Reset Password"])
        
        with um_tabs[0]:
            new_u = st.text_input("New Username (Format: Name (Role))")
            new_p = st.text_input("Account Password", type="password")
            if st.button("Create Account", type="primary"):
                if new_u in users:
                    st.error("Username already exists in the system!")
                elif new_u and new_p:
                    with st.spinner("Provisioning account..."):
                        users[new_u] = new_p
                        save_users(users)
                        st.toast(f"Account '{new_u}' successfully created!", icon="✅")
                        time.sleep(0.5)
                        st.rerun()
                    
        with um_tabs[1]:
            del_u = st.selectbox("Select Account to Delete", [u for u in users if "Admin" not in u])
            confirm_del = st.checkbox(f"Permanently delete {del_u} and all associated data.")
            if st.button("Delete Account", type="primary"):
                if confirm_del and del_u:
                    with st.spinner("Removing user..."):
                        del users[del_u]
                        save_users(users)
                        st.toast("User account permanently deleted.", icon="✅")
                        time.sleep(0.5)
                        st.rerun()
                elif not confirm_del:
                    st.warning("Confirmation checkbox is required for deletion.")
                    
        with um_tabs[2]:
            ch_u = st.selectbox("Target Account", list(users.keys()), key="ch_u")
            ch_p = st.text_input("New Secure Password", type="password", key="ch_p")
            if st.button("Reset Password", type="primary"):
                if ch_p:
                    with st.spinner("Updating credentials..."):
                        users[ch_u] = ch_p
                        save_users(users)
                        st.toast("Password has been reset successfully.", icon="✅")

    with st.expander("📊 Learner Progress Reports", expanded=False):
        users = get_all_users()
        rep_u = st.selectbox("Select Learner Profile", list(users.keys()))
        if rep_u:
            history = load_history().get(rep_u, [])
            if not history:
                st.info(f"No assessment records found for {rep_u}.")
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
                
                st.markdown("#### Performance Summary")
                c1, c2, c3, c4 = st.columns(4)
                with c1: render_metric_card("Total Tests", total_tests, "blue")
                with c2: render_metric_card("Total Attempts", total_attempts, "purple")
                with c3: render_metric_card("Highest Score", f"{high_score:.2f}", "green")
                with c4: render_metric_card("Lowest Score", f"{low_score:.2f}", "amber")
                
                c5, c6, c7, c8 = st.columns(4)
                with c5: render_metric_card("Avg Score", f"{avg_score:.2f}", "blue")
                with c6: render_metric_card("Avg Percentage", f"{avg_perc:.2f}%", "purple")
                with c7: render_metric_card("Last Active", last_attempt.split()[0], "green")
                
                st.write("---")
                st.markdown("#### Complete History Transcript")
                for att in reversed(history):
                    result_status = "Pass" if att['percentage'] >= 33 else "Fail"
                    with st.expander(f"Attempt {att['attempt_number']} - {att['test_name']} ({att['datetime']}) | Final Score: {att['final_score']:.2f}"):
                        st.markdown(f"**Section:** {att['subject']} | **Category:** {att['folder']} | **Result:** <span style='color:{'#16a34a' if result_status=='Pass' else '#dc2626'}; font-weight:bold;'>{result_status}</span>", unsafe_allow_html=True)
                        st.write(f"**Total Questions:** {att['total_questions']} &middot; **Attempted:** {att['attempted']} &middot; **Correct:** {att['correct']} &middot; **Incorrect:** {att['incorrect']} &middot; **Unanswered:** {att['unanswered']}")
                        st.write(f"**Positive Marks:** {att['marks_obtained']} &middot; **Penalty Deductions:** {att['negative_marks']:.2f} &middot; **Final Percentage:** {att['percentage']}%")
                        
                        st.markdown("##### Detailed Answer Trace")
                        for qd in att['q_details']:
                            st.markdown(f"**Q{qd['q_num']}. {qd['question']}**")
                            c_a, c_b, c_c = st.columns(3)
                            c_a.write(f"**Selected:** {qd['user_ans']}")
                            c_b.write(f"**Correct Key:** {qd['correct_ans']}")
                            status_color = "#16a34a" if qd['status'] == "Correct" else "#dc2626" if qd['status'] == "Incorrect" else "#d97706"
                            c_c.markdown(f"**Validation:** <span style='color:{status_color}; font-weight:700;'>{qd['status']}</span>", unsafe_allow_html=True)
                            st.write(f"**Marks:** {qd['marks']} | **Penalty:** {qd['negative']:.2f}")
                            st.write("---")

def render_dashboard():
    first_name = st.session_state.current_user.split()[0] if st.session_state.current_user else "Learner"
    render_page_header(
        f"Welcome back, {first_name}",
        "Choose a test series and continue building your exam readiness.",
        "Practice dashboard",
    )

    col_space1, col_tests, col_space2 = st.columns([1, 4, 1])
    
    with col_tests:
        col_tests_head1, col_tests_head2 = st.columns([1, 1])
        with col_tests_head1:
            st.markdown("### 📋 Available Test Series")
        with col_tests_head2:
            st.session_state.current_bank = st.radio("Question Bank", ["Basic", "Advanced"], horizontal=True, label_visibility="collapsed")
        
        active_user_base = CSV_FOLDER if st.session_state.current_bank == "Basic" else ADVANCED_CSV_FOLDER
        
        search_query = st.text_input("🔍 Search Subject or Folder...", placeholder="e.g. Physics, History...", key="dash_search").strip()
        
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
        
        st.write("<br>", unsafe_allow_html=True)
        if not files_to_display: 
            st.info("No assessments found matching your search criteria.")
        else:
            for file in files_to_display:
                with st.container(border=True):
                    user = st.session_state.current_user
                    test_key = file if st.session_state.current_bank == "Basic" else f"ADVANCED|{file}"
                    
                    attempt_data = get_attempt_data(user, test_key)
                    allowed = attempt_data['allowed']
                    used = attempt_data['used']
                    remaining = allowed - used

                    base_name = os.path.basename(file).replace('.csv', '').replace('_', ' ')
                    folder_context = os.path.dirname(file) or 'Root'

                    c1, c2 = st.columns([3, 1])
                    c1.markdown(f"<h4 class='test-card-title'>📄 {base_name}</h4>", unsafe_allow_html=True)
                    c1.markdown(f"<div class='test-card-folder'>📁 {folder_context.replace('/', ' / ')}</div>", unsafe_allow_html=True)
                    
                    c1.markdown(f"<div class='test-card-stats'>Attempts: {used} / {allowed} &nbsp;&middot;&nbsp; Remaining: {remaining}</div>", unsafe_allow_html=True)
                    
                    if remaining > 0:
                        if c2.button("Start Assessment", key=f"load_{test_key}"):
                            load_quiz(file)
                    else:
                        c2.button("Limit Reached", key=f"limit_{test_key}", disabled=True, help="Maximum attempts reached. Please contact your administrator.")
                        
        st.write("---")
        
        # --- FEATURE 5: Ask Query Section ---
        st.markdown("### 💬 Ask a Query / Support")
        with st.expander("Submit a new academic or technical query", expanded=False):
            query_text = st.text_area(
                "Describe your doubt clearly:", 
                placeholder="E.g., I need clarification on Modern Physics Question 4...",
                height=120,
                key="new_query_text"
            )
            
            # Simple python-side word counting for limits
            word_count = len(re.findall(r'\w+', query_text))
            st.caption(f"Word count updates when submitting. Limit: 100 words. (Current: {word_count})")
            
            if st.button("Submit Query", type="primary", key="btn_submit_query"):
                if word_count == 0:
                    st.warning("Query cannot be empty.")
                elif word_count > 100:
                    st.error("Your query exceeds the maximum limit of 100 words.")
                else:
                    with st.spinner("Submitting your query..."):
                        queries = load_queries()
                        queries.append({
                            "id": str(uuid.uuid4()),
                            "user": st.session_state.current_user,
                            "datetime": time.strftime("%Y-%m-%d %H:%M:%S"),
                            "text": query_text,
                            "status": "Pending",
                            "reply": ""
                        })
                        save_queries(queries)
                        st.toast("Query successfully submitted to Admin!", icon="✅")
                        st.session_state.query_input = ""  # Trigger clear logic if needed via callback
                        time.sleep(0.5)
                        st.rerun()
                        
        # Display User's past queries
        st.write("<br>", unsafe_allow_html=True)
        st.markdown("#### Past Queries History")
        user_queries = load_queries()
        user_history = [q for q in user_queries if q.get("user") == st.session_state.current_user]
        
        if not user_history:
            st.info("You haven't submitted any queries yet.")
        else:
            for q in reversed(user_history):
                with st.container(border=True):
                    q_status = q.get("status", "Pending")
                    badge_class = "badge-pending" if q_status == "Pending" else "badge-resolved"
                    
                    st.markdown(f"<span style='color:#64748b; font-size:0.85rem;'>Submitted: {q.get('datetime', 'N/A')}</span> &middot; <span class='status-badge {badge_class}'>{q_status}</span>", unsafe_allow_html=True)
                    st.markdown(f"<div style='margin-top:8px; font-weight:600; color:#1e293b;'>{q.get('text', '')}</div>", unsafe_allow_html=True)
                    
                    if q_status == "Resolved" and q.get("reply"):
                        st.write("---")
                        st.markdown("<p style='font-size:0.85rem; color:#64748b; margin:0 0 4px 0; text-transform:uppercase; font-weight:700;'>Admin Reply</p>", unsafe_allow_html=True)
                        st.success(q.get("reply"))
                        
    if st.session_state.quiz_ready:
        st.divider()
        st.success(f"✅ Assessment **{st.session_state.topic}** has been securely loaded into the engine.")
        col_space1, col_start, col_space2 = st.columns([1, 2, 1])
        with col_start:
            if st.button("🚀 Proceed to Instructions", type="primary", use_container_width=True):
                with st.spinner("Navigating..."):
                    st.session_state.active_page = "Instructions"
                    time.sleep(0.3)
                    st.rerun()

def render_instructions():
    render_page_header(
        "Important Instructions",
        st.session_state.topic,
        "Before you begin",
    )
    
    # --- NEW MOTIVATIONAL BANNER ---
    st.markdown(
        """
        <div class="motivational-banner">
            <h2>✨📚 Best of Luck for Your Exam! 🍀🎯</h2>
            <p>Believe in Yourself.</p>
            <p>Stay Calm.</p>
            <p>Read Every Question Carefully.</p>
            <p>Manage Your Time Wisely.</p>
            <p class="highlight-text">Success comes to those who prepare with dedication.</p>
            <p>We wish you all the very best for your examination!</p>
            <div class="emojis">🌟📖💯🚀</div>
        </div>
        """,
        unsafe_allow_html=True
    )
    
    col1, col2, col3 = st.columns([1, 3, 1])
    with col2:
        with st.container(border=True):
            st.markdown("### Assessment Guidelines")
            st.markdown(f"🔹 **Total Questions:** {len(st.session_state.questions)}")
            
            time_display_str = "No Time Limit"
            if st.session_state.timer_mode != "No Timer":
                time_display_str = f"{st.session_state.time_val} Minutes"

            st.markdown(f"🔹 **Time Limit Constraint:** {time_display_str}")
            
            neg_mark_display = get_neg_mark(st.session_state.current_test_filename)
            if neg_mark_display > 0:
                st.markdown(f"🔹 **Penalty Rules:** -{neg_mark_display} deducted for every incorrect submission.")
            
            st.markdown("""
            🔹 **Navigation:** You can jump to any question using the Question Palette on the right.
            🔹 **Auto-Pause:** If you become inactive for **5 minutes**, the exam freezes automatically to secure your timing.
            🔹 **Marking Scheme:** Every correct answer adds positive marks to your overall score.
            🔹 **Submission:** Exam validates and submits automatically when the timer reaches zero.
            """)
            
            st.write("<br>", unsafe_allow_html=True)
            if st.button("✅ I confirm I have read all guidelines. Begin Exam.", type="primary", use_container_width=True):
                with st.spinner("Initializing live examination engine..."):
                    now = time.time()
                    st.session_state.last_calc_time = now
                    st.session_state.last_interaction_time = now
                    st.session_state.is_paused = False
                    st.session_state.active_page = "Exam"
                    time.sleep(0.4)
                    st.rerun()

def render_paused_screen():
    st.write("<br><br>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        with st.container(border=True):
            st.markdown("<h1 style='text-align: center; color: #dc2626;'>⏸ Exam Paused</h1>", unsafe_allow_html=True)
            st.markdown("<p style='text-align: center; color: #475569; font-size: 1.1rem;'>Your timer has been frozen and your progress is securely cached.</p>", unsafe_allow_html=True)
            st.write("---")
            if st.button("▶️ Resume Assessment", type="primary", use_container_width=True):
                with st.spinner("Resuming engine..."):
                    now = time.time()
                    st.session_state.last_calc_time = now
                    st.session_state.last_interaction_time = now
                    st.session_state.is_paused = False
                    time.sleep(0.3)
                    st.rerun()

def render_exam():
    if st.session_state.is_paused:
        render_paused_screen()
        return

    q_idx = st.session_state.current_q
    st.session_state.visited_questions.add(q_idx)
    total_q = len(st.session_state.questions)
    q_data = st.session_state.questions[q_idx]

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
        st.markdown("<p class='palette-title'>Exam Controls & Timer</p>", unsafe_allow_html=True)
        render_visual_timer()
        
        st.write("<div style='margin-top:10px;'></div>", unsafe_allow_html=True)
        st.button("⏸ Pause Exam", type="secondary", on_click=pause_exam, use_container_width=True, key="btn_pause_top")
        
        username_display = st.session_state.current_user.split()[0]
        avatar_letter = username_display[0].upper() if username_display else "U"
        
        html_legend = f"""
<div style="background-color: #ffffff; padding: 15px; border: 1px solid #e2e8f0; border-radius: 12px; margin: 15px 0;">
<div style="display: flex; align-items: center; gap: 10px; margin-bottom: 15px;">
<div style="width: 34px; height: 34px; background-color: #2563eb; color: white; border-radius: 50%; display: flex; justify-content: center; align-items: center; font-weight: bold; font-size: 16px;">
<img src="https://ui-avatars.com/api/?name={username_display}&background=2563eb&color=fff&rounded=true&bold=true&size=34" style="border-radius: 50%;" onerror="this.style.display='none'; this.parentElement.innerText='{avatar_letter}';">
</div>
<span style="font-weight: 700; color: #1e293b; font-size: 15px;">{username_display}'s Session</span>
</div>
<div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px 8px; font-size: 11px; color: #475569;">
<div style="display: flex; align-items: center; gap: 6px;">
<div style="width: 20px; height: 20px; background-color: #16a34a; color: white; border-radius: 6px 6px 0 0; display: flex; align-items: center; justify-content: center; font-weight: bold; font-size: 11px;">{ans_count}</div>
<span style="font-weight:600;">Answered</span>
</div>
<div style="display: flex; align-items: center; gap: 6px;">
<div style="width: 20px; height: 20px; background-color: #7c3aed; color: white; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-weight: bold; font-size: 11px;">{marked_count}</div>
<span style="font-weight:600;">Marked</span>
</div>
<div style="display: flex; align-items: center; gap: 6px;">
<div style="width: 20px; height: 20px; background-color: #ffffff; border: 1px solid #cbd5e1; color: #334155; border-radius: 6px; display: flex; align-items: center; justify-content: center; font-weight: bold; font-size: 11px;">{not_visit_count}</div>
<span style="font-weight:600;">Not Visited</span>
</div>
<div style="display: flex; align-items: center; gap: 6px;">
<div style="width: 20px; height: 20px; background-color: #ef4444; color: white; border-radius: 0 0 6px 6px; display: flex; align-items: center; justify-content: center; font-weight: bold; font-size: 11px;">{not_ans_count}</div>
<span style="font-weight:600;">Not Answered</span>
</div>
<div style="display: flex; align-items: center; gap: 6px; grid-column: span 2;">
<div style="width: 20px; height: 20px; background-color: #7c3aed; color: white; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-weight: bold; font-size: 11px; position: relative; overflow: visible;">{ans_marked_count}<div style="position: absolute; bottom: -2px; right: -2px; width: 8px; height: 8px; background-color: #16a34a; border-radius: 50%; border: 1px solid white;"></div></div>
<span style="font-weight:600;">Marked and Answered</span>
</div>
</div>
</div>
"""
        st.markdown(html_legend, unsafe_allow_html=True)
        
        st.markdown(
            f"""<div style='background:linear-gradient(90deg, #eff6ff, #dbeafe); padding:10px 15px; font-weight:800; color:#1e3a8a; font-size:12px; text-transform: uppercase; border-radius: 12px; margin-bottom: 12px; border: 1px solid #bfdbfe; text-align: center;'>
            SECTION: {st.session_state.topic}
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
                
            grid_html += f'<div class="{" ".join(classes)}" data-idx="{i}" role="button" tabindex="0" aria-label="Go to question {i+1}">{i+1}</div>\n'
            
        full_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
        <style>
        body {{ margin: 0; padding: 0; font-family: Inter, -apple-system, sans-serif; background-color: transparent; }}
        .palette-grid {{
            display: grid;
            grid-template-columns: repeat(5, minmax(36px, 1fr));
            gap: 10px;
            padding: 8px 4px;
        }}
        .q-btn {{
            aspect-ratio: 1 / 1;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 14px;
            font-weight: 750;
            cursor: pointer;
            border-radius: 8px;
            border: 1px solid #cbd5e1;
            user-select: none;
            transition: all 0.2s ease;
        }}
        .q-btn:hover {{ transform: translateY(-2px); box-shadow: 0 4px 8px rgba(15, 23, 42, 0.1); }}
        .q-btn:focus-visible {{ outline: 3px solid #3b82f6; outline-offset: 2px; }}
        .notvisited {{ background: #ffffff; color: #334155; border-color: #cbd5e1; }}
        .notanswered {{ background: #ef4444; color: #ffffff; border-color: #ef4444; border-radius: 0 0 12px 12px; }}
        .answered {{ background: #16a34a; color: #ffffff; border-color: #16a34a; border-radius: 12px 12px 0 0; }}
        .marked {{ background: #7c3aed; color: #ffffff; border-color: #7c3aed; border-radius: 50%; }}
        .answeredmarked {{ background: #7c3aed; color: #ffffff; border-color: #7c3aed; border-radius: 50%; position: relative; overflow: visible; }}
        .answeredmarked::after {{
            content: ''; position: absolute; bottom: -3px; right: -3px; width: 10px; height: 10px;
            background-color: #16a34a; border-radius: 50%; border: 2px solid white; z-index: 3;
        }}
        .current {{ outline: 3px solid #2563eb; outline-offset: 3px; transform: scale(1.05); z-index: 2; border-color: #2563eb; }}
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
                    item.addEventListener('keydown', function(event) {{
                        if (event.key === 'Enter' || event.key === ' ') {{
                            event.preventDefault();
                            item.click();
                        }}
                    }});
                }});
            }});
        </script>
        </body>
        </html>
        """
        
        components.html(full_html, height=360, scrolling=True)

        st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)
        b1, b2 = st.columns(2)
        with b1:
            st.button("Question Paper", use_container_width=True, key="btn_qp")
        with b2:
            st.button("Instructions", use_container_width=True, key="btn_inst")
            
        st.write("<br>", unsafe_allow_html=True)
        
        if st.button("🚀 Final Submit", type="primary", use_container_width=True, key="btn_sub_right"):
            with st.spinner("Submitting your exam responses..."):
                time.sleep(0.5)
                nav_submit()
                st.rerun()

    # ================== LEFT PANEL ==================
    with col_main:
        st.markdown(f"<p class='exam-kicker'>Live Assessment &middot; {st.session_state.topic}</p>", unsafe_allow_html=True)
        st.progress((q_idx + 1) / total_q, text=f"Question Progress: {q_idx + 1} / {total_q}")
        
        raw_q = q_data['q']
        clean_q = re.sub(r'^[Qq]?(?:uestion)?\s*\d+[\.\)]\s*', '', raw_q)
        
        st.markdown(
            f"""
            <section class="question-card">
                <span class="question-card__number">Question {q_idx + 1}</span>
                <p class="question-card__text">{clean_q}</p>
            </section>
            """,
            unsafe_allow_html=True,
        )
        
        # --- FEATURE: DYNAMIC QUESTION TYPE RENDERING ---
        if q_data.get('type') == 'match':
            saved_ans = st.session_state.user_answers.get(q_idx, {})
            
            m_col1, m_col2 = st.columns([1, 1])
            m_col1.markdown("<div style='color: #475569; font-weight: 800; font-size: 0.95rem; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 12px; border-bottom: 2px solid #e2e8f0; padding-bottom: 8px;'>Column A (Fixed)</div>", unsafe_allow_html=True)
            m_col2.markdown("<div style='color: #475569; font-weight: 800; font-size: 0.95rem; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 12px; border-bottom: 2px solid #e2e8f0; padding-bottom: 8px;'>Column B (Select Match)</div>", unsafe_allow_html=True)
            
            for l_item in q_data['left']:
                r_c1, r_c2 = st.columns([1, 1])
                r_c1.markdown(f"<div style='padding-top: 10px; font-weight: 600; font-size: 1.15rem; color:#1e293b;'>{l_item}</div>", unsafe_allow_html=True)
                
                w_key = f"match_{q_idx}_{l_item}"
                options = ["-- Select Option --"] + q_data['options']
                current_val = saved_ans.get(l_item, "-- Select Option --")
                try:
                    idx = options.index(current_val)
                except ValueError:
                    idx = 0
                
                r_c2.selectbox("Match Target", options, index=idx, key=w_key, on_change=on_match_change, args=(q_idx, q_data['left']), label_visibility="collapsed")
                
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
    
    accuracy = round((correct / attempted * 100) if attempted > 0 else 0, 1)
    percentage = round((final_score / total_q) * 100, 2) if total_q > 0 else 0

    render_page_header(
        "Performance Analysis",
        f"{st.session_state.topic} &middot; Your result is completely processed and saved.",
        "Test complete",
    )

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        render_metric_card("Final score", f"{final_score:.2f}", "blue", f"Out of {total_q} questions")
    with c2:
        render_metric_card("Percentage", f"{percentage:.2f}%", "purple", "Based on final score")
    with c3:
        render_metric_card("Accuracy", f"{accuracy:.1f}%", "green", "Correct out of attempted")
    with c4:
        render_metric_card("Attempted", f"{attempted} / {total_q}", "amber", f"{unanswered} unattempted")

    st.write("<br>", unsafe_allow_html=True)

    c5, c6, c7, c8 = st.columns(4)
    with c5:
        render_metric_card("Correct", str(correct), "green", "Answers validated correct")
    with c6:
        render_metric_card("Incorrect", str(incorrect), "red", "Answers marked incorrect")
    with c7:
        render_metric_card("Unattempted", str(unanswered), "amber", "Questions left blank")
    with c8:
        render_metric_card("Negative marks", f"-{negative:.2f}", "red", "Total penalty applied")

    st.write("<br><br>", unsafe_allow_html=True)
    st.markdown("### 📋 Detailed Answer Key Transcript")
    st.write("---")
    
    for i, q in enumerate(st.session_state.questions):
        st.markdown(f"<div style='font-size:1.15rem; font-weight:700; color:#1e293b; margin-bottom:8px;'>Q{i+1}: {q['q']}</div>", unsafe_allow_html=True)
        
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
                st.info("**Correct Answer Mapping:**")
                for l, r in correct_ans.items():
                    st.write(f"- **{l}** ➔ {r}")
            else: 
                st.error("**Your Answer:** Incorrect ❌")
                st.markdown("*Your Mapping:*")
                for l in q['left']:
                    u_r = user_ans.get(l, "Not Selected")
                    st.write(f"- **{l}** ➔ {u_r}")
                    
                st.info("**Correct Answer Mapping:**")
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
                st.error(f"**Your Answer:** {user_ans} (❌ Incorrect)")
                st.info(f"**Correct Answer Engine:** {correct_ans}")
        st.write("---")
        
    st.write("<br>", unsafe_allow_html=True)
    if st.button("🏠 Return to Dashboard", type="primary"):
        with st.spinner("Loading workspace..."):
            st.session_state.active_page = "Dashboard"
            st.session_state.quiz_ready = False
            time.sleep(0.3)
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
        elif st.session_state.active_page == "Admin":
            render_admin()
        elif st.session_state.active_page == "UserQueries":
            render_user_queries()
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
