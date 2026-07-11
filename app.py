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
import math
import io
import logging
from supabase import create_client, Client

# Configure logging for production-safe error tracking
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ==========================================
# 0. DATABASE CONNECTION SETUP
# ==========================================
@st.cache_resource(show_spinner=False)
def init_connection():
    # Fetch credentials from Streamlit secrets
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase: Client = init_connection()

# ==========================================
# 1. CONFIGURATION & CONSTANTS
# ==========================================
st.set_page_config(
    page_title="Study Booster | Premium CBT", 
    page_icon="🎓", 
    layout="wide", 
    initial_sidebar_state="expanded"
)

# Initialize Session Folder for Pause/Resume Persistence only
SESSION_FOLDER = 'active_sessions'
if not os.path.exists(SESSION_FOLDER):
    os.makedirs(SESSION_FOLDER)

# Feature 4: Restructure Question Bank Management (Basic & Advanced)
CSV_FOLDER = 'saved_csvs'
ADVANCED_CSV_FOLDER = 'advanced_csvs'

if not os.path.exists(CSV_FOLDER): 
    os.makedirs(CSV_FOLDER)

if not os.path.exists(ADVANCED_CSV_FOLDER):
    os.makedirs(ADVANCED_CSV_FOLDER)

# Cloud Default Category Structure
DEFAULT_STRUCTURE = {
    "Science": ["Physics", "Chemistry", "Biology", "Environment"],
    "Arts": ["History", "Polity", "Geography", "Economics"],
    "Statistics": [],
    "Current affairs": []
}

# Ensure Local Physical Folders exist
for base_folder in [CSV_FOLDER, ADVANCED_CSV_FOLDER]:
    for root_cat, sub_cats in DEFAULT_STRUCTURE.items():
        root_path = os.path.join(base_folder, root_cat)
        os.makedirs(root_path, exist_ok=True)
        for sub_cat in sub_cats:
            os.makedirs(os.path.join(root_path, sub_cat), exist_ok=True)

# ==========================================
# DATA MANAGEMENT FUNCTIONS (CLOUD OPTIMIZED)
# ==========================================

def check_and_create_default_folders():
    """Automatically seeds Supabase with the default folder structure if missing."""
    if st.session_state.get('folders_checked', False):
        return
        
    try:
        # Check if the table is completely empty to prevent recreating defaults if renamed
        res = supabase.table('question_banks').select('id').limit(1).execute()
        if not res.data:
            # If completely empty, generate all default folders for both banks
            for bank_type in ["Basic", "Advanced"]:
                for root_cat, sub_cats in DEFAULT_STRUCTURE.items():
                    supabase.table('question_banks').insert({
                        'bank_type': bank_type, 
                        'folder_path': root_cat, 
                        'file_name': '.keep', 
                        'csv_data': ''
                    }).execute()
                    for sub_cat in sub_cats:
                        supabase.table('question_banks').insert({
                            'bank_type': bank_type, 
                            'folder_path': f"{root_cat}/{sub_cat}", 
                            'file_name': '.keep', 
                            'csv_data': ''
                        }).execute()
        st.session_state.folders_checked = True
    except Exception as e:
        st.error(f"⚠️ Supabase Folder Generation Error: {e} (Hint: Check if RLS is disabled on 'question_banks' table!)")

@st.cache_data(show_spinner=False, ttl=300)
def get_all_users_cached():
    try:
        response = supabase.table('users').select("username, password").execute()
        users_dict = {row['username']: row['password'] for row in response.data}
        
        # FIX: Master Admin ko hamesha list mein rakhein taaki aap kabhi lock out na hon
        if "Jitendra (Admin)" not in users_dict:
            users_dict["Jitendra (Admin)"] = "Admin@1996"
            
        return users_dict
    except Exception as e:
        logger.error(f"Database Connection Error fetching users: {e}")
        return {"Jitendra (Admin)": "Admin@1996"}

def get_all_users():
    return get_all_users_cached()

def add_new_user_to_db(username, password):
    try:
        supabase.table('users').insert({"username": username, "password": password, "role": "Student"}).execute()
        get_all_users_cached.clear()
        return True
    except Exception as e:
        logger.error(f"Error adding user: {e}")
        st.error(f"Error adding user: {e}")
        return False

def delete_user_from_db(username):
    try:
        supabase.table('users').delete().eq('username', username).execute()
        get_all_users_cached.clear()
        return True
    except Exception as e:
        logger.error(f"Error deleting user: {e}")
        return False

# --- SMART CACHING FOR CLOUD HISTORY ---
@st.cache_data(show_spinner=False, ttl=300)
def get_supabase_history_cached(username):
    """Fetches test history from Supabase for a specific user"""
    try:
        response = supabase.table('exam_history').select("*").eq('username', username).execute()
        history = []
        
        # Sort by datetime sequentially to match graph progression logic
        sorted_data = sorted(response.data, key=lambda x: x.get('datetime', ''))

        for row in sorted_data:
            q_details = row.get('q_details', [])
            if isinstance(q_details, str):
                try: q_details = json.loads(q_details)
                except: q_details = []
            
            attempt_data = {
                "test_name": row.get('test_name', 'Unknown'),
                "subject": row.get('subject', 'Unknown'),
                "folder": row.get('folder', 'Root'),
                "attempt_number": row.get('attempt_number', 1),
                "datetime": row.get('datetime', ''), 
                "total_questions": row.get('total_questions', 0),
                "attempted": row.get('total_questions', 0) - row.get('unanswered', 0),
                "correct": row.get('correct', 0),
                "incorrect": row.get('incorrect', 0),
                "unanswered": row.get('unanswered', 0),
                "marks_obtained": row.get('correct', 0),
                "negative_marks": row.get('negative_marks', 0.0),
                "final_score": row.get('final_score', 0.0),
                "percentage": row.get('percentage', 0.0),
                "q_details": q_details
            }
            history.append(attempt_data)
        return history
    except Exception as e:
        logger.error(f"Error fetching history from Supabase: {e}")
        return []

def get_supabase_history(username):
    return get_supabase_history_cached(username)

@st.cache_data(show_spinner=False, ttl=300)
def get_all_supabase_history_cached():
    """Fetches all test histories from Supabase for Admin reporting"""
    try:
        response = supabase.table('exam_history').select("*").execute()
        history_dict = {}
        sorted_data = sorted(response.data, key=lambda x: x.get('datetime', ''))
        
        for row in sorted_data:
            username = row.get('username')
            if not username: continue
            if username not in history_dict:
                history_dict[username] = []
            
            q_details = row.get('q_details', [])
            if isinstance(q_details, str):
                try: q_details = json.loads(q_details)
                except: q_details = []
            
            attempt_data = {
                "test_name": row.get('test_name', 'Unknown'),
                "subject": row.get('subject', 'Unknown'),
                "folder": row.get('folder', 'Root'),
                "attempt_number": row.get('attempt_number', 1),
                "datetime": row.get('datetime', ''),
                "total_questions": row.get('total_questions', 0),
                "attempted": row.get('total_questions', 0) - row.get('unanswered', 0),
                "correct": row.get('correct', 0),
                "incorrect": row.get('incorrect', 0),
                "unanswered": row.get('unanswered', 0),
                "marks_obtained": row.get('correct', 0),
                "negative_marks": row.get('negative_marks', 0.0),
                "final_score": row.get('final_score', 0.0),
                "percentage": row.get('percentage', 0.0),
                "q_details": q_details
            }
            history_dict[username].append(attempt_data)
        return history_dict
    except Exception as e:
        logger.error(f"Error fetching all history from Supabase: {e}")
        return {}

def get_all_supabase_history():
    return get_all_supabase_history_cached()

# --- CLOUD SETTINGS FUNCTIONS (Penalties, Timers, Attempts) ---

@st.cache_data(show_spinner=False, ttl=600)
def get_neg_mark_cached(test_key):
    try:
        res = supabase.table('test_penalties').select('penalty').eq('test_file', test_key).execute()
        if res.data: return float(res.data[0]['penalty'])
    except Exception as e: logger.error(f"DB Error getting neg mark: {e}")
    return 0.0

def get_neg_mark(test_key):
    return get_neg_mark_cached(test_key)

def set_neg_mark(test_key, value):
    try:
        res = supabase.table('test_penalties').select('id').eq('test_file', test_key).execute()
        if res.data:
            supabase.table('test_penalties').update({'penalty': float(value)}).eq('id', res.data[0]['id']).execute()
        else:
            supabase.table('test_penalties').insert({'test_file': test_key, 'penalty': float(value)}).execute()
        get_neg_mark_cached.clear(test_key)
    except Exception as e: 
        logger.error(f"Error setting neg mark: {e}")

@st.cache_data(show_spinner=False, ttl=600)
def get_timer_config_cached(test_key):
    try:
        res = supabase.table('test_timers').select('mode, value').eq('test_file', test_key).execute()
        if res.data:
            return {"mode": res.data[0]['mode'], "value": res.data[0]['value']}
    except Exception as e: logger.error(f"DB Error getting timer config: {e}")
    return {"mode": "Total Time", "value": 30}

def get_timer_config(test_key):
    return get_timer_config_cached(test_key)

def set_timer_config(test_key, mode, value):
    try:
        res = supabase.table('test_timers').select('id').eq('test_file', test_key).execute()
        if res.data:
            supabase.table('test_timers').update({'mode': mode, 'value': value}).eq('id', res.data[0]['id']).execute()
        else:
            supabase.table('test_timers').insert({'test_file': test_key, 'mode': mode, 'value': value}).execute()
        get_timer_config_cached.clear(test_key)
    except Exception as e:
        logger.error(f"Error setting timer: {e}")

# Resolves N+1 query issue for attempts on the Dashboard
@st.cache_data(show_spinner=False, ttl=120)
def get_user_attempts_map(username):
    """Fetches all attempts for a user efficiently in a single query."""
    try:
        res = supabase.table('user_attempts').select('test_file, allowed, used').eq('username', username).execute()
        return {row['test_file']: {'allowed': row['allowed'], 'used': row['used']} for row in res.data}
    except Exception as e:
        logger.error(f"Error fetching attempts map: {e}")
        return {}

def get_attempt_data(user, test_file):
    attempts_map = get_user_attempts_map(user)
    return attempts_map.get(test_file, {'allowed': 5, 'used': 0})

def increment_attempt(user, test_file):
    curr = get_attempt_data(user, test_file)
    try:
        res = supabase.table('user_attempts').select('id').eq('username', user).eq('test_file', test_file).execute()
        if res.data:
            supabase.table('user_attempts').update({'used': curr['used'] + 1}).eq('id', res.data[0]['id']).execute()
        else:
            supabase.table('user_attempts').insert({'username': user, 'test_file': test_file, 'allowed': curr['allowed'], 'used': curr['used'] + 1}).execute()
        get_user_attempts_map.clear(user)
    except Exception as e:
        logger.error(f"Error incrementing attempt: {e}")

def set_allowed_attempts(user, test_file, allowed_count):
    curr = get_attempt_data(user, test_file)
    try:
        res = supabase.table('user_attempts').select('id').eq('username', user).eq('test_file', test_file).execute()
        if res.data:
            supabase.table('user_attempts').update({'allowed': allowed_count}).eq('id', res.data[0]['id']).execute()
        else:
            supabase.table('user_attempts').insert({'username': user, 'test_file': test_file, 'allowed': allowed_count, 'used': curr['used']}).execute()
        get_user_attempts_map.clear(user)
    except Exception as e:
        logger.error(f"Error setting allowed attempts: {e}")

# --- CLOUD CSV QUESTION BANK FUNCTIONS ---
@st.cache_data(show_spinner=False, ttl=300)
def get_cloud_hierarchy_cached(bank_type):
    """Returns a list of unique folders and a list of file paths from Supabase"""
    try:
        res = supabase.table('question_banks').select('folder_path, file_name').eq('bank_type', bank_type).execute()
        folders = set()
        files = []
        for r in res.data:
            fp = r['folder_path']
            if fp != 'Root':
                folders.add(fp)
                parts = fp.split('/')
                if len(parts) > 1:
                    folders.add(parts[0])
            
            if r['file_name'] != '.keep':
                if fp == 'Root':
                    files.append(r['file_name'])
                else:
                    files.append(f"{fp}/{r['file_name']}")
        return sorted(list(folders)), sorted(files)
    except Exception as e:
        logger.error(f"Error fetching Cloud Hierarchy: {e}")
        return [], []

def get_cloud_hierarchy(bank_type):
    return get_cloud_hierarchy_cached(bank_type)

@st.cache_data(show_spinner=False, ttl=120)
def get_user_feedback_cached(username):
    try:
        fb_res = supabase.table('user_feedback').select('feedback').eq('username', username).execute()
        if fb_res.data:
            return fb_res.data[0]['feedback']
    except Exception as e:
        logger.error(f"Error fetching feedback: {e}")
    return ""

def nav_admin_up():
    curr = st.session_state.admin_current_path
    if curr:
        parts = curr.split('/')
        st.session_state.admin_current_path = '/'.join(parts[:-1])

def nav_admin_down(folder):
    curr = st.session_state.admin_current_path
    if curr: st.session_state.admin_current_path = curr + '/' + folder
    else: st.session_state.admin_current_path = folder

# Performance Optimization: Merged dual-loop calculations into single pass computation
def evaluate_assessment(test_key, questions, user_answers):
    """Calculates scores and builds detailed question reports efficiently in a single pass."""
    score, incorrect, unanswered = 0, 0, 0
    neg_mark_value = get_neg_mark(test_key)
    q_details = []
    
    for i, q in enumerate(questions):
        is_match = (q.get('type') == 'match')
        user_ans = user_answers.get(i)
        
        q_num = i + 1
        clean_q = re.sub(r'^[Qq]?(?:uestion)?\s*\d+[\.\)]\s*', '', q['q'])
        status, marks, neg = "Unanswered", 0, 0
        c_ans_str, u_ans_str = "N/A", "None"
        
        if user_ans is None or (is_match and not user_ans):
            unanswered += 1
            if is_match: c_ans_str = str(q['ans'])
            else: c_ans_str = str(q['options'][q['ans']] if 0 <= q['ans'] < len(q['options']) else "N/A")
        else:
            u_ans_str = str(user_ans)
            if is_match:
                correct_ans = q['ans']
                c_ans_str = str(correct_ans)
                if isinstance(user_ans, dict) and user_ans == correct_ans:
                    status, marks = "Correct", 1
                    score += 1
                else:
                    status, neg = "Incorrect", neg_mark_value
                    incorrect += 1
            else:
                correct_ans = q['options'][q['ans']] if 0 <= q['ans'] < len(q['options']) else None
                c_ans_str = str(correct_ans)
                if user_ans == correct_ans:
                    status, marks = "Correct", 1
                    score += 1
                else:
                    status, neg = "Incorrect", neg_mark_value
                    incorrect += 1
                    
        q_details.append({
            "q_num": q_num, "question": clean_q, "user_ans": u_ans_str,
            "correct_ans": c_ans_str, "status": status, "marks": marks, "negative": neg
        })
        
    negative_marks = incorrect * neg_mark_value
    final_score = score - negative_marks
    return score, incorrect, unanswered, negative_marks, final_score, q_details

def record_detailed_attempt(user, test_key, original_file):
    # Retrieve optimized single-pass evaluations
    correct, incorrect, unanswered, negative, final_score, q_details = evaluate_assessment(
        test_key, st.session_state.questions, st.session_state.user_answers
    )
    total_q = len(st.session_state.questions)
        
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

    try:
        supabase_data = {
            "username": user,
            "test_name": attempt_data["test_name"],
            "subject": attempt_data["subject"],
            "total_questions": attempt_data["total_questions"],
            "correct": attempt_data["correct"],
            "incorrect": attempt_data["incorrect"],
            "unanswered": attempt_data["unanswered"],
            "final_score": attempt_data["final_score"],
            "folder": attempt_data["folder"],
            "attempt_number": attempt_data["attempt_number"],
            "negative_marks": attempt_data["negative_marks"],
            "percentage": attempt_data["percentage"],
            "datetime": attempt_data["datetime"],
            "q_details": attempt_data["q_details"]
        }
        supabase.table("exam_history").insert(supabase_data).execute()
        # Invalidate related caches directly
        get_supabase_history_cached.clear(user)
        get_all_supabase_history_cached.clear()
    except Exception as e:
        st.session_state.db_save_error = str(e)
        logger.error(f"Failed to sync result to Supabase: {e}")

def record_attempt_usage():
    if not st.session_state.get('attempt_recorded', False):
        user = st.session_state.get('current_user')
        test_key = st.session_state.get('current_test_filename')
        if user and test_key:
            original_file = test_key.replace("ADVANCED|", "")
            increment_attempt(user, test_key)
            record_detailed_attempt(user, test_key, original_file)
            
            try:
                res = supabase.table('exam_history').select('id').eq('username', user).execute()
                st.session_state.history_view_index = len(res.data) - 1
            except:
                st.session_state.history_view_index = 0
            
        st.session_state.attempt_recorded = True

def destroy_active_assessment():
    """Completely clears the active assessment state and destroys any resume sessions."""
    st.session_state.quiz_ready = False
    st.session_state.questions = []
    st.session_state.current_q = 0
    st.session_state.user_answers = {}
    st.session_state.visited_questions = set()
    st.session_state.marked_questions = set()
    st.session_state.topic = ""
    st.session_state.timer_mode = "No Timer"
    st.session_state.time_val = 0
    st.session_state.remaining_seconds = 0
    st.session_state.last_calc_time = 0
    st.session_state.last_interaction_time = 0
    st.session_state.is_paused = False
    st.session_state.current_test_filename = ""
    st.session_state.attempt_recorded = False

    # Invalidate the resume session file safely
    sid = st.session_state.get("sid")
    if sid:
        session_path = os.path.join(SESSION_FOLDER, f"{sid}.pkl")
        if os.path.exists(session_path):
            try:
                os.remove(session_path)
            except Exception as e:
                logger.error(f"Failed cleaning session pkl: {e}")

# ==========================================
# 2. STATE INITIALIZATION
# ==========================================
def init_session():
    default_state = {
        'auth': False, 'current_user': "", 'questions': [], 'current_q': 0,
        'user_answers': {}, 'visited_questions': set(), 'marked_questions': set(),
        'quiz_ready': False, 'topic': "", 'timer_mode': "No Timer", 
        'time_val': 0, 'remaining_seconds': 0, 'last_calc_time': 0, 'last_interaction_time': 0,
        'active_page': "Dashboard", 'dashboard_tab': "Practice", 'is_paused': False,
        'current_test_filename': "", 'attempt_recorded': False, 'admin_current_path': "",
        'sid': "", 'current_bank': "Basic", 'last_admin_bank': "Basic",
        'query_input': "", 'history_view_index': -1, 'folders_checked': False,
        'editing_item': None, 'db_save_error': None
    }

    query_params = st.query_params
    sid = query_params.get("sid", None)
    
    if sid and not st.session_state.get('auth', False):
        session_path = os.path.join(SESSION_FOLDER, f"{sid}.pkl")
        if os.path.exists(session_path):
            try:
                with open(session_path, "rb") as f: saved_state = pickle.load(f)
                for k, v in saved_state.items():
                    if k in default_state: st.session_state[k] = v
                return 
            except Exception: pass 
                
    for key, value in default_state.items():
        if key not in st.session_state: st.session_state[key] = value

# ==========================================
# 3. CORE TIME & EVENT HANDLERS
# ==========================================
def passive_time_check():
    if st.session_state.get('active_page') != 'Exam' or st.session_state.get('is_paused', False): return

    now = time.time()
    elapsed = now - st.session_state.get('last_calc_time', now)
    st.session_state.last_calc_time = now

    if st.session_state.timer_mode == "Total Time (Minutes)":
        st.session_state.remaining_seconds -= elapsed
        if st.session_state.remaining_seconds <= 0:
            st.session_state.remaining_seconds = 0
            st.session_state.active_page = "Result"
            record_attempt_usage()
            destroy_active_assessment()
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
    with st.spinner(f"Configuring {os.path.basename(file_name)} engine from Cloud..."):
        st.session_state.questions = []
        bank = st.session_state.get('current_bank', 'Basic')
        
        parts = file_name.split('/')
        fname = parts[-1]
        folder_path = '/'.join(parts[:-1]) if len(parts) > 1 else 'Root'
        test_key = file_name if bank == 'Basic' else f"ADVANCED|{file_name}"
        
        try:
            res = supabase.table('question_banks').select('csv_data').eq('bank_type', bank).eq('folder_path', folder_path).eq('file_name', fname).execute()
            if not res.data:
                st.error("Assessment data not found in Cloud.")
                time.sleep(2)
                st.rerun()
            
            csv_data = res.data[0]['csv_data']
            f = io.StringIO(csv_data)
            reader = csv.DictReader(f)
            
            for row in reader:
                raw_type = row.get('Type')
                q_type = str(raw_type).strip().lower() if raw_type else ''
                
                if q_type == 'match':
                    left_items = []; right_items = []
                    for i in range(1, 11): 
                        l_val = row.get(f'Left{i}'); r_val = row.get(f'Right{i}')
                        l_str = str(l_val).strip() if l_val else ''
                        r_str = str(r_val).strip() if r_val else ''
                        if l_str and r_str: left_items.append(l_str); right_items.append(r_str)
                    
                    if left_items:
                        q_text = row.get('Question')
                        st.session_state.questions.append({
                            'type': 'match', 'q': str(q_text).strip() if q_text else '',
                            'left': left_items, 'right': right_items,
                            'options': sorted(right_items), 
                            'ans': {l: r for l, r in zip(left_items, right_items)} 
                        })
                else:
                    opts = []
                    for i in range(1, 6):
                        val = row.get(f'Option{i}')
                        if val and str(val).strip(): opts.append(str(val).strip())
                    
                    q_text = row.get('Question')
                    ans_val = row.get('Answer')
                    ans_str = str(ans_val).strip() if ans_val else ''
                    
                    st.session_state.questions.append({
                        'type': 'mcq', 'q': str(q_text).strip() if q_text else '', 
                        'options': opts, 'ans': int(ans_str) - 1 if ans_str.isdigit() else -1
                    })
        except Exception as e:
            logger.error(f"Error parsing Cloud File: {e}")
            st.error("An error occurred configuring the assessment engine.")
            st.stop()
                
        t_config = get_timer_config(test_key)
        
        if t_config["mode"] == "No Timer": t_mode = "No Timer"; t_val = 0; rem_sec = 0
        elif t_config["mode"] == "Per Question":
            t_mode = "Total Time (Minutes)" 
            total_seconds = len(st.session_state.questions) * t_config["value"]
            t_val = round(total_seconds / 60, 2); rem_sec = total_seconds
        else: 
            t_mode = "Total Time (Minutes)"; t_val = t_config["value"]; rem_sec = t_val * 60
                
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

def nav_goto(q_idx):
    record_activity()
    if not st.session_state.is_paused: st.session_state.current_q = q_idx

def nav_prev():
    record_activity()
    if not st.session_state.is_paused and st.session_state.current_q > 0: st.session_state.current_q -= 1

def nav_next():
    record_activity()
    if not st.session_state.is_paused and st.session_state.current_q < len(st.session_state.questions) - 1: st.session_state.current_q += 1

def nav_submit():
    record_activity()
    if not st.session_state.is_paused:
        record_attempt_usage()
        destroy_active_assessment()
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
                    if w_key in st.session_state: st.session_state[w_key] = "-- Select --"
            else:
                if f"radio_ans_{q_idx}" in st.session_state: st.session_state[f"radio_ans_{q_idx}"] = None

def toggle_mark(q_idx):
    record_activity()
    if not st.session_state.is_paused:
        if q_idx in st.session_state.marked_questions: st.session_state.marked_questions.remove(q_idx)
        else: st.session_state.marked_questions.add(q_idx)

def on_radio_change(q_idx):
    record_activity()
    if not st.session_state.is_paused:
        selected = st.session_state.get(f"radio_ans_{q_idx}")
        if selected is not None: st.session_state.user_answers[q_idx] = selected
        else: st.session_state.user_answers.pop(q_idx, None)

def on_match_change(q_idx, left_items):
    record_activity()
    if not st.session_state.is_paused:
        current_match = {}
        for l in left_items:
            val = st.session_state.get(f"match_{q_idx}_{l}")
            if val and val != "-- Select --": current_match[l] = val
        if current_match: st.session_state.user_answers[q_idx] = current_match
        else: st.session_state.user_answers.pop(q_idx, None)

# ==========================================
# 5. CSS & JAVASCRIPT INJECTION
# ==========================================
UI_COLORS = {
    "primary": "#4F46E5", "primary_dark": "#4338ca", "ink": "#0f172a", "muted": "#64748b",
    "surface": "#ffffff", "surface_subtle": "#f8fafc", "border": "#e2e8f0",
    "success": "#16a34a", "warning": "#d97706", "danger": "#dc2626",
}

def render_page_header(title, subtitle=None, eyebrow=None):
    eyebrow_html = f"<p class='page-eyebrow'>{eyebrow}</p>" if eyebrow else ""
    subtitle_html = f"<p class='page-subtitle'>{subtitle}</p>" if subtitle else ""
    st.markdown(f'<section class="page-header">{eyebrow_html}<h1>{title}</h1>{subtitle_html}</section>', unsafe_allow_html=True)

def render_metric_card(label, value, accent="blue", helper_text=None):
    helper_html = f"<p>{helper_text}</p>" if helper_text else ""
    st.markdown(f'<div class="metric-card metric-{accent}"><span>{label}</span><strong>{value}</strong>{helper_html}</div>', unsafe_allow_html=True)

def inject_custom_css():
    try:
        with open('bg.jpg', "rb") as image_file:
            encoded_string = base64.b64encode(image_file.read()).decode()
            bg_css = f".stApp {{ background-image: linear-gradient(rgba(8, 25, 55, 0.35), rgba(8, 25, 55, 0.35)), url(data:image/jpeg;base64,{encoded_string}); background-size: cover; background-position: center; background-attachment: fixed; }} @media (prefers-color-scheme: dark) {{ .stApp {{ background-image: linear-gradient(rgba(0, 0, 0, 0.45), rgba(0, 0, 0, 0.45)), url(data:image/jpeg;base64,{encoded_string}); }} }}"
    except: bg_css = ".stApp { background-color: var(--background-color); }"

    st.markdown(f"""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
        {bg_css}
        *, html, body {{ -webkit-font-smoothing: antialiased !important; -moz-osx-font-smoothing: grayscale !important; text-rendering: optimizeLegibility !important; }}
        [class*="viewerBadge_container"], [data-testid="manage-app-button"] {{ position: fixed !important; top: 15px !important; left: 15px !important; bottom: auto !important; right: auto !important; transform: scale(0.65) translateZ(0) !important; transform-origin: top left !important; opacity: 0.65 !important; background-color: rgba(255, 255, 255, 0.85) !important; border-radius: 8px !important; box-shadow: 0 2px 8px rgba(0,0,0,0.1) !important; z-index: 999999 !important; transition: opacity 0.2s ease !important; }}
        [class*="viewerBadge_container"]:hover, [data-testid="manage-app-button"]:hover {{ opacity: 1 !important; background-color: rgba(255, 255, 255, 1) !important; }}
        @media (prefers-color-scheme: dark) {{ [class*="viewerBadge_container"], [data-testid="manage-app-button"] {{ background-color: rgba(15, 23, 42, 0.85) !important; }} [class*="viewerBadge_container"]:hover, [data-testid="manage-app-button"]:hover {{ background-color: rgba(15, 23, 42, 1) !important; }} }}
        @media (max-width: 640px) {{ div[data-testid="stHorizontalBlock"]:has(> div[data-testid="column"]:nth-child(4)) {{ flex-wrap: wrap !important; flex-direction: row !important; gap: 0.5rem !important; }} div[data-testid="stHorizontalBlock"]:has(> div[data-testid="column"]:nth-child(4)) > div[data-testid="column"] {{ min-width: calc(50% - 0.5rem) !important; flex: 1 1 calc(50% - 0.5rem) !important; width: calc(50% - 0.5rem) !important; }} }}
        h1, h2, h3, h4, h5, h6, p, span, label, div[data-testid="stMarkdownContainer"], .question-card__text, .question-card__number {{ text-shadow: 0 2px 6px rgba(0,0,0,0.45); }}
        @media (max-width: 768px) {{ h1, h2, h3, h4, h5, h6, p, span, label, div[data-testid="stMarkdownContainer"], .question-card__text, .question-card__number {{ text-shadow: none !important; }} div[data-testid="stContainer"], .metric-card, .edtech-profile-card, .page-header {{ box-shadow: none !important; border: 1px solid var(--border) !important; }} }}
        @media (prefers-color-scheme: light) {{ h1, h2, h3, h4, h5, h6, p, label, div[data-testid="stMarkdownContainer"], .question-card__text {{ color: #FFFFFF !important; }} span, .page-subtitle, .assessment-meta, .exam-motivation-note, .legend-text, .metric-card p {{ color: #E5E7EB !important; }} input, select, textarea, div.stButton > button, div.stButton > button * {{ color: var(--text-color) !important; text-shadow: none !important; }} .stAlert * {{ text-shadow: none !important; }} }}
        @media (prefers-color-scheme: dark) {{ input, select, textarea, div.stButton > button, div.stButton > button * {{ text-shadow: none !important; }} .stAlert * {{ text-shadow: none !important; }} }}
        :root {{ --sb-primary: {UI_COLORS['primary']}; --sb-primary-dark: {UI_COLORS['primary_dark']}; }}
        header[data-testid="stHeader"] {{ background: transparent !important; }}
        .block-container {{ max-width: 1400px !important; padding: clamp(1rem, 3vw, 2.5rem) !important; margin: 1.5rem auto !important; min-height: calc(100vh - 4rem); border: 1px solid rgba(128, 128, 128, 0.2); border-radius: 20px; background-color: var(--background-color) !important; box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.15); animation: fadeIn 0.4s ease-out forwards; }}
        @keyframes fadeIn {{ from {{ opacity: 0; transform: translateY(10px); }} to {{ opacity: 1; transform: translateY(0); }} }}
        section[data-testid="stSidebar"] {{ border-right: 1px solid rgba(128, 128, 128, 0.2); box-shadow: 2px 0 20px rgba(0,0,0,0.03); }}
        .edtech-profile-card {{ background: var(--secondary-background-color); border: 1px solid rgba(128, 128, 128, 0.2); border-radius: 16px; padding: 1.25rem 1rem; margin: 0.5rem 0 1.5rem 0; display: flex; align-items: center; gap: 12px; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05); }}
        .edtech-profile-avatar {{ width: 44px; height: 44px; border-radius: 50%; background: linear-gradient(135deg, #4f46e5, #6366f1); color: white !important; display: flex; align-items: center; justify-content: center; font-weight: 800; font-size: 1.1rem; box-shadow: 0 4px 10px rgba(79, 70, 229, 0.3); }}
        .edtech-profile-info strong {{ display: block; font-size: 0.95rem; font-weight: 700; line-height: 1.2; color: var(--text-color); }}
        .edtech-profile-info span {{ display: block; font-size: 0.75rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em; margin-top: 2px; color: var(--text-color); opacity: 0.8;}}
        div.stButton > button {{ min-height: 2.2rem !important; border-radius: 6px !important; font-weight: 600 !important; font-size: 0.85rem !important; padding: 0.25rem 0.5rem !important; transition: opacity 0.15s ease !important; transform: translateZ(0) !important; box-shadow: none !important; }}
        div.stButton > button:hover:not(:disabled) {{ opacity: 0.85 !important; }}
        div.stButton > button[kind="primary"] {{ border: none !important; background: var(--sb-primary) !important; color: #ffffff !important; }}
        div.stButton > button[kind="primary"]:hover:not(:disabled) {{ background: var(--sb-primary-dark) !important; }}
        .page-header {{ margin: 0 0 2rem; padding: 1.75rem 2rem; border: 1px solid rgba(128, 128, 128, 0.2); border-radius: 16px; background: var(--secondary-background-color); box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05); }}
        .page-header h1 {{ margin: 0 !important; color: var(--text-color) !important; font-size: clamp(1.75rem, 3.5vw, 2.5rem) !important; font-weight: 800; }}
        .page-eyebrow {{ margin: 0 0 0.5rem !important; color: var(--sb-primary) !important; font-weight: 700; text-transform: uppercase; }}
        .page-subtitle {{ margin: 0.5rem 0 0 !important; color: var(--text-color) !important; opacity: 0.8; font-size: 1.05rem; }}
        .metric-card {{ padding: 1.25rem; border: 1px solid rgba(128, 128, 128, 0.2); border-top: 4px solid var(--metric-accent, #4f46e5); border-radius: 16px; background: var(--secondary-background-color); box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.03); transition: all 0.25s ease; }}
        .metric-card span {{ display: block; font-size: 0.8rem; font-weight: 700; text-transform: uppercase; color: var(--text-color) !important; opacity: 0.8; }}
        .metric-card strong {{ display: block; margin-top: 0.4rem; font-size: clamp(1.4rem, 2vw, 1.8rem); font-weight: 800; color: var(--text-color) !important; }}
        .metric-card p {{ margin: 0.5rem 0 0 !important; font-size: 0.85rem; color: var(--text-color) !important; opacity: 0.8; }}
        .metric-blue {{ --metric-accent: #3b82f6; }} .metric-green {{ --metric-accent: #10b981; }} .metric-red {{ --metric-accent: #ef4444; }} .metric-amber {{ --metric-accent: #f59e0b; }} .metric-purple {{ --metric-accent: #8b5cf6; }}
        .legend-box {{ background: var(--secondary-background-color); padding: 10px; border: 1px solid rgba(128, 128, 128, 0.2); border-radius: 8px; margin: 6px 0; box-shadow: 0 2px 5px -2px rgba(0,0,0,0.05); }}
        .legend-title {{ font-weight: 700; color: var(--text-color); font-size: 12px; }} .legend-text {{ font-weight: 600; color: var(--text-color); opacity: 0.9; }}
        .palette-title {{ margin: 0 0 0.5rem !important; color: var(--text-color) !important; font-size: 0.9rem; font-weight: 800; text-transform: uppercase; }}
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.palette-title) div.stButton > button {{ min-height: 2.2rem; font-size: 0.85rem; }}
        .exam-motivation-banner {{ position: relative; overflow: hidden; margin: 0 0 1.5rem; padding: clamp(1.5rem, 3vw, 2.25rem) clamp(1.25rem, 4vw, 3rem); border: 1px solid rgba(128, 128, 128, 0.2); border-radius: 16px; background: var(--secondary-background-color); text-align: center; animation: examBannerFadeIn 0.55s ease-out both; }}
        .exam-motivation-content {{ position: relative; z-index: 1; max-width: 760px; margin: 0 auto; }}
        .exam-motivation-banner h2 {{ margin: 0 !important; font-size: clamp(1.35rem, 3vw, 2rem) !important; font-weight: 800; color: var(--text-color) !important; }}
        .exam-motivation-lines {{ display: grid; gap: 0.2rem; margin: 1rem 0 0 !important; font-size: clamp(0.95rem, 2vw, 1.05rem); font-weight: 600; color: var(--text-color) !important; }}
        .exam-motivation-note {{ margin: 1rem 0 0 !important; font-size: 0.95rem; font-weight: 500; color: var(--text-color) !important; opacity: 0.9; }}
        .exam-motivation-closing {{ margin: 0.7rem 0 0 !important; font-size: 0.95rem; font-weight: 700; color: var(--text-color) !important; }}
        .exam-motivation-footer {{ margin: 0.85rem 0 0 !important; font-size: 1.2rem; letter-spacing: 0.18em; }}
        .exam-banner-emoji {{ position: absolute; z-index: 0; font-size: clamp(1.15rem, 2.5vw, 1.6rem); opacity: 0.7; pointer-events: none; animation: examEmojiFloat 4s ease-in-out infinite; }}
        .exam-banner-emoji-left {{ top: 17%; left: 5%; }} .exam-banner-emoji-right {{ right: 5%; bottom: 16%; animation-delay: -1.7s; }}
        @keyframes examBannerFadeIn {{ from {{ opacity: 0; transform: translateY(10px); }} to {{ opacity: 1; transform: translateY(0); }} }}
        @keyframes examEmojiFloat {{ 0%, 100% {{ transform: translateY(0); }} 50% {{ transform: translateY(-6px); }} }}
        .res-correct {{ border-top-color: #16a34a !important; }} .res-incorrect {{ border-top-color: #dc2626 !important; }} .res-unanswered {{ border-top-color: #d97706 !important; }}
        </style>
    """, unsafe_allow_html=True)

def render_visual_timer():
    is_timed = (st.session_state.timer_mode == "Total Time (Minutes)")
    rem_sec = int(max(0, st.session_state.remaining_seconds))
    html_code = f"""<!DOCTYPE html><html><head><style>
        body {{ margin:0; padding:0; font-family: Inter, sans-serif; background: transparent; }}
        .timer-box {{ box-sizing: border-box; min-height: 38px; padding: 5px 8px; border: 1px solid #fecaca; border-radius: 8px; background: linear-gradient(135deg, #fff5f5, #fff1f2); color: #e11d48; font-size: 16px; font-weight: 800; text-align: center; display: flex; align-items: center; justify-content: center; gap: 8px; box-shadow: 0 2px 5px rgba(225, 29, 72, 0.05); }}
        .no-timer {{ background: #f0f9ff; border-color: #bae6fd; color: #0284c7; font-size: 14px; }}
        @media (prefers-color-scheme: dark) {{ .timer-box {{ background: linear-gradient(135deg, #4c1d95, #312e81); border-color: #4338ca; color: #f8fafc; }} .no-timer {{ background: #0f172a; border-color: #1e293b; color: #38bdf8; }} }}
        </style></head><body><div id="t-box" class="timer-box {'no-timer' if not is_timed else ''}">⏳ <span id="time">Loading...</span></div>
        <script>
            var is_timed = {1 if is_timed else 0}; var rem = {rem_sec}; var display = document.getElementById("time");
            if (!is_timed) {{ display.innerHTML = "Practice Mode - No Limit"; }} else {{
                function updateDisplay() {{ if (rem <= 0) {{ display.innerHTML = "TIME UP!"; return false; }} var m = Math.floor(rem / 60); var s = Math.floor(rem % 60); display.innerHTML = (m < 10 ? "0" + m : m) + ":" + (s < 10 ? "0" + s : s); return true; }}
                updateDisplay(); var x = setInterval(function() {{ rem--; if (!updateDisplay()) clearInterval(x); }}, 1000);
            }}
        </script></body></html>"""
    components.html(html_code, height=45)

# ==========================================
# 6. PAGE RENDERING FUNCTIONS
# ==========================================
def render_login():
    users = get_all_users()
    st.write("<br><br>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 1.5, 1]) 
    with col2:
        with st.container(border=True):
            st.markdown("<h1 style='text-align:center; font-weight:800; margin-bottom:0.2rem;'>Study Booster</h1>", unsafe_allow_html=True)
            st.markdown("<p style='text-align:center; font-size:1rem; margin-top:0; opacity:0.8;'>Your focused space for practice and progress.</p>", unsafe_allow_html=True)
            st.divider()
            
            # FIX: Sort users alphabetically but keep Admin at the top
            admin_users = sorted([u for u in users.keys() if "Admin" in u])
            student_users = sorted([u for u in users.keys() if "Admin" not in u], key=lambda x: x.lower())
            dropdown_options = ["-- Select User --"] + admin_users + student_users
            
            username = st.selectbox("👤 Select Profile", dropdown_options)
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
    st.sidebar.markdown(f"<div class='edtech-profile-card'><div class='edtech-profile-avatar'>{user_initial}</div><div class='edtech-profile-info'><strong>{st.session_state.current_user.split()[0]}</strong><span>{role}</span></div></div>", unsafe_allow_html=True)
    
    def safe_navigate(target_page, dashboard_tab=None):
        if st.session_state.get('active_page') == 'Exam' and not st.session_state.get('is_paused', False):
            st.sidebar.error("An assessment is currently in progress. Please Submit or Pause the assessment before leaving this page.")
        else:
            st.session_state.active_page = target_page
            if dashboard_tab:
                st.session_state.dashboard_tab = dashboard_tab
            st.rerun()

    if is_admin:
        if st.sidebar.button("⚙️ Admin Control Panel", use_container_width=True): safe_navigate("Admin")
        if st.sidebar.button("💬 User Queries", use_container_width=True): safe_navigate("UserQueries")
        st.sidebar.divider()
            
    if st.sidebar.button("📚 Dashboard", use_container_width=True): safe_navigate("Dashboard", "Practice")
    if st.sidebar.button("📈 Performance", use_container_width=True): safe_navigate("Dashboard", "Performance")
    if st.sidebar.button("💬 Ask Query", use_container_width=True): safe_navigate("Dashboard", "Ask Query")
        
    st.sidebar.divider()
    if st.sidebar.button("🚪 Logout", type="secondary", use_container_width=True):
        if st.session_state.get('active_page') == 'Exam' and not st.session_state.get('is_paused', False):
            st.sidebar.error("An assessment is currently in progress. Please Submit or Pause the assessment before leaving this page.")
        else:
            with st.spinner("Logging out safely..."):
                if st.session_state.get("sid"):
                    session_path = os.path.join(SESSION_FOLDER, f"{st.session_state.sid}.pkl")
                    if os.path.exists(session_path):
                        try: os.remove(session_path)
                        except: pass
                if "sid" in st.query_params: del st.query_params["sid"]
                for key in list(st.session_state.keys()): del st.session_state[key]
                time.sleep(0.4)
                st.rerun()

@st.cache_data(show_spinner=False, ttl=120)
def get_user_queries_cached():
    try:
        res = supabase.table('user_queries').select('*').execute()
        return sorted(res.data, key=lambda x: x.get('datetime', ''))
    except Exception as e:
        logger.error(f"Failed to fetch queries: {e}")
        return []

def render_user_queries():
    if "Admin" not in st.session_state.current_user: st.error("Unauthorized!"); return
    st.markdown("<h2 style='font-weight:800;'>Support Center & Queries</h2>", unsafe_allow_html=True)
    st.write("---")
    
    queries = get_user_queries_cached()
    
    col1, col2 = st.columns([2, 1])
    search_u = col1.text_input("🔍 Search by Username", placeholder="Type username...", key="admin_search_query")
    filter_s = col2.selectbox("📁 Filter by Status", ["All", "Pending", "Resolved"], key="admin_filter_query")
    
    filtered = queries
    if search_u: filtered = [q for q in filtered if search_u.lower() in q.get("username", "").lower()]
    if filter_s != "All": filtered = [q for q in filtered if q.get("status") == filter_s]
    
    if not filtered: st.info("No queries found."); return
        
    for q in reversed(filtered):
        with st.container(border=True):
            st.markdown(f"**{q.get('username', 'Unknown')}** &middot; <span style='font-size:0.85rem; opacity:0.8;'>{q.get('datetime', 'Unknown')}</span> &middot; **[{q.get('status', 'Pending')}]**", unsafe_allow_html=True)
            st.markdown(f"<div style='margin-top:8px; padding:12px; background:var(--secondary-background-color); border-radius:8px; border-left: 4px solid #cbd5e1; font-size:1rem;'>{q.get('text', '')}</div>", unsafe_allow_html=True)
            
            if q.get('status', 'Pending') == "Pending":
                reply_input = st.text_area("Write your reply:", key=f"reply_input_{q['id']}")
                if st.button("Mark as Resolved & Send", key=f"btn_resolve_{q['id']}", type="primary"):
                    if reply_input.strip():
                        with st.spinner("Updating status..."):
                            try:
                                supabase.table('user_queries').update({
                                    "reply": reply_input, 
                                    "status": "Resolved"
                                }).eq("id", q["id"]).execute()
                                get_user_queries_cached.clear()
                                st.toast("Reply sent!", icon="✅"); time.sleep(0.5); st.rerun()
                            except Exception as e:
                                logger.error(f"Error saving reply: {e}")
                                st.error("Failed to save reply.")
                    else: st.warning("Please enter a reply.")
            else:
                st.markdown(f"**Admin Reply:**")
                st.success(q.get("reply", ""))

def render_admin():
    if "Admin" not in st.session_state.current_user: st.error("Unauthorized!"); return
    st.markdown("<h2 style='font-weight:800;'>⚙️ Admin Control Panel</h2>", unsafe_allow_html=True)
    st.write("---")
    
    _, basic_files = get_cloud_hierarchy("Basic")
    _, adv_files = get_cloud_hierarchy("Advanced")
    
    admin_file_options = {f"Basic | {f}": f for f in basic_files}
    admin_file_options.update({f"Advanced | {f}": f"ADVANCED|{f}" for f in adv_files})

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

    with st.expander("📁 Question Bank Management (Cloud DB)", expanded=False):
        admin_bank = st.radio("Select Question Bank", ["Basic", "Advanced"], horizontal=True, key="admin_bank_radio")
        if st.session_state.get('last_admin_bank') != admin_bank:
            st.session_state.admin_current_path = ""; st.session_state.last_admin_bank = admin_bank
        
        current_path = st.session_state.get('admin_current_path') or ''
        display_path = current_path.replace('/', ' / ') if current_path else 'Root'
        st.markdown(f"**Current Directory:** ` {display_path} `")
        
        c_up, c_newf, c_upld = st.columns(3)
        with c_up:
            if current_path != '': 
                st.button("⬅️ Back / Up", on_click=nav_admin_up, use_container_width=True)
        with c_newf:
            new_f = st.text_input("New Folder", key="new_f_input", label_visibility="collapsed", placeholder="Folder Name")
            if st.button("Create Folder", use_container_width=True):
                if new_f:
                    try:
                        new_fp = new_f.strip() if current_path == '' else f"{current_path}/{new_f.strip()}"
                        supabase.table('question_banks').insert({
                            'bank_type': admin_bank, 'folder_path': new_fp, 'file_name': '.keep', 'csv_data': ''
                        }).execute()
                        get_cloud_hierarchy_cached.clear(admin_bank)
                        st.toast(f"Created '{new_f}'", icon="✅"); st.rerun()
                    except Exception as e:
                        logger.error(f"Error creating folder: {e}")
        with c_upld:
            uploaded_file = st.file_uploader("Upload CSV", type=['csv'], label_visibility="collapsed")
            if uploaded_file:
                with st.spinner("Uploading to Database..."):
                    try:
                        content = uploaded_file.getvalue().decode('utf-8-sig', errors='ignore')
                        supabase.table('question_banks').insert({
                            'bank_type': admin_bank, 'folder_path': current_path if current_path != '' else 'Root', 
                            'file_name': uploaded_file.name, 'csv_data': content
                        }).execute()
                        get_cloud_hierarchy_cached.clear(admin_bank)
                        st.toast("Uploaded securely to Cloud!", icon="✅"); time.sleep(0.5); st.rerun()
                    except Exception as e:
                        logger.error(f"Error uploading CSV: {e}")
                
        st.write("---")
        
        try:
            res = supabase.table('question_banks').select('id, folder_path, file_name, created_at, csv_data').eq('bank_type', admin_bank).execute()
            records = res.data
        except Exception as e:
            logger.error(f"Error fetching directory contents: {e}")
            records = []
            
        subfolders = set()
        files = []
        
        for r in records:
            fp = r['folder_path']
            if current_path == '':
                if fp == 'Root':
                    if r['file_name'] != '.keep': files.append(r)
                else:
                    subfolders.add(fp.split('/')[0])
            else:
                if fp == current_path:
                    if r['file_name'] != '.keep': files.append(r)
                elif fp.startswith(current_path + '/'):
                    remainder = fp[len(current_path)+1:]
                    subfolders.add(remainder.split('/')[0])

        subfolders = sorted(list(subfolders))
        
        st.markdown("#### Folders")
        for folder in subfolders:
            with st.container(border=True):
                edit_key = f"edit_folder_{current_path}_{folder}"
                is_editing = st.session_state.get('editing_item') == edit_key
                
                if is_editing:
                    st.markdown(f"📁 **{folder}**")
                    ec1, ec2, ec3 = st.columns([8, 2, 2])
                    new_fn = ec1.text_input("New Name", value=folder, key=f"in_{edit_key}", label_visibility="collapsed")
                    if ec2.button("Save", key=f"save_{edit_key}", type="primary", use_container_width=True):
                        if new_fn and new_fn.strip() != folder:
                            try:
                                old_prefix = folder if current_path == '' else f"{current_path}/{folder}"
                                new_prefix = new_fn.strip() if current_path == '' else f"{current_path}/{new_fn.strip()}"
                                for r in records:
                                    rfp = r['folder_path']
                                    if rfp == old_prefix:
                                        supabase.table('question_banks').update({'folder_path': new_prefix}).eq('id', r['id']).execute()
                                    elif rfp.startswith(old_prefix + '/'):
                                        new_fp = rfp.replace(old_prefix, new_prefix, 1)
                                        supabase.table('question_banks').update({'folder_path': new_fp}).eq('id', r['id']).execute()
                                get_cloud_hierarchy_cached.clear(admin_bank)
                            except Exception as e:
                                logger.error(f"Error renaming folder: {e}")
                        st.session_state.editing_item = None
                        st.rerun()
                    if ec3.button("Cancel", key=f"cancel_{edit_key}", use_container_width=True):
                        st.session_state.editing_item = None
                        st.rerun()
                else:
                    fc1, fc2, fc3 = st.columns([8, 2, 2])
                    fc1.button(f"📁 {folder}", key=f"nav_{current_path}_{folder}", on_click=nav_admin_down, args=(folder,), use_container_width=True)
                    if fc2.button("Rename", key=f"rn_btn_{current_path}_{folder}", use_container_width=True):
                        st.session_state.editing_item = edit_key
                        st.rerun()
                    if fc3.button("Delete", key=f"del_f_{current_path}_{folder}", use_container_width=True):
                        try:
                            old_prefix = folder if current_path == '' else f"{current_path}/{folder}"
                            for r in records:
                                rfp = r['folder_path']
                                if rfp == old_prefix or rfp.startswith(old_prefix + '/'):
                                    supabase.table('question_banks').delete().eq('id', r['id']).execute()
                            get_cloud_hierarchy_cached.clear(admin_bank)
                        except Exception as e:
                            logger.error(f"Error deleting folder: {e}")
                        st.rerun()
                        
        st.write("---")
        c_ah1, c_ah2 = st.columns([6, 4])
        c_ah1.markdown("#### Assessments")
        sort_opt = c_ah2.selectbox("Sort Files By", ["Alphabetical (A–Z)", "Alphabetical (Z–A)", "Upload Date (Newest First)", "Upload Date (Oldest First)"], label_visibility="collapsed", key=f"sort_files_{current_path}")
        
        if sort_opt == "Alphabetical (A–Z)": files.sort(key=lambda x: x['file_name'].lower())
        elif sort_opt == "Alphabetical (Z–A)": files.sort(key=lambda x: x['file_name'].lower(), reverse=True)
        elif sort_opt == "Upload Date (Newest First)": files.sort(key=lambda x: x['created_at'], reverse=True)
        elif sort_opt == "Upload Date (Oldest First)": files.sort(key=lambda x: x['created_at'])

        all_folders = ["Root"] + sorted(list(set(r['folder_path'] for r in records if r['folder_path'] != 'Root')))
        
        for f_data in files:
            file_id = f_data['id']
            f_name = f_data['file_name']
            file_size_kb = len(f_data['csv_data'].encode('utf-8')) / 1024
            
            with st.container(border=True):
                edit_key = f"edit_file_{file_id}"
                is_editing = st.session_state.get('editing_item') == edit_key
                
                c1, c2 = st.columns([8, 2])
                c1.markdown(f"📄 **{f_name}**")
                c2.markdown(f"<span style='opacity:0.8;'>{file_size_kb:.1f} KB</span>", unsafe_allow_html=True)
                
                if is_editing:
                    ec1, ec2, ec3 = st.columns([8, 2, 2])
                    new_fn = ec1.text_input("New Name", value=f_name, key=f"in_{edit_key}", label_visibility="collapsed")
                    if ec2.button("Save", key=f"save_{edit_key}", type="primary", use_container_width=True):
                        if new_fn and new_fn.strip() != f_name:
                            try:
                                cn = new_fn.strip() if new_fn.strip().endswith('.csv') else new_fn.strip() + '.csv'
                                supabase.table('question_banks').update({'file_name': cn}).eq('id', file_id).execute()
                                get_cloud_hierarchy_cached.clear(admin_bank)
                            except Exception as e:
                                logger.error(f"Error renaming file: {e}")
                        st.session_state.editing_item = None
                        st.rerun()
                    if ec3.button("Cancel", key=f"cancel_{edit_key}", use_container_width=True):
                        st.session_state.editing_item = None
                        st.rerun()
                else:
                    mc1, mc2, mc3 = st.columns([6, 3, 3])
                    tgt = mc1.selectbox("Move", ["-- Move to Folder --"] + all_folders, key=f"mov_{file_id}", label_visibility="collapsed")
                    if tgt != "-- Move to Folder --":
                        try:
                            supabase.table('question_banks').update({'folder_path': tgt}).eq('id', file_id).execute()
                            get_cloud_hierarchy_cached.clear(admin_bank)
                        except Exception as e:
                            logger.error(f"Error moving file: {e}")
                        st.rerun()
                    
                    if mc2.button("Rename", key=f"rn_btn_{file_id}", use_container_width=True):
                        st.session_state.editing_item = edit_key
                        st.rerun()
                    
                    if mc3.button("Delete", key=f"del_{file_id}", use_container_width=True):
                        try:
                            supabase.table('question_banks').delete().eq('id', file_id).execute()
                            get_cloud_hierarchy_cached.clear(admin_bank)
                        except Exception as e:
                            logger.error(f"Error deleting file: {e}")
                        st.rerun()

    with st.expander("⚖️ Scoring & Penalty Configuration", expanded=False):
        if admin_file_options:
            nm_test_key = admin_file_options[st.selectbox("Select Assessment for Penalty", list(admin_file_options.keys()))]
            new_val = st.number_input("Penalty Value", min_value=0.0, max_value=0.33, value=float(get_neg_mark(nm_test_key)), step=0.01)
            if st.button("Apply Penalty Rule", type="primary"):
                set_neg_mark(nm_test_key, new_val)
                st.toast("Updated!", icon="✅")

    with st.expander("⏱️ Timer Configuration", expanded=False):
        if admin_file_options:
            sel_display = st.selectbox("Select Assessment", list(admin_file_options.keys()), key="tmr_test")
            t_file = admin_file_options[sel_display]
            curr_set = get_timer_config(t_file)
            new_mode = st.radio("Timing Rule", ["Total Time", "Per Question", "No Timer"], index=["Total Time", "Per Question", "No Timer"].index(curr_set["mode"]))
            new_val = st.number_input("Value", min_value=1, value=curr_set.get("value", 30)) if new_mode != "No Timer" else 0
            if st.button("Save Configuration", type="primary"):
                set_timer_config(t_file, new_mode, new_val)
                st.toast("Updated!", icon="✅")

    with st.expander("👥 User Management", expanded=False):
        users = get_all_users()
        t1, t2, t3 = st.tabs(["Add New", "Remove", "Reset Password"])
        with t1:
            new_u = st.text_input("New Username")
            new_p = st.text_input("Password", type="password")
            if st.button("Create Account", type="primary"):
                if new_u in users: st.error("User Already Exists!")
                elif new_u and new_p: 
                    if add_new_user_to_db(new_u, new_p):
                        st.toast("Account Created!", icon="✅"); time.sleep(1); st.rerun()
        with t2:
            del_u = st.selectbox("Account to Delete", [u for u in users if "Admin" not in u])
            cf_del = st.checkbox("Confirm deletion")
            if st.button("Delete Account", type="primary") and cf_del and del_u:
                if delete_user_from_db(del_u):
                    st.toast("User Deleted!", icon="✅"); time.sleep(1); st.rerun()
        with t3:
            ch_u = st.selectbox("Target Account", list(users.keys()))
            ch_p = st.text_input("New Secure Password", type="password")
            if st.button("Reset Password", type="primary") and ch_p:
                try:
                    supabase.table('users').update({"password": ch_p}).eq("username", ch_u).execute()
                    get_all_users_cached.clear()
                    st.toast("Password Reset Successfully!", icon="✅")
                except Exception as e:
                    logger.error(f"Error resetting password: {e}")

    with st.expander("📊 User Performance Reports", expanded=False):
        history = get_all_supabase_history()
        users = get_all_users()
        student_users = [u for u in users if "Admin" not in u]
        
        summary_data = []
        for u in student_users:
            u_hist = history.get(u, [])
            if not u_hist: continue
            
            total_tests = len(u_hist)
            scores = [h['final_score'] for h in u_hist]
            accs = [round((h['correct']/h['attempted']*100),1) if h['attempted']>0 else 0 for h in u_hist]
            avg_acc = sum(accs)/total_tests if total_tests > 0 else 0
            
            if avg_acc >= 80: status = "🟢 Excellent"
            elif avg_acc >= 60: status = "🔵 Good"
            elif avg_acc >= 40: status = "🟡 Average"
            else: status = "🔴 Needs Improvement"
            
            summary_data.append({
                "User": u,
                "Total Tests": total_tests,
                "Highest Score": round(max(scores), 2),
                "Avg Score": round(sum(scores)/total_tests, 2),
                "Avg Accuracy (%)": round(avg_acc, 1),
                "Status": status,
                "Last Test Date": u_hist[-1]['datetime'].split(" ")[0] if u_hist[-1]['datetime'] else ""
            })
            
        if summary_data:
            st.dataframe(summary_data, use_container_width=True, hide_index=True)
            st.write("---")
            
            sel_u = st.selectbox("Select User for Detailed Report & Feedback", [d["User"] for d in summary_data])
            if sel_u:
                u_hist = history.get(sel_u, [])
                scores = [h['final_score'] for h in u_hist]
                accs = [round((h['correct']/h['attempted']*100),1) if h['attempted']>0 else 0 for h in u_hist]
                
                total_q_overall = sum(h['total_questions'] for h in u_hist)
                total_corr = sum(h['correct'] for h in u_hist)
                total_inc = sum(h['incorrect'] for h in u_hist)
                total_unans = sum(h['unanswered'] for h in u_hist)
                
                st.markdown(f"#### 📈 {sel_u}'s Detailed Performance")
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Total Tests", len(u_hist))
                c2.metric("Highest Score", round(max(scores), 2))
                c3.metric("Avg Score", round(sum(scores)/len(scores), 2))
                c4.metric("Global Accuracy", f"{(total_corr/total_q_overall*100) if total_q_overall>0 else 0:.1f}%")
                
                c5, c6, c7, c8 = st.columns(4)
                c5.metric("Total Questions", total_q_overall)
                c6.metric("Total Correct", total_corr)
                c7.metric("Total Incorrect", total_inc)
                c8.metric("Unattempted", total_unans)
                
                tc1, tc2 = st.columns(2)
                with tc1: st.markdown("**Score Trend**"); st.line_chart(scores, height=150)
                with tc2: st.markdown("**Accuracy Trend (%)**"); st.line_chart(accs, height=150)
                
                st.markdown("#### 💬 Admin Feedback & Suggestions")
                current_fb = get_user_feedback_cached(sel_u)
                new_fb = st.text_area("Write personalized feedback for this user:", value=current_fb, height=120)
                
                if st.button("Save Feedback", type="primary", key=f"save_fb_{sel_u}"):
                    try:
                        supabase.table('user_feedback').upsert({
                            "username": sel_u,
                            "feedback": new_fb
                        }).execute()
                        get_user_feedback_cached.clear(sel_u)
                        st.toast("Feedback saved securely to Cloud!", icon="✅")
                    except Exception as e:
                        logger.error(f"Error saving feedback: {e}")
                        st.error("Error saving feedback.")
        else:
            st.info("No user performance data available yet.")

def render_dashboard_practice():
    st.markdown("<h3 style='margin-bottom:15px; font-weight:800;'>📋 Available Test Series</h3>", unsafe_allow_html=True)
    st.session_state.current_bank = st.radio("Question Bank", ["Basic", "Advanced"], horizontal=True, label_visibility="collapsed")
    
    active_base = st.session_state.current_bank
    folders, all_files = get_cloud_hierarchy(active_base)
    
    search_q = st.text_input("🔍 Search Subject or Folder...", placeholder="e.g. Physics, Mock 1...").strip().lower()
    
    if search_q: 
        files_to_disp = [f for f in all_files if search_q in f.lower()]
    else:
        c1, c2 = st.columns(2)
        # Display top-level root folders
        root_flds = sorted(list(set(f.split('/')[0] for f in folders)))
        sel_cat = c1.selectbox("Category", ["All"] + root_flds) if root_flds else "All"
        
        if sel_cat != "All":
            sub_flds = sorted(list(set(f.split('/')[1] for f in folders if f.startswith(sel_cat + '/') and f.count('/') >= 1)))
            sel_sub = c2.selectbox("Subcategory", ["All"] + sub_flds) if sub_flds else "All"
            prefix = sel_cat + '/' if sel_sub == "All" else f"{sel_cat}/{sel_sub}/"
            files_to_disp = [f for f in all_files if f.startswith(prefix)]
        else: 
            files_to_disp = all_files

    st.write("<br>", unsafe_allow_html=True)
    if not files_to_disp: 
        st.info("No assessments found matching criteria.")
    else:
        # Optimized N+1 Query mapping for attempts
        attempts_map = get_user_attempts_map(st.session_state.current_user)
        
        for f in files_to_disp:
            with st.container(border=True):
                test_k = f if st.session_state.current_bank == "Basic" else f"ADVANCED|{f}"
                att_data = attempts_map.get(test_k, {'allowed': 5, 'used': 0})
                used, allowed = att_data['used'], att_data['allowed']
                c1, c2 = st.columns([3, 1])
                c1.markdown(f"<h4 style='margin:0; font-weight:700;'>📄 {os.path.basename(f)[:-4]}</h4>", unsafe_allow_html=True)
                c1.markdown(f"<span style='font-size:0.85rem; font-weight:600; opacity:0.8;'>📁 {(os.path.dirname(f) or 'Root').replace('/',' / ')} &middot; Attempts: {used}/{allowed}</span>", unsafe_allow_html=True)
                if allowed - used > 0:
                    if c2.button("Start Assessment", key=f"ld_{test_k}", type="primary", use_container_width=True):
                        with st.spinner("Configuring Engine..."): 
                            time.sleep(0.3)
                            load_quiz(f)
                            st.rerun()
                else:
                    c2.button("Limit Reached", key=f"lm_{test_k}", disabled=True, use_container_width=True)

def render_dashboard_performance():
    st.markdown("<h2 style='font-weight:800;'>📈 Performance Analytics</h2>", unsafe_allow_html=True)
    st.write("---")
    
    user_fb = get_user_feedback_cached(st.session_state.current_user)

    if user_fb:
        st.markdown(f"""
        <div style='background-color: var(--secondary-background-color); border-left: 5px solid {UI_COLORS["primary"]}; padding: 16px; border-radius: 8px; margin-bottom: 24px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05);'>
            <h4 style='margin: 0 0 8px 0; color: var(--text-color); font-size: 1.05rem;'>💬 Admin Suggestion</h4>
            <p style='margin: 0; color: var(--text-color); opacity: 0.9; font-size: 0.95rem; white-space: pre-wrap;'>{user_fb}</p>
        </div>
        """, unsafe_allow_html=True)

    history = get_supabase_history(st.session_state.current_user)
    
    if not history:
        st.info("No test history found. Complete an assessment to generate your analytics dashboard.")
        return
        
    scores = [h['final_score'] for h in history]
    accs = [round((h['correct']/h['attempted']*100),1) if h['attempted']>0 else 0 for h in history]
    total_q = sum(h['attempted'] for h in history)
    total_corr = sum(h['correct'] for h in history)
    
    c1, c2, c3, c4 = st.columns(4)
    with c1: render_metric_card("Total Tests", str(len(history)), "blue")
    with c2: render_metric_card("Avg Score", f"{sum(scores)/len(scores):.1f}", "green")
    with c3: render_metric_card("Highest Score", f"{max(scores):.2f}", "purple")
    with c4: render_metric_card("Global Accuracy", f"{(total_corr/total_q*100) if total_q>0 else 0:.1f}%", "amber")
    
    st.write("<br>", unsafe_allow_html=True)
    ch_c1, ch_c2 = st.columns(2)
    with ch_c1: st.markdown("**Score Trend**"); st.line_chart(scores, height=200)
    with ch_c2: st.markdown("**Accuracy Trend (%)**"); st.line_chart(accs, height=200)
        
    st.markdown("#### 📜 Recent Test History")
    for i, att in enumerate(reversed(history)):
        real_idx = len(history) - 1 - i
        with st.container(border=True):
            r1, r2, r3, r4 = st.columns([3, 2, 2, 2])
            r1.markdown(f"**{att['test_name']}**<br><span style='font-size:0.8rem; opacity:0.8;'>{att['datetime']}</span>", unsafe_allow_html=True)
            r2.markdown(f"**Score:** {att['final_score']:.2f}")
            r3.markdown(f"**Accuracy:** {accs[real_idx]}%")
            if r4.button("View Full Report", key=f"rpt_{real_idx}"):
                st.session_state.history_view_index = real_idx
                st.session_state.active_page = "Result"
                st.rerun()

def render_dashboard_ask_query():
    st.markdown("<h2 style='font-weight:800;'>💬 Support & Doubts</h2>", unsafe_allow_html=True)
    st.markdown("<p style='opacity:0.8;'>Submit technical or academic queries directly to the platform administrators.</p>", unsafe_allow_html=True)
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
                with st.spinner("Submitting to Cloud Database..."):
                    try:
                        supabase.table('user_queries').insert({
                            "id": str(uuid.uuid4()), 
                            "username": st.session_state.current_user,
                            "datetime": time.strftime("%Y-%m-%d %H:%M:%S"), 
                            "text": query_text,
                            "status": "Pending", 
                            "reply": ""
                        }).execute()
                        get_user_queries_cached.clear()
                        st.toast("Submitted Successfully!", icon="✅"); time.sleep(0.5); st.rerun()
                    except Exception as e:
                        logger.error(f"Error submitting query: {e}")
                        st.error("Failed to submit query.")
                    
    st.markdown("#### Your Query History")
    queries = get_user_queries_cached()
    my_qs = [q for q in queries if q.get('username') == st.session_state.current_user]
        
    if not my_qs: st.info("No queries found.")
    else:
        for q in reversed(my_qs):
            with st.container(border=True):
                stat = q.get("status", "Pending")
                st.markdown(f"<span style='font-size:0.85rem; opacity:0.8;'>{q.get('datetime')}</span> &middot; **[{stat}]**", unsafe_allow_html=True)
                st.markdown(f"<div style='margin-top:5px; font-weight:600;'>{q.get('text')}</div>", unsafe_allow_html=True)
                if stat == "Resolved" and q.get("reply"):
                    st.markdown(f"<div style='margin-top:10px; padding:10px; background:var(--secondary-background-color); border-left:4px solid #16a34a; border-radius:6px;'>**Admin:** {q.get('reply')}</div>", unsafe_allow_html=True)

def render_dashboard():
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
    st.markdown("""<section class="exam-motivation-banner" aria-label="Exam encouragement"><span class="exam-banner-emoji exam-banner-emoji-left" aria-hidden="true">✨</span><div class="exam-motivation-content"><h2>✨📚 Best of Luck for Your Exam! 🍀🎯</h2><div class="exam-motivation-lines"><span>Believe in Yourself.</span><span>Stay Calm.</span><span>Read Every Question Carefully.</span><span>Manage Your Time Wisely.</span></div><p class="exam-motivation-note">Success comes to those who prepare with dedication.</p><p class="exam-motivation-closing">We wish you all the very best for your examination!</p><p class="exam-motivation-footer" aria-hidden="true">🌟📖💯🚀</p></div><span class="exam-banner-emoji exam-banner-emoji-right" aria-hidden="true">🍀</span></section>""", unsafe_allow_html=True)
    render_page_header("Important Instructions", st.session_state.topic, "Before you begin")
    col1, col2, col3 = st.columns([1, 4, 1])
    with col2:
        with st.container(border=True):
            st.markdown("### Assessment Guidelines")
            att_data = get_attempt_data(st.session_state.current_user, st.session_state.current_test_filename)
            used = att_data.get('used', 0); allowed = att_data.get('allowed', 5); curr_att = used + 1
            if allowed >= 99: st.markdown(f"🔹 **Attempt Number:** Attempt {curr_att} (Unlimited Attempts)")
            else: st.markdown(f"🔹 **Attempt Number:** Attempt {curr_att} of {allowed}")
            st.markdown(f"🔹 **Total Questions:** {len(st.session_state.questions)}")
            st.markdown(f"🔹 **Time Limit:** {st.session_state.time_val} Min" if st.session_state.timer_mode != "No Timer" else "🔹 **Time Limit:** None")
            nm = get_neg_mark(st.session_state.current_test_filename)
            if nm > 0: st.markdown(f"🔹 **Penalty:** -{nm} marks per incorrect answer.")
            st.markdown("🔹 **Navigation:** Jump to any question using the Palette.\n🔹 **Auto-Pause:** Exam freezes automatically after 5 minutes of total inactivity.\n🔹 **Submission:** Auto-submits precisely when the timer hits zero.")
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
            st.markdown("<p style='text-align: center; opacity:0.8;'>Your timer is frozen and progress cached securely.</p>", unsafe_allow_html=True)
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
            
    with col_pal:
        with st.container(border=True):
            st.markdown("<p class='palette-title'>Exam Controls & Timer</p>", unsafe_allow_html=True)
            render_visual_timer()
            st.write("<div style='margin-top:6px;'></div>", unsafe_allow_html=True)
            st.button("⏸ Pause Exam", type="secondary", on_click=pause_exam, use_container_width=True)
            
            udisp = st.session_state.current_user.split()[0]
            html_legend = f"""<div class="legend-box"><div style="display:flex; align-items:center; gap:8px; margin-bottom:10px;"><div style="width:24px; height:24px; background:linear-gradient(135deg, #4f46e5, #6366f1); color:white; border-radius:50%; display:flex; justify-content:center; align-items:center; font-weight:bold; font-size:11px;">{udisp[0].upper()}</div><span class="legend-title">{udisp}'s Session</span></div><div style="display:grid; grid-template-columns:1fr 1fr; gap:8px 4px; font-size:10px;"><div style="display:flex; align-items:center; gap:4px;"><div style="width:14px; height:14px; background:#16a34a; border: 1px solid #16a34a; border-radius:4px; display:flex; align-items:center; justify-content:center;"></div><span class="legend-text">Answered</span></div><div style="display:flex; align-items:center; gap:4px;"><div style="width:14px; height:14px; background:#7c3aed; border: 1px solid #7c3aed; border-radius:4px; display:flex; align-items:center; justify-content:center;"></div><span class="legend-text">Marked</span></div><div style="display:flex; align-items:center; gap:4px;"><div style="width:14px; height:14px; background:transparent; border:1px solid #cbd5e1; border-radius:4px; display:flex; align-items:center; justify-content:center;"></div><span class="legend-text">Not Visited</span></div><div style="display:flex; align-items:center; gap:4px;"><div style="width:14px; height:14px; background:#ef4444; border: 1px solid #ef4444; border-radius:4px; display:flex; align-items:center; justify-content:center;"></div><span class="legend-text">Not Answered</span></div><div style="display:flex; align-items:center; gap:4px; grid-column:span 2;"><div style="width:14px; height:14px; background:#7c3aed; border: 1px solid #7c3aed; border-radius:4px; position:relative;"><div style="position:absolute; bottom:-3px; right:-3px; width:7px; height:7px; background:#16a34a; border-radius:50%; border:1px solid white;"></div></div><span class="legend-text" style="margin-left: 2px;">Marked and Answered</span></div></div></div>"""
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
        body {{ margin:0; padding:0; font-family:Inter,sans-serif; background: transparent; }}
        .palette-grid {{ display:grid; grid-template-columns:repeat(5, 1fr); gap:6px; padding:4px; }}
        .q-btn {{ aspect-ratio:1/1; display:flex; align-items:center; justify-content:center; font-size:12px; font-weight:700; cursor:pointer; border-radius:6px; border:1px solid #cbd5e1; user-select:none; transition:all 0.2s; }}
        .q-btn:hover {{ transform:translateY(-2px); box-shadow:0 4px 8px rgba(0,0,0,0.1); }}
        .notvisited {{ background:#fff; color:#334155; }} .notanswered {{ background:#ef4444; color:#fff; border-color:#ef4444; }} .answered {{ background:#16a34a; color:#fff; border-color:#16a34a; }} .marked {{ background:#7c3aed; color:#fff; border-color:#7c3aed; }} .answeredmarked {{ background:#7c3aed; color:#fff; border-color:#7c3aed; position:relative; }} .answeredmarked::after {{ content:''; position:absolute; bottom:-3px; right:-3px; width:8px; height:8px; background:#16a34a; border-radius:50%; border:1px solid white; }}
        .current {{ outline:2px solid #2563eb; outline-offset:2px; transform:scale(1.05); z-index:2; border-color:transparent; }}
        @media (prefers-color-scheme: dark) {{ .notvisited {{ background:#1e293b; color:#cbd5e1; border-color:#334155; }} .answeredmarked::after {{ border-color: #0f172a; }} }}
        </style></head><body><div class="palette-grid">{grid_html}</div><script>
        function mapAndHide() {{ try {{ const pDoc = window.parent.document; const m = pDoc.getElementById('hidden-engine-marker'); if(m) {{ const d=m.closest('details'); if(d)d.style.display='none'; const e=m.closest('div[data-testid="stExpander"]'); if(e)e.style.display='none'; }} pDoc.querySelectorAll('button').forEach(b => {{ if(b.innerText&&b.innerText.includes('HBTN_')) window.hiddenMap[b.innerText.split('_')[1].trim()] = b; }}); }}catch(e){{}} }}
        window.hiddenMap = {{}}; document.addEventListener("DOMContentLoaded", function() {{ mapAndHide(); setTimeout(mapAndHide, 50); setTimeout(mapAndHide, 200); document.querySelectorAll('.q-btn').forEach(i => {{ i.addEventListener('click', function() {{ let id=this.getAttribute('data-idx'); if(window.hiddenMap[id]) window.hiddenMap[id].click(); else {{mapAndHide(); if(window.hiddenMap[id])window.hiddenMap[id].click();}} }}); }}); }});
        </script></body></html>"""
        components.html(full_html, height=280, scrolling=True)

        st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)
        b1, b2 = st.columns(2)
        b1.button("Question Paper", use_container_width=True)
        b2.button("Instructions", use_container_width=True)
        st.write("<br>", unsafe_allow_html=True)
        if st.button("🚀 Final Submit", type="primary", use_container_width=True):
            with st.spinner("Submitting responses securely..."):
                nav_submit()
                st.rerun()

    with col_main:
        st.markdown(f"<p class='exam-kicker' style='font-weight:700; opacity:0.8;'>Live Assessment &middot; {st.session_state.topic}</p>", unsafe_allow_html=True)
        st.progress((q_idx + 1) / total_q)
        
        with st.container(border=False):
            raw_q = q_data['q']
            clean_q = re.sub(r'^[Qq]?(?:uestion)?\s*\d+[\.\)]\s*', '', raw_q)
            st.markdown(f"""
                <section class="question-card">
                    <span class="question-card__number" style="font-weight:700; opacity:0.8; font-size:0.9rem;">Question {q_idx + 1} of {total_q}</span>
                    <p class="question-card__text" style="font-size:1.15rem; font-weight:600; margin-top:8px;">{clean_q}</p>
                </section>
                """, unsafe_allow_html=True)
            
            if q_data.get('type') == 'match':
                saved_ans = st.session_state.user_answers.get(q_idx, {})
                m_col1, m_col2 = st.columns(2)
                m_col1.markdown("<div style='font-weight:800; font-size:0.85rem; opacity:0.8; text-transform:uppercase; border-bottom:2px solid rgba(128,128,128,0.2); padding-bottom:8px;'>Column A (Fixed)</div>", unsafe_allow_html=True)
                m_col2.markdown("<div style='font-weight:800; font-size:0.85rem; opacity:0.8; text-transform:uppercase; border-bottom:2px solid rgba(128,128,128,0.2); padding-bottom:8px;'>Column B (Select Target)</div>", unsafe_allow_html=True)
                for l_item in q_data['left']:
                    r_c1, r_c2 = st.columns(2)
                    r_c1.markdown(f"<div style='padding-top:10px; font-weight:650; font-size:1.1rem;'>{l_item}</div>", unsafe_allow_html=True)
                    opts = ["-- Select Option --"] + q_data['options']
                    idx = opts.index(saved_ans.get(l_item, "-- Select Option --")) if saved_ans.get(l_item) in opts else 0
                    r_c2.selectbox("Match Target", opts, index=idx, key=f"match_{q_idx}_{l_item}", on_change=on_match_change, args=(q_idx, q_data['left']), label_visibility="collapsed")
            else:
                saved_ans = st.session_state.user_answers.get(q_idx)
                idx = q_data['options'].index(saved_ans) if saved_ans in q_data['options'] else None
                st.radio("Options:", options=q_data['options'], index=idx, key=f"radio_ans_{q_idx}", on_change=on_radio_change, args=(q_idx,), label_visibility="collapsed")

            st.markdown("<hr style='margin: 1rem 0; border: none; border-top: 1px solid rgba(128, 128, 128, 0.2);'>", unsafe_allow_html=True)
            is_cur_marked = q_idx in st.session_state.marked_questions
            act_cols = st.columns(4)
            act_cols[0].button("Clear Response", on_click=clear_answer, args=(q_idx,), use_container_width=True)
            act_cols[1].button("Unmark" if is_cur_marked else "Mark for Review", on_click=toggle_mark, args=(q_idx,), use_container_width=True)
            act_cols[2].button("Previous", on_click=nav_prev, use_container_width=True)
            if q_idx == total_q - 1: act_cols[3].button("Submit Exam", type="primary", use_container_width=True, on_click=nav_submit)
            else: act_cols[3].button("Next", type="primary", on_click=nav_next, use_container_width=True)

def render_result():
    if st.session_state.get('db_save_error'):
        st.error(f"⚠️ Critical Database Error: Could not save your result. Error details: {st.session_state.db_save_error}")
        st.warning("Admin Hint: Go to Supabase -> Table Editor -> 'exam_history'. Make sure **Row Level Security (RLS)** is Disabled, and all columns exist with exact names/types.")
        st.session_state.db_save_error = None # Clear error after showing

    history = get_supabase_history(st.session_state.current_user)
    
    if not history:
        st.info("No result data available. (If you just completed a test and see this, your data was not saved to the cloud).")
        return
        
    idx = st.session_state.get('history_view_index', -1)
    if idx == -1 or idx >= len(history): idx = len(history) - 1
    
    att = history[idx]
    total_q = att['total_questions']
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col1:
        if st.button("← Previous Test", disabled=(idx == 0), use_container_width=True):
            st.session_state.history_view_index = idx - 1; st.rerun()
    with col3:
        if st.button("Next Test →", disabled=(idx == len(history)-1), use_container_width=True):
            st.session_state.history_view_index = idx + 1; st.rerun()
            
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
            st.markdown(f"<div style='font-size:1.15rem; font-weight:700; margin-bottom:8px;'>Q{qd['q_num']}: {qd['question']}</div>", unsafe_allow_html=True)
            
            c_a, c_b = st.columns(2)
            c_a.markdown(f"<span style='font-size:0.8rem; font-weight:700; text-transform:uppercase; opacity:0.8;'>Your Selection</span>", unsafe_allow_html=True)
            if qd['status'] == "Unanswered": c_a.warning("Not Attempted")
            elif qd['status'] == "Incorrect": c_a.error(qd['user_ans'])
            else: c_a.success(qd['user_ans'])
                
            c_b.markdown(f"<span style='font-size:0.8rem; font-weight:700; text-transform:uppercase; opacity:0.8;'>Correct Engine Answer</span>", unsafe_allow_html=True)
            c_b.info(qd['correct_ans'])
            
            st.markdown(f"<div style='margin-top:10px; font-size:0.85rem; font-weight:600; opacity:0.9;'>Validation: <span style='color:{'#16a34a' if qd['status']=='Correct' else '#dc2626' if qd['status']=='Incorrect' else '#d97706'}'>{qd['status']}</span> &middot; Marks: {qd['marks']} &middot; Penalty: -{qd['negative']:.2f}</div></div>", unsafe_allow_html=True)

# ==========================================
# 7. MAIN APPLICATION LOOP
# ==========================================
def main():
    init_session()
    
    # Check folder creation from Supabase safely
    check_and_create_default_folders()
    
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
