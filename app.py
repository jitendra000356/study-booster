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
    page_title="Study Booster | Premium CBT", 
    page_icon="🎓", 
    layout="wide", 
    initial_sidebar_state="expanded"
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
QUERIES_FILE = 'queries_data.json'

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
    if not st.session_state.get('attempt_recorded', False):
        user = st.session_state.get('current_user')
        test_key = st.session_state.get('current_test_filename')
        if user and test_key:
            original_file = test_key.replace("ADVANCED|", "")
            increment_attempt(user, test_key)
            record_detailed_attempt(user, test_key, original_file)
            
            # Feature 4: Navigation update - Store current index for Results navigation
            history = load_history().get(user, [])
            st.session_state.history_view_index = len(history) - 1
            
        st.session_state.attempt_recorded = True

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
        'dashboard_tab': "Practice",  # For custom dash tabs navigation
        'is_paused': False,
        'current_test_filename': "",
        'attempt_recorded': False,
        'admin_current_path': "",
        'sid': "",
        'current_bank': "Basic",
        'last_admin_bank': "Basic",
        'query_input': "",
        'history_view_index': -1
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
    with st.spinner(f"Configuring {os.path.basename(file_name)} engine..."):
        st.session_state.questions = []
        bank = st.session_state.get('current_bank', 'Basic')
        base_dir = CSV_FOLDER if bank == 'Basic' else ADVANCED_CSV_FOLDER
        file_path = os.path.join(base_dir, file_name.replace('/', os.sep))
        
        test_key = file_name if bank == 'Basic' else f"ADVANCED|{file_name}"
        
        with open(file_path, 'r', encoding='utf-8-sig', errors='ignore') as f:
            reader = csv.DictReader(f)
            for row in reader:
                raw_type = row.get('Type')
                q_type = str(raw_type).strip().lower() if raw_type else ''
                
                if q_type == 'match':
                    left_items = []
                    right_items = []
                    for i in range(1, 11): 
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
                            'options': sorted(right_items), 
                            'ans': {l: r for l, r in zip(left_items, right_items)} 
                        })
                else:
                    opts = []
                    for i in range(1, 6):
                        col_name = f'Option{i}'
                        val = row.get(col_name)
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

def calculate_detailed_score(test_key):
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
        record_attempt_usage()
        st.session_state.active_page = "Result"

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
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
        
        {bg_css}

        :root {{
            --sb-primary: {UI_COLORS['primary']};
            --sb-primary-dark: {UI_COLORS['primary_dark']};
            --sb-ink: {UI_COLORS['ink']};
            --sb-muted: {UI_COLORS['muted']};
            --sb-surface: {UI_COLORS['surface']};
            --sb-border: {UI_COLORS['border']};
        }}

        html, body, [class*="css"]  {{ font-family: 'Inter', sans-serif; }}
        .stApp {{ color: var(--sb-ink); }}
        header[data-testid="stHeader"] {{ background: transparent !important; }}
        
        .block-container {{
            max-width: 1400px !important;
            padding: clamp(1rem, 3vw, 2.5rem) !important;
            margin: 1.5rem auto !important;
            min-height: calc(100vh - 4rem);
            border: 1px solid rgba(226, 232, 240, 0.85);
            border-radius: 20px;
            background: rgba(255, 255, 255, 0.96) !important;
            backdrop-filter: blur(10px);
            box-shadow: 0 25px 50px -12px rgba(15, 23, 42, 0.15);
            animation: fadeIn 0.4s ease-out forwards;
        }}
        @keyframes fadeIn {{ from {{ opacity: 0; transform: translateY(10px); }} to {{ opacity: 1; transform: translateY(0); }} }}

        /* EdTech Premium Sidebar */
        section[data-testid="stSidebar"] {{ 
            background: #ffffff !important; 
            border-right: 1px solid #e2e8f0; 
            box-shadow: 2px 0 20px rgba(0,0,0,0.03);
        }}
        section[data-testid="stSidebar"] * {{ color: #334155 !important; }}
        
        .edtech-profile-card {{
            background: linear-gradient(135deg, rgba(79, 70, 229, 0.05), rgba(79, 70, 229, 0.12));
            border: 1px solid rgba(79, 70, 229, 0.2);
            border-radius: 16px;
            padding: 1.25rem 1rem;
            margin: 0.5rem 0 1.5rem 0;
            display: flex;
            align-items: center;
            gap: 12px;
            box-shadow: 0 4px 6px -1px rgba(79, 70, 229, 0.05);
        }}
        .edtech-profile-avatar {{
            width: 44px; height: 44px;
            border-radius: 50%;
            background: linear-gradient(135deg, #4f46e5, #6366f1);
            color: white !important;
            display: flex; align-items: center; justify-content: center;
            font-weight: 800; font-size: 1.1rem;
            box-shadow: 0 4px 10px rgba(79, 70, 229, 0.3);
        }}
        .edtech-profile-info strong {{ display: block; font-size: 0.95rem; font-weight: 700; color: #0f172a !important; line-height: 1.2; }}
        .edtech-profile-info span {{ display: block; font-size: 0.75rem; font-weight: 600; color: #64748b !important; text-transform: uppercase; letter-spacing: 0.05em; margin-top: 2px; }}

        section[data-testid="stSidebar"] div.stButton > button {{ 
            background: transparent !important; border-color: transparent !important; 
            color: #475569 !important; text-align: left !important; box-shadow: none !important; 
            font-size: 0.95rem !important; padding: 0.6rem 0.8rem !important;
            border-radius: 10px !important;
            transition: all 0.2s ease;
            font-weight: 600 !important;
        }}
        section[data-testid="stSidebar"] div.stButton > button:hover:not(:disabled) {{ 
            background: #f1f5f9 !important; color: #0f172a !important; transform: translateX(4px); 
        }}
        .active-sidebar-btn {{
            background: #eff6ff !important;
            color: #2563eb !important;
            border-left: 4px solid #2563eb !important;
            border-radius: 0 10px 10px 0 !important;
        }}

        /* Buttons and Cards */
        div.stButton > button {{
            min-height: 2.8rem; border-radius: 12px; font-weight: 600; font-size: 0.95rem;
            transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
            border: 1px solid #cbd5e1; background: #ffffff; color: #0f172a;
        }}
        div.stButton > button:hover:not(:disabled) {{
            border-color: #93c5fd; background: #f8fafc;
            box-shadow: 0 6px 12px -2px rgba(0,0,0,0.05); transform: translateY(-1px);
        }}
        div.stButton > button[kind="primary"] {{
            border: none; background: linear-gradient(135deg, var(--sb-primary) 0%, #6366f1 100%);
            color: #ffffff !important; box-shadow: 0 4px 12px rgba(79, 70, 229, 0.25);
        }}
        div.stButton > button[kind="primary"] * {{ color: white !important; }}
        div.stButton > button[kind="primary"]:hover:not(:disabled) {{ 
            box-shadow: 0 8px 20px rgba(79, 70, 229, 0.4); transform: translateY(-2px); 
        }}
        
        .metric-card {{
            padding: 1.25rem; border: 1px solid #e2e8f0; border-top: 4px solid var(--metric-accent, #4f46e5);
            border-radius: 16px; background: #ffffff;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.03);
            transition: all 0.25s ease;
        }}
        .metric-card:hover {{ transform: translateY(-4px); box-shadow: 0 12px 20px -5px rgba(0, 0, 0, 0.08); }}
        .metric-card span {{ display: block; color: #64748b !important; font-size: 0.8rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; }}
        .metric-card strong {{ display: block; margin-top: 0.4rem; color: #0f172a; font-size: clamp(1.4rem, 2vw, 1.8rem); font-weight: 800; }}
        
        /* Motivational Banner */
        .motivational-banner {{
            background: linear-gradient(120deg, #4f46e5, #7c3aed, #ec4899);
            background-size: 200% 200%;
            animation: gradientMove 6s ease infinite;
            border-radius: 16px; padding: 1.5rem 2rem; color: white; margin-bottom: 2rem;
            box-shadow: 0 10px 25px -5px rgba(79, 70, 229, 0.3);
            display: flex; justify-content: space-between; align-items: center;
        }}
        @keyframes gradientMove {{ 0% {{ background-position: 0% 50%; }} 50% {{ background-position: 100% 50%; }} 100% {{ background-position: 0% 50%; }} }}
        .banner-text h2 {{ margin: 0 0 0.5rem 0 !important; color: white !important; font-weight: 800; font-size: 1.8rem; }}
        .banner-text p {{ margin: 0 !important; color: rgba(255,255,255,0.9) !important; font-size: 1rem; font-weight: 500; }}
        .banner-emoji {{ font-size: 3.5rem; animation: float 3s ease-in-out infinite; }}
        @keyframes float {{ 0% {{ transform: translateY(0px); }} 50% {{ transform: translateY(-10px); }} 100% {{ transform: translateY(0px); }} }}

        /* Custom Tabs Styling */
        div[data-testid="stTabs"] button {{
            font-size: 1.05rem; font-weight: 600; padding: 0.5rem 1rem;
            transition: all 0.2s ease;
        }}
        
        /* Alerts styling */
        div[data-testid="stAlert"] {{
            border-radius: 12px; border: none; border-left: 4px solid; 
            box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05); background: #ffffff;
        }}
        
        /* Result Top Colored Cards */
        .res-correct {{ border-top-color: #16a34a !important; background: linear-gradient(to bottom, #f0fdf4, #ffffff) !important; }}
        .res-incorrect {{ border-top-color: #dc2626 !important; background: linear-gradient(to bottom, #fef2f2, #ffffff) !important; }}
        .res-unanswered {{ border-top-color: #d97706 !important; background: linear-gradient(to bottom, #fffbeb, #ffffff) !important; }}

        @media (max-width: 768px) {{
            .block-container {{ padding: 1rem !important; border-radius: 0; }}
            .motivational-banner {{ flex-direction: column; text-align: center; padding: 1.5rem; gap: 1rem; }}
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
            body {{ margin:0; padding:0; font-family: Inter, sans-serif; background: transparent; }}
            .timer-box {{
                box-sizing: border-box; min-height: 55px; padding: 10px;
                border: 2px solid #fecaca; border-radius: 12px;
                background: linear-gradient(135deg, #fff5f5, #fff1f2);
                color: #e11d48; font-size: 22px; font-weight: 800; text-align: center;
                display: flex; align-items: center; justify-content: center; gap: 8px;
                box-shadow: 0 4px 6px rgba(225, 29, 72, 0.1);
            }}
            .no-timer {{ background: #f0f9ff; border-color: #bae6fd; color: #0284c7; font-size: 16px; }}
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
            
            if (!is_timed) {{ display.innerHTML = "Practice Mode - No Limit"; }} 
            else {{
                function updateDisplay() {{
                    if (rem <= 0) {{ display.innerHTML = "TIME UP!"; return false; }}
                    var m = Math.floor(rem / 60); var s = Math.floor(rem % 60);
                    display.innerHTML = (m < 10 ? "0" + m : m) + ":" + (s < 10 ? "0" + s : s);
                    return true;
                }}
                updateDisplay();
                var x = setInterval(function() {{ rem--; if (!updateDisplay()) clearInterval(x); }}, 1000);
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
    st.write("<br><br>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 1.5, 1]) 
    with col2:
        with st.container(border=True):
            st.markdown("<h1 style='text-align:center; color:#0f172a; font-weight:800; margin-bottom:0.2rem;'>Study Booster</h1>", unsafe_allow_html=True)
            st.markdown("<p style='text-align:center; font-size:1rem; color:#64748b; margin-top:0;'>Your focused space for practice and progress.</p>", unsafe_allow_html=True)
            st.divider()
            username = st.selectbox("👤 Select Profile", ["-- Select User --"] + list(users.keys()))
            pwd = st.text_input("🔑 Enter Passcode", type="password")
            st.write("<br>", unsafe_allow_html=True)
            if st.button("Secure Login 🚀", type="primary", use_container_width=True):
                if username != "-- Select User --" and users.get(username) == pwd:
                    with st.spinner("Authenticating secure session..."):
                        time.sleep(0.5)
                        st.session_state.auth = True
                        st.session_state.current_user = username
                        st.session_state.active_page = "Dashboard"
                        st.session_state.dashboard_tab = "Practice"
                        new_sid = base64.urlsafe_b64encode(os.urandom(12)).decode()
                        st.session_state.sid = new_sid
                        st.query_params["sid"] = new_sid
                        st.rerun()
                else:
                    st.error("❌ Invalid Credentials! Please try again.")

def render_sidebar():
    is_admin = "Admin" in st.session_state.current_user
    user_initial = st.session_state.current_user[0].upper()
    role = "Administrator" if is_admin else "Learner"

    st.sidebar.markdown(f"""
    <div class='edtech-profile-card'>
        <div class='edtech-profile-avatar'>{user_initial}</div>
        <div class='edtech-profile-info'>
            <strong>{st.session_state.current_user.split()[0]}</strong>
            <span>{role}</span>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    if is_admin:
        if st.sidebar.button("⚙️ Admin Control Panel", use_container_width=True):
            st.session_state.active_page = "Admin"
            st.rerun()
        if st.sidebar.button("💬 User Queries", use_container_width=True):
            st.session_state.active_page = "UserQueries"
            st.rerun()
        st.sidebar.divider()
            
    if st.sidebar.button("📚 Dashboard", use_container_width=True):
        st.session_state.active_page = "Dashboard"
        st.session_state.dashboard_tab = "Practice"
        st.rerun()
        
    if st.sidebar.button("📈 Performance", use_container_width=True):
        st.session_state.active_page = "Dashboard"
        st.session_state.dashboard_tab = "Performance"
        st.rerun()
        
    if st.sidebar.button("💬 Ask Query", use_container_width=True):
        st.session_state.active_page = "Dashboard"
        st.session_state.dashboard_tab = "Ask Query"
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
            time.sleep(0.4)
            st.rerun()

def render_user_queries():
    if "Admin" not in st.session_state.current_user:
        st.error("Unauthorized access!")
        return
        
    st.markdown("<h2 style='color:#0f172a; font-weight:800;'>Support Center & Queries</h2>", unsafe_allow_html=True)
    st.write("---")
    
    queries = load_queries()
    col1, col2 = st.columns([2, 1])
    search_u = col1.text_input("🔍 Search by Username", placeholder="Type username...", key="admin_search_query")
    filter_s = col2.selectbox("📁 Filter by Status", ["All", "Pending", "Resolved"], key="admin_filter_query")
    
    filtered = queries
    if search_u: filtered = [q for q in filtered if search_u.lower() in q["user"].lower()]
    if filter_s != "All": filtered = [q for q in filtered if q["status"] == filter_s]
    
    if not filtered:
        st.info("No queries found matching the criteria.")
        return
        
    for q in reversed(filtered):
        with st.container(border=True):
            q_date = q.get("datetime", "Unknown")
            q_user = q.get("user", "Unknown")
            q_status = q.get("status", "Pending")
            q_text = q.get("text", "")
            q_reply = q.get("reply", "")
            badge = "bg-yellow-100 text-yellow-800" if q_status == "Pending" else "bg-green-100 text-green-800"
            
            st.markdown(f"**{q_user}** &middot; <span style='color:#64748b; font-size:0.85rem;'>{q_date}</span> &middot; **[{q_status}]**", unsafe_allow_html=True)
            st.markdown(f"<div style='margin-top:8px; padding:12px; background:#f8fafc; border-radius:8px; border-left: 4px solid #cbd5e1; font-size:1rem;'>{q_text}</div>", unsafe_allow_html=True)
            
            if q_status == "Pending":
                reply_input = st.text_area("Write your reply:", key=f"reply_input_{q['id']}")
                if st.button("Mark as Resolved & Send", key=f"btn_resolve_{q['id']}", type="primary"):
                    if reply_input.strip():
                        with st.spinner("Updating status..."):
                            for i, item in enumerate(queries):
                                if item["id"] == q["id"]:
                                    queries[i]["reply"] = reply_input
                                    queries[i]["status"] = "Resolved"
                                    break
                            save_queries(queries)
                            st.toast("Reply sent!", icon="✅")
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
        
    st.markdown("<h2 style='color:#0f172a; font-weight:800;'>⚙️ Admin Control Panel</h2>", unsafe_allow_html=True)
    st.write("---")
    
    with st.expander("📁 Question Bank Management", expanded=False):
        admin_bank = st.radio("Select Question Bank", ["Basic", "Advanced"], horizontal=True, key="admin_bank_radio")
        if st.session_state.get('last_admin_bank') != admin_bank:
            st.session_state.admin_current_path = ""
            st.session_state.last_admin_bank = admin_bank
        
        active_admin_base = CSV_FOLDER if admin_bank == "Basic" else ADVANCED_CSV_FOLDER
        current_admin_path = st.session_state.get('admin_current_path', '')
        full_admin_path = os.path.join(active_admin_base, current_admin_path.replace('/', os.sep))
        
        st.markdown(f"**Current Directory:** `Root / {current_admin_path.replace('/', ' / ')}`")
        
        c_up, c_newf, c_upld = st.columns(3)
        with c_up:
            if current_admin_path != '': st.button("⬅️ Back / Up", on_click=nav_admin_up, use_container_width=True)
        with c_newf:
            new_f = st.text_input("New Folder", key="new_f_input", label_visibility="collapsed", placeholder="Folder Name")
            if st.button("Create Folder", use_container_width=True):
                if new_f:
                    os.makedirs(os.path.join(full_admin_path, new_f), exist_ok=True)
                    st.toast(f"Created '{new_f}'", icon="✅")
                    st.rerun()
        with c_upld:
            uploaded_file = st.file_uploader("Upload CSV", type=['csv'], label_visibility="collapsed")
            if uploaded_file:
                with st.spinner("Uploading..."):
                    save_path = os.path.join(full_admin_path, uploaded_file.name)
                    with open(save_path, "wb") as f: f.write(uploaded_file.getbuffer())
                    st.toast("Uploaded!", icon="✅")
                    time.sleep(0.5)
                    st.rerun()
                
        st.write("---")
        items = sorted(os.listdir(full_admin_path)) if os.path.exists(full_admin_path) else []
        folders = [f for f in items if os.path.isdir(os.path.join(full_admin_path, f))]
        files = [f for f in items if f.endswith('.csv')]
        
        st.markdown("#### Folders")
        for folder in folders:
            with st.container(border=True):
                fc1, fc2, fc3, fc4 = st.columns([3, 4, 2, 2])
                fc1.button(f"📁 {folder}", key=f"nav_{current_admin_path}_{folder}", on_click=nav_admin_down, args=(folder,), use_container_width=True)
                if current_admin_path == "" and folder in ["Arts", "Computer", "Current affairs", "Science", "Statistics"]:
                    fc2.markdown("<div style='padding-top:10px; color:#94a3b8; font-size:12px; font-weight:bold;'>Protected</div>", unsafe_allow_html=True)
                else:
                    new_fn = fc2.text_input("Rename", value=folder, key=f"ren_fld_{current_admin_path}_{folder}", label_visibility="collapsed")
                    if fc3.button("✏️ Rename", key=f"rn_btn_{current_admin_path}_{folder}", use_container_width=True):
                        if new_fn and new_fn.strip() != folder:
                            try:
                                os.rename(os.path.join(full_admin_path, folder), os.path.join(full_admin_path, new_fn.strip()))
                                st.rerun()
                            except: pass
                    if fc4.button("🗑️ Delete", key=f"del_f_{current_admin_path}_{folder}", use_container_width=True):
                        try: os.rmdir(os.path.join(full_admin_path, folder)); st.rerun()
                        except: st.error("Folder not empty!")
                        
        st.write("---")
        st.markdown("#### Assessments")
        all_folders = ["Root"] + [os.path.relpath(os.path.join(r, d), active_admin_base).replace(os.sep, '/') for r, d, _ in os.walk(active_admin_base) for d in d]
        for f_name in files:
            file_p = os.path.join(full_admin_path, f_name)
            with st.container(border=True):
                c1, c2 = st.columns([8, 2])
                c1.markdown(f"📄 **{f_name}**")
                c2.markdown(f"<span style='color:#64748b;'>{os.path.getsize(file_p)/1024:.1f} KB</span>", unsafe_allow_html=True)
                mc1, mc2, mc3, mc4 = st.columns([3, 4, 2, 2])
                tgt = mc1.selectbox("Move", ["-- Select --"] + all_folders, key=f"mov_{current_admin_path}_{f_name}", label_visibility="collapsed")
                if tgt != "-- Select --":
                    dest = active_admin_base if tgt == "Root" else os.path.join(active_admin_base, tgt.replace('/', os.sep))
                    os.rename(file_p, os.path.join(dest, f_name))
                    st.rerun()
                new_fn = mc2.text_input("Rename", value=f_name, key=f"ren_f_{current_admin_path}_{f_name}", label_visibility="collapsed")
                if mc3.button("✏️ Rename", key=f"rn_fbtn_{current_admin_path}_{f_name}", use_container_width=True):
                    if new_fn and new_fn.strip() != f_name:
                        cn = new_fn.strip() if new_fn.strip().endswith('.csv') else new_fn.strip() + '.csv'
                        try: os.rename(file_p, os.path.join(full_admin_path, cn)); st.rerun()
                        except: pass
                if mc4.button("🗑️ Delete", key=f"del_{current_admin_path}_{f_name}", use_container_width=True):
                    os.remove(file_p); st.rerun()

    admin_file_options = {f"Basic | {f}": f for f in get_all_csv_files(CSV_FOLDER)}
    admin_file_options.update({f"Advanced | {f}": f"ADVANCED|{f}" for f in get_all_csv_files(ADVANCED_CSV_FOLDER)})

    with st.expander("⏱️ Timer Configuration", expanded=False):
        if admin_file_options:
            sel_display = st.selectbox("Select Assessment", list(admin_file_options.keys()), key="tmr_test")
            t_file = admin_file_options[sel_display]
            curr_set = load_timers_data().get(t_file, {"mode": "Total Time", "value": 30})
            new_mode = st.radio("Timing Rule", ["Total Time", "Per Question", "No Timer"], index=["Total Time", "Per Question", "No Timer"].index(curr_set["mode"]))
            new_val = st.number_input("Value", min_value=1, value=curr_set.get("value", 30)) if new_mode != "No Timer" else 0
            if st.button("Save Configuration", type="primary"):
                td = load_timers_data()
                td[t_file] = {"mode": new_mode, "value": new_val}
                save_timers_data(td)
                st.toast("Updated!", icon="✅")

    with st.expander("⚙️ Assessment Access Control", expanded=False):
        users = get_all_users()
        a_col1, a_col2 = st.columns(2)
        sel_user = a_col1.selectbox("Select Learner", list(users.keys()), key="adm_user")
        if admin_file_options:
            sel_test = admin_file_options[a_col2.selectbox("Select Assessment", list(admin_file_options.keys()), key="adm_test")]
            if sel_user and sel_test:
                new_limit = st.number_input("Attempts Limit", min_value=1, value=get_attempt_data(sel_user, sel_test)['allowed'])
                if st.button("Update Limit", type="primary"):
                    set_allowed_attempts(sel_user, sel_test, new_limit)
                    st.toast("Updated!", icon="✅")

    with st.expander("⚖️ Scoring & Penalty Configuration", expanded=False):
        if admin_file_options:
            nm_test_key = admin_file_options[st.selectbox("Select Assessment for Penalty", list(admin_file_options.keys()))]
            new_val = st.number_input("Penalty Value", min_value=0.0, max_value=0.33, value=float(get_neg_mark(nm_test_key)), step=0.01)
            if st.button("Apply Penalty Rule", type="primary"):
                set_neg_mark(nm_test_key, new_val)
                st.toast("Updated!", icon="✅")

    with st.expander("👥 User Management", expanded=False):
        users = get_all_users()
        t1, t2, t3 = st.tabs(["Add New", "Remove", "Reset Password"])
        with t1:
            new_u = st.text_input("New Username")
            new_p = st.text_input("Password", type="password")
            if st.button("Create Account", type="primary"):
                if new_u in users: st.error("Exists!")
                elif new_u and new_p: users[new_u] = new_p; save_users(users); st.rerun()
        with t2:
            del_u = st.selectbox("Account to Delete", [u for u in users if "Admin" not in u])
            cf_del = st.checkbox("Confirm deletion")
            if st.button("Delete Account", type="primary") and cf_del and del_u:
                del users[del_u]; save_users(users); st.rerun()
        with t3:
            ch_u = st.selectbox("Target Account", list(users.keys()))
            ch_p = st.text_input("New Secure Password", type="password")
            if st.button("Reset Password", type="primary") and ch_p:
                users[ch_u] = ch_p; save_users(users); st.toast("Reset!", icon="✅")

def render_dashboard_practice():
    st.markdown("""
    <div class="motivational-banner">
        <div class="banner-text">
            <h2>✨ Best of Luck for Your Exam! 🍀</h2>
            <p>Believe in yourself. Stay focused. Success comes to those who never stop learning.</p>
        </div>
        <div class="banner-emoji">🎯🚀</div>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("<h3 style='color:#0f172a; margin-bottom:15px;'>📋 Available Test Series</h3>", unsafe_allow_html=True)
    st.session_state.current_bank = st.radio("Question Bank", ["Basic", "Advanced"], horizontal=True, label_visibility="collapsed")
    
    active_base = CSV_FOLDER if st.session_state.current_bank == "Basic" else ADVANCED_CSV_FOLDER
    all_files = get_all_csv_files(active_base)
    
    search_q = st.text_input("🔍 Search Subject or Folder...", placeholder="e.g. Physics, Mock 1...").strip().lower()
    if search_q: files_to_disp = [f for f in all_files if search_q in f.lower()]
    else:
        c1, c2 = st.columns(2)
        root_flds = sorted([d for d in os.listdir(active_base) if os.path.isdir(os.path.join(active_base, d))])
        sel_cat = c1.selectbox("Category", root_flds) if root_flds else None
        if sel_cat:
            cat_p = os.path.join(active_base, sel_cat)
            sub_flds = sorted([d for d in os.listdir(cat_p) if os.path.isdir(os.path.join(cat_p, d))])
            sel_sub = c2.selectbox("Subcategory", ["All"] + sub_flds) if sub_flds else "All"
            prefix = sel_cat if sel_sub == "All" else f"{sel_cat}/{sel_sub}"
            files_to_disp = [f for f in all_files if f.startswith(prefix)]
        else: files_to_disp = []

    st.write("<br>", unsafe_allow_html=True)
    if not files_to_disp: st.info("No assessments found matching criteria.")
    else:
        for f in files_to_disp:
            with st.container(border=True):
                test_k = f if st.session_state.current_bank == "Basic" else f"ADVANCED|{f}"
                att_data = get_attempt_data(st.session_state.current_user, test_k)
                used, allowed = att_data['used'], att_data['allowed']
                c1, c2 = st.columns([3, 1])
                c1.markdown(f"<h4 style='margin:0; font-weight:700; color:#1e293b;'>📄 {os.path.basename(f)[:-4]}</h4>", unsafe_allow_html=True)
                c1.markdown(f"<span style='font-size:0.85rem; color:#64748b; font-weight:600;'>📁 {(os.path.dirname(f) or 'Root').replace('/',' / ')} &middot; Attempts: {used}/{allowed}</span>", unsafe_allow_html=True)
                if allowed - used > 0:
                    if c2.button("Start Assessment", key=f"ld_{test_k}", type="primary", use_container_width=True):
                        with st.spinner("Configuring Engine..."): time.sleep(0.3); load_quiz(f); st.rerun()
                else:
                    c2.button("Limit Reached", key=f"lm_{test_k}", disabled=True, use_container_width=True)

def render_dashboard_performance():
    st.markdown("<h2 style='color:#0f172a; font-weight:800;'>📈 Performance Analytics</h2>", unsafe_allow_html=True)
    st.write("---")
    history = load_history().get(st.session_state.current_user, [])
    
    if not history:
        st.info("No test history found. Complete an assessment to generate your analytics dashboard.")
        return
        
    scores = [h['final_score'] for h in history]
    accs = [round((h['correct']/h['attempted']*100),1) if h['attempted']>0 else 0 for h in history]
    total_q = sum(h['attempted'] for h in history)
    total_corr = sum(h['correct'] for h in history)
    
    c1, c2, c3, c4 = st.columns(4)
    with c1: st.markdown(f"<div class='metric-card metric-blue'><span>Total Tests</span><strong>{len(history)}</strong></div>", unsafe_allow_html=True)
    with c2: st.markdown(f"<div class='metric-card metric-green'><span>Avg Score</span><strong>{sum(scores)/len(scores):.1f}</strong></div>", unsafe_allow_html=True)
    with c3: st.markdown(f"<div class='metric-card metric-purple'><span>Highest Score</span><strong>{max(scores):.2f}</strong></div>", unsafe_allow_html=True)
    with c4: st.markdown(f"<div class='metric-card metric-amber'><span>Global Accuracy</span><strong>{(total_corr/total_q*100) if total_q>0 else 0:.1f}%</strong></div>", unsafe_allow_html=True)
    
    st.write("<br>", unsafe_allow_html=True)
    ch_c1, ch_c2 = st.columns(2)
    with ch_c1:
        st.markdown("**Score Trend**")
        st.line_chart(scores, height=200)
    with ch_c2:
        st.markdown("**Accuracy Trend (%)**")
        st.line_chart(accs, height=200)
        
    st.markdown("#### 📜 Recent Test History")
    for i, att in enumerate(reversed(history)):
        real_idx = len(history) - 1 - i
        with st.container(border=True):
            r1, r2, r3, r4 = st.columns([3, 2, 2, 2])
            r1.markdown(f"**{att['test_name']}**<br><span style='font-size:0.8rem; color:#64748b;'>{att['datetime']}</span>", unsafe_allow_html=True)
            r2.markdown(f"**Score:** {att['final_score']:.2f}")
            r3.markdown(f"**Accuracy:** {accs[real_idx]}%")
            if r4.button("View Full Report", key=f"rpt_{real_idx}"):
                st.session_state.history_view_index = real_idx
                st.session_state.active_page = "Result"
                st.rerun()

def render_dashboard_ask_query():
    st.markdown("<h2 style='color:#0f172a; font-weight:800;'>💬 Support & Doubts</h2>", unsafe_allow_html=True)
    st.markdown("<p style='color:#64748b;'>Submit technical or academic queries directly to the platform administrators.</p>", unsafe_allow_html=True)
    st.write("---")
    
    with st.container(border=True):
        st.markdown("#### Submit a New Query")
        query_text = st.text_area("Describe your doubt clearly:", placeholder="E.g., Clarification needed on Modern Physics Question 4...", height=120)
        wc = len(re.findall(r'\w+', query_text))
        st.caption(f"Word limit: 100 words. (Current: {wc})")
        if st.button("Submit Secure Query", type="primary"):
            if wc == 0: st.warning("Query cannot be empty.")
            elif wc > 100: st.error("Limit exceeded.")
            else:
                with st.spinner("Encrypting and submitting..."):
                    qs = load_queries()
                    qs.append({
                        "id": str(uuid.uuid4()), "user": st.session_state.current_user,
                        "datetime": time.strftime("%Y-%m-%d %H:%M:%S"), "text": query_text,
                        "status": "Pending", "reply": ""
                    })
                    save_queries(qs)
                    st.toast("Submitted!", icon="✅")
                    time.sleep(0.5)
                    st.rerun()
                    
    st.markdown("#### Your Query History")
    my_qs = [q for q in load_queries() if q["user"] == st.session_state.current_user]
    if not my_qs: st.info("No queries found.")
    else:
        for q in reversed(my_qs):
            with st.container(border=True):
                stat = q.get("status", "Pending")
                b_cls = "bg-yellow-100 text-yellow-800" if stat == "Pending" else "bg-green-100 text-green-800"
                st.markdown(f"<span style='color:#64748b; font-size:0.85rem;'>{q.get('datetime')}</span> &middot; **[{stat}]**", unsafe_allow_html=True)
                st.markdown(f"<div style='margin-top:5px; font-weight:600;'>{q.get('text')}</div>", unsafe_allow_html=True)
                if stat == "Resolved" and q.get("reply"):
                    st.markdown(f"<div style='margin-top:10px; padding:10px; background:#f0fdf4; border-left:4px solid #16a34a; border-radius:6px;'>**Admin:** {q.get('reply')}</div>", unsafe_allow_html=True)

def render_dashboard():
    # Native Streamlit tabs cannot be reliably driven by sidebar without complex hacks, so manual routing is robust.
    tab = st.session_state.get('dashboard_tab', 'Practice')
    if tab == "Practice": render_dashboard_practice()
    elif tab == "Performance": render_dashboard_performance()
    elif tab == "Ask Query": render_dashboard_ask_query()

    if st.session_state.quiz_ready:
        st.divider()
        col_space1, col_start, col_space2 = st.columns([1, 2, 1])
        with col_start:
            if st.button("🚀 Proceed to Instructions", type="primary", use_container_width=True):
                with st.spinner("Preparing secure exam environment..."):
                    st.session_state.active_page = "Instructions"
                    time.sleep(0.4)
                    st.rerun()

def render_instructions():
    render_page_header("Important Instructions", st.session_state.topic, "Before you begin")
    col1, col2, col3 = st.columns([1, 4, 1])
    with col2:
        with st.container(border=True):
            st.markdown("### Assessment Guidelines")
            st.markdown(f"🔹 **Total Questions:** {len(st.session_state.questions)}")
            st.markdown(f"🔹 **Time Limit:** {st.session_state.time_val} Min" if st.session_state.timer_mode != "No Timer" else "🔹 **Time Limit:** None")
            nm = get_neg_mark(st.session_state.current_test_filename)
            if nm > 0: st.markdown(f"🔹 **Penalty:** -{nm} marks per incorrect answer.")
            st.markdown("""
            🔹 **Navigation:** Jump to any question using the Palette.
            🔹 **Auto-Pause:** Exam freezes automatically after 5 minutes of total inactivity.
            🔹 **Submission:** Auto-submits precisely when the timer hits zero.
            """)
            st.write("<br>", unsafe_allow_html=True)
            if st.button("✅ I understand. Begin Exam.", type="primary", use_container_width=True):
                with st.spinner("Initializing engine..."):
                    now = time.time()
                    st.session_state.last_calc_time = st.session_state.last_interaction_time = now
                    st.session_state.is_paused = False
                    st.session_state.active_page = "Exam"
                    time.sleep(0.4)
                    st.rerun()

def render_paused_screen():
    st.write("<br><br>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        with st.container(border=True):
            st.markdown("<h1 style='text-align: center; color: #dc2626;'>⏸ Session Paused</h1>", unsafe_allow_html=True)
            st.markdown("<p style='text-align: center; color: #475569;'>Your timer is frozen and progress cached securely.</p>", unsafe_allow_html=True)
            st.write("---")
            if st.button("▶️ Resume Assessment", type="primary", use_container_width=True):
                with st.spinner("Resuming..."):
                    now = time.time()
                    st.session_state.last_calc_time = st.session_state.last_interaction_time = now
                    st.session_state.is_paused = False
                    time.sleep(0.3)
                    st.rerun()

def render_exam():
    if st.session_state.is_paused: return render_paused_screen()

    q_idx = st.session_state.current_q
    st.session_state.visited_questions.add(q_idx)
    total_q = len(st.session_state.questions)
    q_data = st.session_state.questions[q_idx]

    col_main, col_pal = st.columns([7, 3]) 
    
    ans_count = sum(1 for i in range(total_q) if st.session_state.user_answers.get(i) is not None and i not in st.session_state.marked_questions)
    ans_marked_count = sum(1 for i in range(total_q) if st.session_state.user_answers.get(i) is not None and i in st.session_state.marked_questions)
    marked_count = sum(1 for i in range(total_q) if st.session_state.user_answers.get(i) is None and i in st.session_state.marked_questions)
    not_ans_count = sum(1 for i in range(total_q) if st.session_state.user_answers.get(i) is None and i in st.session_state.visited_questions and i not in st.session_state.marked_questions)
    not_visit_count = total_q - (ans_count + ans_marked_count + marked_count + not_ans_count)
            
    with col_pal:
        st.markdown("<p class='palette-title'>Exam Controls & Timer</p>", unsafe_allow_html=True)
        render_visual_timer()
        st.write("<div style='margin-top:10px;'></div>", unsafe_allow_html=True)
        st.button("⏸ Pause Exam", type="secondary", on_click=pause_exam, use_container_width=True)
        
        udisp = st.session_state.current_user.split()[0]
        html_legend = f"""
        <div style="background:#fff; padding:15px; border:1px solid #e2e8f0; border-radius:12px; margin:15px 0; box-shadow:0 4px 6px -1px rgba(0,0,0,0.03);">
        <div style="display:flex; align-items:center; gap:10px; margin-bottom:15px;">
        <div style="width:34px; height:34px; background:linear-gradient(135deg, #4f46e5, #6366f1); color:white; border-radius:50%; display:flex; justify-content:center; align-items:center; font-weight:bold;">{udisp[0].upper()}</div>
        <span style="font-weight:700; color:#0f172a; font-size:15px;">{udisp}'s Session</span>
        </div>
        <div style="display:grid; grid-template-columns:1fr 1fr; gap:10px 8px; font-size:11px; color:#475569;">
        <div style="display:flex; align-items:center; gap:6px;"><div style="width:20px; height:20px; background:#16a34a; color:white; border-radius:6px 6px 0 0; display:flex; align-items:center; justify-content:center; font-weight:bold;">{ans_count}</div><span style="font-weight:600;">Answered</span></div>
        <div style="display:flex; align-items:center; gap:6px;"><div style="width:20px; height:20px; background:#7c3aed; color:white; border-radius:50%; display:flex; align-items:center; justify-content:center; font-weight:bold;">{marked_count}</div><span style="font-weight:600;">Marked</span></div>
        <div style="display:flex; align-items:center; gap:6px;"><div style="width:20px; height:20px; background:#fff; border:1px solid #cbd5e1; color:#334155; border-radius:6px; display:flex; align-items:center; justify-content:center; font-weight:bold;">{not_visit_count}</div><span style="font-weight:600;">Not Visited</span></div>
        <div style="display:flex; align-items:center; gap:6px;"><div style="width:20px; height:20px; background:#ef4444; color:white; border-radius:0 0 6px 6px; display:flex; align-items:center; justify-content:center; font-weight:bold;">{not_ans_count}</div><span style="font-weight:600;">Not Answered</span></div>
        <div style="display:flex; align-items:center; gap:6px; grid-column:span 2;"><div style="width:20px; height:20px; background:#7c3aed; color:white; border-radius:50%; display:flex; align-items:center; justify-content:center; font-weight:bold; position:relative;">{ans_marked_count}<div style="position:absolute; bottom:-2px; right:-2px; width:8px; height:8px; background:#16a34a; border-radius:50%; border:1px solid white;"></div></div><span style="font-weight:600;">Marked and Answered</span></div>
        </div></div>"""
        st.markdown(html_legend, unsafe_allow_html=True)
        st.markdown(f"<div style='background:linear-gradient(90deg, #eff6ff, #dbeafe); padding:10px; font-weight:800; color:#1e40af; font-size:11px; text-transform:uppercase; border-radius:8px; margin-bottom:12px; text-align:center;'>SECTION: {st.session_state.topic}</div>", unsafe_allow_html=True)

        with st.expander("System Engine", expanded=False):
            st.markdown("<div id='hidden-engine-marker'></div>", unsafe_allow_html=True)
            for i in range(total_q): st.button(f"HBTN_{i}", key=f"hbtn_{i}", on_click=nav_goto, args=(i,))

        grid_html = ""
        for i in range(total_q):
            is_ans = st.session_state.user_answers.get(i) is not None
            is_vis = i in st.session_state.visited_questions
            is_mark = i in st.session_state.marked_questions
            cls = ["q-btn", "current" if i==q_idx else "", "answeredmarked" if is_ans and is_mark else "answered" if is_ans else "marked" if is_mark else "notanswered" if is_vis else "notvisited"]
            grid_html += f'<div class="{" ".join(cls)}" data-idx="{i}" role="button" tabindex="0">{i+1}</div>\n'
            
        full_html = f"""<!DOCTYPE html><html><head><style>
        body {{ margin:0; padding:0; font-family:Inter,sans-serif; }}
        .palette-grid {{ display:grid; grid-template-columns:repeat(5, 1fr); gap:10px; padding:5px; }}
        .q-btn {{ aspect-ratio:1/1; display:flex; align-items:center; justify-content:center; font-size:13px; font-weight:750; cursor:pointer; border-radius:8px; border:1px solid #cbd5e1; user-select:none; transition:all 0.2s; }}
        .q-btn:hover {{ transform:translateY(-2px); box-shadow:0 4px 8px rgba(0,0,0,0.1); }}
        .notvisited {{ background:#fff; color:#334155; }}
        .notanswered {{ background:#ef4444; color:#fff; border-color:#ef4444; border-radius:0 0 12px 12px; }}
        .answered {{ background:#16a34a; color:#fff; border-color:#16a34a; border-radius:12px 12px 0 0; }}
        .marked {{ background:#7c3aed; color:#fff; border-color:#7c3aed; border-radius:50%; }}
        .answeredmarked {{ background:#7c3aed; color:#fff; border-color:#7c3aed; border-radius:50%; position:relative; overflow:visible; }}
        .answeredmarked::after {{ content:''; position:absolute; bottom:-3px; right:-3px; width:10px; height:10px; background:#16a34a; border-radius:50%; border:2px solid white; }}
        .current {{ outline:3px solid #2563eb; outline-offset:2px; transform:scale(1.05); z-index:2; }}
        </style></head><body><div class="palette-grid">{grid_html}</div>
        <script>
        function mapAndHide() {{ try {{
            const pDoc = window.parent.document;
            const m = pDoc.getElementById('hidden-engine-marker');
            if(m) {{ const d=m.closest('details'); if(d)d.style.display='none'; const e=m.closest('div[data-testid="stExpander"]'); if(e)e.style.display='none'; }}
            pDoc.querySelectorAll('button').forEach(b => {{ if(b.innerText&&b.innerText.includes('HBTN_')) window.hiddenMap[b.innerText.split('_')[1].trim()] = b; }});
        }}catch(e){{}} }}
        window.hiddenMap = {{}};
        document.addEventListener("DOMContentLoaded", function() {{
            mapAndHide(); setTimeout(mapAndHide, 50); setTimeout(mapAndHide, 200);
            document.querySelectorAll('.q-btn').forEach(i => {{
                i.addEventListener('click', function() {{ let id=this.getAttribute('data-idx'); if(window.hiddenMap[id]) window.hiddenMap[id].click(); else {{mapAndHide(); if(window.hiddenMap[id])window.hiddenMap[id].click();}} }});
            }});
        }});
        </script></body></html>"""
        components.html(full_html, height=360, scrolling=True)

        st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)
        b1, b2 = st.columns(2)
        b1.button("Question Paper", use_container_width=True)
        b2.button("Instructions", use_container_width=True)
        st.write("<br>", unsafe_allow_html=True)
        if st.button("🚀 Final Submit", type="primary", use_container_width=True):
            with st.spinner("Submitting responses securely..."):
                time.sleep(0.5); nav_submit(); st.rerun()

    with col_main:
        st.markdown(f"<p class='exam-kicker'>Live Assessment &middot; {st.session_state.topic}</p>", unsafe_allow_html=True)
        st.progress((q_idx + 1) / total_q)
        
        raw_q = q_data['q']
        clean_q = re.sub(r'^[Qq]?(?:uestion)?\s*\d+[\.\)]\s*', '', raw_q)
        st.markdown(f"""
            <section class="question-card">
                <span class="question-card__number">Question {q_idx + 1} of {total_q}</span>
                <p class="question-card__text">{clean_q}</p>
            </section>
            """, unsafe_allow_html=True)
        
        if q_data.get('type') == 'match':
            saved_ans = st.session_state.user_answers.get(q_idx, {})
            m_col1, m_col2 = st.columns(2)
            m_col1.markdown("<div style='color:#64748b; font-weight:800; font-size:0.85rem; text-transform:uppercase; border-bottom:2px solid #e2e8f0; padding-bottom:8px;'>Column A (Fixed)</div>", unsafe_allow_html=True)
            m_col2.markdown("<div style='color:#64748b; font-weight:800; font-size:0.85rem; text-transform:uppercase; border-bottom:2px solid #e2e8f0; padding-bottom:8px;'>Column B (Select Target)</div>", unsafe_allow_html=True)
            for l_item in q_data['left']:
                r_c1, r_c2 = st.columns(2)
                r_c1.markdown(f"<div style='padding-top:10px; font-weight:650; font-size:1.1rem; color:#0f172a;'>{l_item}</div>", unsafe_allow_html=True)
                opts = ["-- Select Option --"] + q_data['options']
                idx = opts.index(saved_ans.get(l_item, "-- Select Option --")) if saved_ans.get(l_item) in opts else 0
                r_c2.selectbox("Match Target", opts, index=idx, key=f"match_{q_idx}_{l_item}", on_change=on_match_change, args=(q_idx, q_data['left']), label_visibility="collapsed")
        else:
            saved_ans = st.session_state.user_answers.get(q_idx)
            idx = q_data['options'].index(saved_ans) if saved_ans in q_data['options'] else None
            st.radio("Options:", options=q_data['options'], index=idx, key=f"radio_ans_{q_idx}", on_change=on_radio_change, args=(q_idx,), label_visibility="collapsed")
            
        st.write("<br><br>", unsafe_allow_html=True)
        b_col1, b_col2, b_col3, b_col4 = st.columns([1.5, 1.5, 2.5, 1.5])
        b_col1.button("⏪ Previous", on_click=nav_prev, use_container_width=True)
        b_col2.button("🧹 Clear", on_click=clear_answer, args=(q_idx,), use_container_width=True)
        is_cur_marked = q_idx in st.session_state.marked_questions
        b_col3.button("🚩 Unmark" if is_cur_marked else "🚩 Mark for Review", on_click=toggle_mark, args=(q_idx,), use_container_width=True)
        if q_idx == total_q - 1: b_col4.button("Finish", disabled=True, use_container_width=True)
        else: b_col4.button("Next ⏩", type="primary", on_click=nav_next, use_container_width=True)

def render_result():
    history = load_history().get(st.session_state.current_user, [])
    if not history:
        st.info("No result data available.")
        return
        
    idx = st.session_state.get('history_view_index', -1)
    if idx == -1 or idx >= len(history): idx = len(history) - 1
    
    att = history[idx]
    total_q = att['total_questions']
    
    # Navigation controls (Feature 4 requirement)
    col1, col2, col3 = st.columns([1, 2, 1])
    with col1:
        if st.button("← Previous Test", disabled=(idx == 0), use_container_width=True):
            st.session_state.history_view_index = idx - 1
            st.rerun()
    with col3:
        if st.button("Next Test →", disabled=(idx == len(history)-1), use_container_width=True):
            st.session_state.history_view_index = idx + 1
            st.rerun()
            
    render_page_header("Performance Analysis", f"{att['test_name']} &middot; Attempted on {att['datetime']}", "Report generated")

    c1, c2, c3, c4 = st.columns(4)
    with c1: render_metric_card("Final score", f"{att['final_score']:.2f}", "blue", f"Out of {total_q}")
    with c2: render_metric_card("Percentage", f"{att['percentage']:.2f}%", "purple", "Based on final score")
    with c3: render_metric_card("Accuracy", f"{round((att['correct'] / att['attempted'] * 100) if att['attempted'] > 0 else 0, 1)}%", "green", "Correct out of attempted")
    with c4: render_metric_card("Attempted", f"{att['attempted']} / {total_q}", "amber", f"{att['unanswered']} unattempted")

    st.write("<br>", unsafe_allow_html=True)
    c5, c6, c7, c8 = st.columns(4)
    with c5: render_metric_card("Correct", str(att['correct']), "green", "Answers validated correct")
    with c6: render_metric_card("Incorrect", str(att['incorrect']), "red", "Answers marked incorrect")
    with c7: render_metric_card("Unattempted", str(att['unanswered']), "amber", "Questions left blank")
    with c8: render_metric_card("Negative marks", f"-{att['negative_marks']:.2f}", "red", "Penalty applied")

    st.write("<br><br>", unsafe_allow_html=True)
    st.markdown("### 📋 Detailed Answer Key")
    
    with st.expander("Review Complete Answer Breakdown", expanded=False):
        for qd in att['q_details']:
            card_class = "res-correct" if qd['status'] == "Correct" else "res-incorrect" if qd['status'] == "Incorrect" else "res-unanswered"
            st.markdown(f"<div class='metric-card {card_class}' style='margin-bottom:1rem; min-height:auto; padding:1.2rem;'>", unsafe_allow_html=True)
            st.markdown(f"<div style='font-size:1.15rem; font-weight:700; color:#0f172a; margin-bottom:8px;'>Q{qd['q_num']}: {qd['question']}</div>", unsafe_allow_html=True)
            
            c_a, c_b = st.columns(2)
            c_a.markdown(f"<span style='color:#64748b; font-size:0.8rem; font-weight:700; text-transform:uppercase;'>Your Selection</span>", unsafe_allow_html=True)
            if qd['status'] == "Unanswered":
                c_a.warning("Not Attempted")
            elif qd['status'] == "Incorrect":
                c_a.error(qd['user_ans'])
            else:
                c_a.success(qd['user_ans'])
                
            c_b.markdown(f"<span style='color:#64748b; font-size:0.8rem; font-weight:700; text-transform:uppercase;'>Correct Engine Answer</span>", unsafe_allow_html=True)
            c_b.info(qd['correct_ans'])
            
            st.markdown(f"<div style='margin-top:10px; font-size:0.85rem; color:#475569; font-weight:600;'>Validation: <span style='color:{'#16a34a' if qd['status']=='Correct' else '#dc2626' if qd['status']=='Incorrect' else '#d97706'}'>{qd['status']}</span> &middot; Marks: {qd['marks']} &middot; Penalty: -{qd['negative']:.2f}</div></div>", unsafe_allow_html=True)

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
        
        if st.session_state.active_page == "Dashboard": render_dashboard()
        elif st.session_state.active_page == "Admin": render_admin()
        elif st.session_state.active_page == "UserQueries": render_user_queries()
        elif st.session_state.active_page == "Instructions": render_instructions()
        elif st.session_state.active_page == "Exam": render_exam()
        elif st.session_state.active_page == "Result": render_result()

    if st.session_state.get("auth") and st.session_state.get("sid"):
        try:
            session_path = os.path.join(SESSION_FOLDER, f"{st.session_state.sid}.pkl")
            safe_keys = ['auth', 'current_user', 'questions', 'current_q', 'user_answers', 'visited_questions', 'marked_questions', 'quiz_ready', 'topic', 'timer_mode', 'time_val', 'remaining_seconds', 'last_calc_time', 'last_interaction_time', 'active_page', 'dashboard_tab', 'is_paused', 'current_test_filename', 'attempt_recorded', 'admin_current_path', 'sid', 'current_bank', 'last_admin_bank', 'history_view_index']
            with open(session_path, "wb") as f: pickle.dump({k: st.session_state[k] for k in safe_keys if k in st.session_state}, f)
        except: pass

if __name__ == "__main__":
    main()
