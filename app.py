import streamlit as st
import csv
import os
import time
from datetime import datetime

# ==========================================
# 1. PAGE CONFIGURATION & PREMIUM CSS
# ==========================================
st.set_page_config(page_title="Study Booster", page_icon="🎓", layout="wide", initial_sidebar_state="expanded")

# Ultra-Professional EdTech UI CSS
st.markdown("""
    <style>
    /* Clean Light Background for entire app */
    .stApp { background-color: #F4F7FB; color: #1E293B; }
    
    /* Center align the login card */
    .login-container {
        background-color: white;
        padding: 3rem;
        border-radius: 12px;
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
        text-align: center;
    }
    
    /* Professional EdTech Buttons (Primary) */
    div.stButton > button[kind="primary"] {
        background-color: #4F46E5 !important;
        color: white !important;
        border: none !important;
        border-radius: 6px !important;
        font-weight: 600 !important;
        padding: 0.5rem 1rem !important;
        width: 100%;
        transition: all 0.3s ease;
    }
    div.stButton > button[kind="primary"]:hover {
        background-color: #4338CA !important;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
    }
    
    /* Secondary Buttons */
    div.stButton > button[kind="secondary"] {
        background-color: white !important;
        color: #4F46E5 !important;
        border: 1px solid #4F46E5 !important;
        border-radius: 6px !important;
        font-weight: 600 !important;
    }
    
    /* Inputs & Radios styling */
    .stTextInput > div > div > input {
        border-radius: 6px;
        border: 1px solid #CBD5E1;
    }
    
    /* Headings */
    h1, h2, h3 { color: #0F172A !important; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }
    
    /* Top Right Button Alignment hack */
    .top-right-btn { display: flex; justify-content: flex-end; }
    </style>
""", unsafe_allow_html=True)

CSV_FOLDER = 'saved_csvs'
if not os.path.exists(CSV_FOLDER): os.makedirs(CSV_FOLDER)

# Configuration
ALLOWED_USERS = {
    "Jiten (Admin)": "admin123",
    "Rahul (Student)": "rahul2026",
    "Amit (Student)": "amit999"
}

# ==========================================
# 2. SESSION STATE MANAGEMENT
# ==========================================
if 'auth' not in st.session_state:
    st.session_state.update({
        'auth': False, 'current_user': "", 'questions': [], 'current_q': 0,
        'user_answers': {}, 'quiz_completed': False, 'quiz_ready': False,
        'topic': "", 'start_time': 0
    })

# ==========================================
# 3. PROFESSIONAL LOGIN SCREEN
# ==========================================
if not st.session_state.auth:
    # 3 Columns banakar center wale me login form dalenge
    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        st.markdown("<div class='login-container'>", unsafe_allow_html=True)
        
        # Logo aur Title
        try:
            st.image("logo.png", width=100) # Ensure logo.png is in your folder
        except:
            st.markdown("<h1 style='font-size: 3rem; text-align:center;'>🎓</h1>", unsafe_allow_html=True)
            
        st.markdown("<h2 style='text-align: center;'>Study Booster Portal</h2>", unsafe_allow_html=True)
        st.write("---")
        
        username = st.selectbox("👤 Select Profile", ["-- Select User --"] + list(ALLOWED_USERS.keys()))
        pwd = st.text_input("🔑 Enter Passcode", type="password")
        
        st.write("") # spacing
        if st.button("Secure Login 🚀", type="primary"):
            if username != "-- Select User --" and ALLOWED_USERS.get(username) == pwd:
                st.session_state.auth = True
                st.session_state.current_user = username
                st.rerun()
            else:
                st.error("❌ Invalid Credentials! Please check your name and passcode.")
        st.markdown("</div>", unsafe_allow_html=True)
    st.stop()

# ==========================================
# 4. FUNCTIONS
# ==========================================
def load_quiz(file_name):
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
    st.session_state.start_time = time.time()

def generate_report(score, total):
    report = f"🎓 STUDY BOOSTER - OFFICIAL REPORT CARD 🎓\n"
    report += f"Candidate: {st.session_state.current_user}\n"
    report += f"Subject: {st.session_state.topic}\n"
    report += f"Date: {datetime.now().strftime('%d-%b-%Y %I:%M %p')}\n"
    report += "="*40 + "\n"
    report += f"SCORE: {score} out of {total}\n"
    report += "="*40 + "\n\n--- DETAILED ANSWER KEY ---\n"
    
    for i, q in enumerate(st.session_state.questions):
        report += f"Q{i+1}: {q['q']}\n"
        user_ans = st.session_state.user_answers.get(i, "Not Attempted")
        correct_ans = q['options'][q['ans']]
        report += f"Your Answer: {user_ans}\n"
        report += f"Correct Answer: {correct_ans}\n\n"
    return report

# ==========================================
# 5. SIDEBAR NAVIGATION
# ==========================================
st.sidebar.markdown(f"### 👤 {st.session_state.current_user}")
st.sidebar.write("---")

# Conditional Menu based on Role
if "Admin" in st.session_state.current_user:
    menu = st.sidebar.radio("Navigation", ["📚 Load Quiz", "📝 Live Exam", "⚙️ Manage Database"])
else:
    menu = st.sidebar.radio("Navigation", ["📚 Load Quiz", "📝 Live Exam"])

st.sidebar.write("---")
if st.sidebar.button("🚪 Logout", type="secondary"):
    st.session_state.auth = False
    st.rerun()

# ==========================================
# 6. LOAD QUIZ MODULE (Dashboard)
# ==========================================
if menu == "📚 Load Quiz":
    st.header("Welcome to Study Booster! 🚀")
    
    if "Admin" in st.session_state.current_user:
        with st.expander("➕ Upload New Quiz File"):
            uploaded_file = st.file_uploader("Upload CSV", type=['csv'])
            if uploaded_file:
                with open(os.path.join(CSV_FOLDER, uploaded_file.name), "wb") as f:
                    f.write(uploaded_file.getbuffer())
                st.success("Test uploaded successfully!")
    
    st.subheader("Available Test Series")
    files = [f for f in os.listdir(CSV_FOLDER) if f.endswith('.csv')]
    
    if not files:
        st.info("No test series available right now.")
    else:
        for file in files:
            col1, col2 = st.columns([4, 1])
            with col1:
                st.markdown(f"#### 📄 {file.replace('.csv', '')}")
            with col2:
                if st.button("Load Quiz", key=f"load_{file}", type="primary"):
                    load_quiz(file)
                    st.success(f"Quiz Loaded! Go to 'Live Exam' from sidebar.")

# ==========================================
# 7. LIVE EXAM MODULE (The Real Deal)
# ==========================================
elif menu == "📝 Live Exam":
    if not st.session_state.quiz_ready:
        st.warning("⚠️ No active test. Please load a quiz first.")
        st.stop()
        
    # --- RESULT SCREEN ---
    if st.session_state.quiz_completed:
        total_q = len(st.session_state.questions)
        score = sum(1 for i, q in enumerate(st.session_state.questions) if st.session_state.user_answers.get(i) == q['options'][q['ans']])
        
        st.header("🏆 Performance Analysis")
        st.success("Exam submitted successfully!")
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Total Questions", total_q)
        c2.metric("Attempted", len(st.session_state.user_answers))
        c3.metric("Final Score", f"{score} / {total_q}")
        
        if score == total_q and total_q > 0: st.balloons()
        
        st.write("---")
        report_data = generate_report(score, total_q)
        st.download_button("📥 Download Detailed Report Card", data=report_data, file_name=f"{st.session_state.topic}_Result.txt")
        
    # --- ACTIVE EXAM SCREEN ---
    else:
        q_idx = st.session_state.current_q
        total_q = len(st.session_state.questions)
        q_data = st.session_state.questions[q_idx]

        # Top Bar: Topic Name & Submit Button (Right side)
        c_title, c_btn = st.columns([4, 1])
        with c_title:
            st.markdown(f"<h3 style='color:#4F46E5;'>{st.session_state.topic}</h3>", unsafe_allow_html=True)
        with c_btn:
            is_last = (q_idx == total_q - 1)
            btn_txt = "Submit Exam 🚀" if is_last else "Next Question ➡️"
            if st.button(btn_txt, type="primary"):
                if st.session_state.get('curr_choice'):
                    st.session_state.user_answers[q_idx] = st.session_state.curr_choice
                    if is_last:
                        st.session_state.quiz_completed = True
                    else:
                        st.session_state.current_q += 1
                    st.rerun()
                else:
                    st.error("⚠️ Please select an answer to proceed!")

        st.progress((q_idx) / total_q)
        st.write("---")
        
        # Question Area
        st.markdown(f"#### Q{q_idx + 1}. {q_data['q']}")
        
        # Options Radio
        saved_ans = st.session_state.user_answers.get(q_idx, None)
        try:
            def_idx = q_data['options'].index(saved_ans) if saved_ans else None
        except:
            def_idx = None
            
        st.session_state.curr_choice = st.radio("Select your option:", q_data['options'], index=def_idx)

# ==========================================
# 8. MANAGE DATABASE (Admin Only)
# ==========================================
elif menu == "⚙️ Manage Database":
    st.header("Database & Server Management")
    files = [f for f in os.listdir(CSV_FOLDER) if f.endswith('.csv')]
    
    if not files:
        st.info("No files in database.")
    else:
        for file in files:
            file_path = os.path.join(CSV_FOLDER, file)
            dt = datetime.fromtimestamp(os.path.getmtime(file_path)).strftime("%d %b %Y")
            
            c1, c2, c3 = st.columns([3, 2, 1])
            c1.write(f"**{file}**")
            c2.write(dt)
            if c3.button("Delete ❌", key=f"del_{file}"):
                os.remove(file_path)
                st.rerun()
