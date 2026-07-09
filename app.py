import streamlit as st
import csv
import os
import time
from datetime import datetime

# ==========================================
# PAGE CONFIGURATION
# ==========================================
st.set_page_config(page_title="Ultra Pro Quiz App", page_icon="🎓", layout="centered")

CSV_FOLDER = 'saved_csvs'
if not os.path.exists(CSV_FOLDER):
    os.makedirs(CSV_FOLDER)

# 🔒 SECRET PASSWORD
SECRET_PASSCODE = "PROQUIZ2026" 

ALLOWED_USERS = {
    "Jiten (Admin)": "admin123",
    "Rahul": "rahul2026",
    "Amit": "amit999",
    "Priya": "pass1234"
}

# ==========================================
# SESSION STATE (Memory)
# ==========================================
if 'auth' not in st.session_state:
    st.session_state.auth = False
    st.session_state.current_user = ""
if 'questions' not in st.session_state:
    st.session_state.questions = []
    st.session_state.current_q = 0
    st.session_state.topic = "General Quiz"
    
    # Naye variables (Real Exam Mode ke liye)
    st.session_state.user_answers = {} # User ke saare answers yahan save honge
    st.session_state.quiz_completed = False # Quiz khatam hua ya nahi
    
    st.session_state.timer_mode = "No Timer"
    st.session_state.time_val = 0
    st.session_state.start_timestamp = 0.0
    st.session_state.q_start_timestamp = 0.0

# ==========================================
# AUTHENTICATION SCREEN
# ==========================================
if not st.session_state.auth:
    st.title("🔒 Secure Login Area")
    st.write("Kripya apna naam chunein aur apna password dalein.")
    
    username = st.selectbox("Apna Naam Select Karein:", ["-- Select User --"] + list(ALLOWED_USERS.keys()))
    pwd = st.text_input("Enter Passcode:", type="password")
    
    if st.button("Login 🚀", type="primary"):
        if username == "-- Select User --":
            st.warning("Pehle apna naam select karein!")
        elif username in ALLOWED_USERS and ALLOWED_USERS[username] == pwd:
            st.session_state.auth = True
            st.session_state.current_user = username
            st.success(f"Welcome back, {username}!")
            st.rerun()
        else:
            st.error("❌ Galat Password! Kripya sahi code dalein.")
    st.stop()

# ==========================================
# FUNCTIONS
# ==========================================
def load_csv(file_path, file_name):
    encodings = ['utf-8-sig', 'utf-8', 'cp1252', 'latin-1']
    success = False
    for enc in encodings:
        try:
            temp_q = []
            with open(file_path, 'r', encoding=enc, errors='ignore') as f:
                reader = csv.DictReader(f)
                if 'Question' not in reader.fieldnames:
                    continue
                for row in reader:
                    q = row['Question']
                    options = [row['Option1'], row['Option2'], row['Option3'], row['Option4'], row['Option5']]
                    ans = int(row['Answer']) - 1
                    temp_q.append({'q': q, 'options': options, 'ans': ans})
            
            st.session_state.questions = temp_q
            raw_name = os.path.splitext(file_name)[0]
            st.session_state.topic = raw_name.replace('_', ' ').replace('-', ' ').title()
            success = True
            break
        except Exception:
            continue
    return success

def reset_quiz(t_mode, t_val):
    st.session_state.current_q = 0
    st.session_state.user_answers = {}
    st.session_state.quiz_completed = False
    
    st.session_state.timer_mode = t_mode
    st.session_state.time_val = t_val
    st.session_state.start_timestamp = time.time()
    st.session_state.q_start_timestamp = time.time()

def calculate_results():
    score = 0
    attempted = 0
    
    for i, q_data in enumerate(st.session_state.questions):
        user_ans = st.session_state.user_answers.get(i)
        if user_ans and user_ans != "TIMEOUT":
            attempted += 1
            correct_text = q_data['options'][q_data['ans']]
            if user_ans == correct_text:
                score += 1
                
    return score, attempted

def generate_report(score, attempted):
    total_q = len(st.session_state.questions)
    report = f"🏆 OFFICIAL QUIZ REPORT CARD 🏆\n"
    report += f"Student Name: {st.session_state.current_user}\n"
    report += f"Topic: {st.session_state.topic}\n"
    report += f"Timer Mode: {st.session_state.timer_mode}\n"
    report += f"Date: {datetime.now().strftime('%d-%b-%Y %I:%M %p')}\n"
    report += "-"*40 + "\n"
    report += f"Total Questions: {total_q}\n"
    report += f"Attempted: {attempted}\n"
    report += f"Correct: {score}\n"
    report += f"Wrong / Time Out: {attempted - score}\n"
    report += "-"*40 + "\n"
    report += f"FINAL SCORE: {score} / {total_q}\n\n"
    
    report += "=== DETAILED ANSWER KEY ===\n"
    for i, q in enumerate(st.session_state.questions):
        report += f"Q{i+1}: {q['q']}\n"
        user_ans = st.session_state.user_answers.get(i, "Not Attempted")
        correct_ans = q['options'][q['ans']]
        report += f"Your Answer: {user_ans}\n"
        report += f"Correct Answer: {correct_ans}\n\n"
        
    return report

# ==========================================
# SIDEBAR NAVIGATION
# ==========================================
st.sidebar.title(f"👤 {st.session_state.current_user}")
st.sidebar.divider()

menu = st.sidebar.radio("Menu Options", ["🏠 Dashboard (Upload)", "🎮 Take Quiz", "📁 Manage CSVs"])

st.sidebar.divider()
if st.sidebar.button("🚪 Logout", type="primary"):
    st.session_state.auth = False
    st.session_state.current_user = ""
    st.session_state.questions = []
    st.rerun()

# ==========================================
# PAGE 1: DASHBOARD & UPLOAD
# ==========================================
if menu == "🏠 Dashboard (Upload)":
    st.title("Welcome to Ultra Pro Quiz! 🌟")
    
    if "Admin" in st.session_state.current_user:
        uploaded_file = st.file_uploader("📥 Drag & Drop your CSV file here", type=['csv'])
        if uploaded_file is not None:
            file_path = os.path.join(CSV_FOLDER, uploaded_file.name)
            with open(file_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            st.success(f"✅ '{uploaded_file.name}' hamesha ke liye save ho gayi!")
        st.divider()
    
    st.subheader("⚙️ Timer Settings")
    t_mode = st.radio("Timer kaise set karna hai?", ["No Timer", "Total Time (Minutes)", "Time Per Question (Seconds)"], horizontal=True)
    
    t_val = 0
    if t_mode == "Total Time (Minutes)":
        t_val = st.number_input("Total time (Minutes) me dalein:", min_value=1, value=10)
    elif t_mode == "Time Per Question (Seconds)":
        t_val = st.number_input("Ek question ka time (Seconds) me dalein:", min_value=10, value=30)
        
    st.divider()
    
    st.subheader("📚 Available Topics")
    files = [f for f in os.listdir(CSV_FOLDER) if f.endswith('.csv')]
    
    if not files:
        st.info("Abhi tak koi quiz file upload nahi hui hai.")
    else:
        for file in files:
            col1, col2 = st.columns([3, 1])
            with col1:
                st.markdown(f"📄 **{file}**")
            with col2:
                if st.button("Load & Start", key=f"load_{file}", type="primary"):
                    if load_csv(os.path.join(CSV_FOLDER, file), file):
                        st.success(f"{file} loaded! Go to 'Take Quiz' to start.")
                        reset_quiz(t_mode, t_val)
                    else:
                        st.error("File headings me error hai.")

# ==========================================
# PAGE 2: TAKE QUIZ & RESULTS
# ==========================================
elif menu == "🎮 Take Quiz":
    if not st.session_state.questions:
        st.warning("⚠️ Pehle 'Dashboard' se koi file load karein.")
        
    # --- QUIZ COMPLETE HONE KE BAAD KA SCREEN (RESULT & ANSWER KEY) ---
    elif st.session_state.quiz_completed:
        total_q = len(st.session_state.questions)
        score, attempted = calculate_results()
        
        st.title("🏆 Final Result Dashboard")
        st.success("Aapka test successfully submit ho gaya hai!")
        
        # Top Metrics
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total", total_q)
        col2.metric("Attempted", attempted)
        col3.metric("Correct ✅", score)
        col4.metric("Wrong ❌", attempted - score)
        
        st.markdown(f"### 🎯 Final Marks: {score} / {total_q}")
        if score == total_q and total_q > 0:
            st.balloons()
            
        st.divider()
        
        # Download Report
        report_text = generate_report(score, attempted)
        st.download_button("📄 Download Report Card", data=report_text, file_name=f"{st.session_state.current_user}_{st.session_state.topic}_Result.txt", mime="text/plain")
        
        st.divider()
        st.header("📋 Detailed Answer Key")
        
        # Saare questions ki list, user ka answer aur sahi answer
        for i, q in enumerate(st.session_state.questions):
            st.markdown(f"**Q{i+1}: {q['q']}**")
            
            correct_ans = q['options'][q['ans']]
            user_ans = st.session_state.user_answers.get(i, "Skipped / Not Attempted")
            
            if user_ans == correct_ans:
                st.success(f"Your Answer: {user_ans} (✅ Correct)")
            elif user_ans == "TIMEOUT":
                st.error(f"⏱️ Time Out! Sahi Answer: {correct_ans}")
            elif user_ans == "Skipped / Not Attempted":
                st.warning(f"Not Attempted. Sahi Answer: {correct_ans}")
            else:
                st.error(f"Your Answer: {user_ans} (❌ Wrong)")
                st.info(f"Sahi Answer: {correct_ans}")
            st.write("---")
            
    # --- ACTIVE EXAM SCREEN ---
    else:
        q_idx = st.session_state.current_q
        total_q = len(st.session_state.questions)
        
        # Timer Display
        if st.session_state.timer_mode == "Total Time (Minutes)":
            st.info(f"⏱️ **Total Time Limit:** {st.session_state.time_val} Minutes")
        elif st.session_state.timer_mode == "Time Per Question (Seconds)":
            st.info(f"⏱️ **Time Per Question:** {st.session_state.time_val} Seconds")
            
        st.title(f"🏷️ {st.session_state.topic}")
        st.progress((q_idx) / total_q)
        
        q_data = st.session_state.questions[q_idx]
        st.markdown(f"### Q{q_idx + 1}: {q_data['q']}")
        
        # Purana answer pre-select karne ke liye (agar user previous use karta, par hum aage badh rahe hain)
        saved_ans = st.session_state.user_answers.get(q_idx, None)
        selected_opt = st.radio("Options:", q_data['options'], index=q_data['options'].index(saved_ans) if saved_ans in q_data['options'] else None)
        
        col1, col2 = st.columns([1, 4])
        with col1:
            # Agar aakhiri question nahi hai toh "Next" dikhao, warna "Final Submit"
            is_last_q = (q_idx == total_q - 1)
            btn_text = "Final Submit 🚀" if is_last_q else "Next Question ➡️"
            
            if st.button(btn_text, type="primary"):
                
                # TIMING CHECK
                time_taken = time.time() - st.session_state.q_start_timestamp
                total_time_taken = time.time() - st.session_state.start_timestamp
                
                if st.session_state.timer_mode == "Time Per Question (Seconds)" and time_taken > st.session_state.time_val:
                    st.session_state.user_answers[q_idx] = "TIMEOUT"
                elif st.session_state.timer_mode == "Total Time (Minutes)" and total_time_taken > (st.session_state.time_val * 60):
                    # Agar total time over ho gaya toh test turant submit ho jayega
                    st.warning("⏱️ Time is over! Auto-submitting the test.")
                    st.session_state.quiz_completed = True
                    st.rerun()
                else:
                    # Sahi time me answer diya hai
                    if selected_opt:
                        st.session_state.user_answers[q_idx] = selected_opt
                    else:
                        st.session_state.user_answers[q_idx] = "Skipped / Not Attempted"
                
                # Aage Badhna ya Khatam karna
                if is_last_q:
                    st.session_state.quiz_completed = True
                else:
                    st.session_state.current_q += 1
                    st.session_state.q_start_timestamp = time.time() # Reset clock for next Q
                st.rerun()

        with col2:
            if st.button("🛑 Submit Test Now"):
                # Beech me hi test submit karne ke liye
                st.session_state.quiz_completed = True
                st.rerun()

# ==========================================
# PAGE 3: MANAGE FILES
# ==========================================
elif menu == "📁 Manage CSVs":
    st.title("🗑️ Database Management")
    if "Admin" not in st.session_state.current_user:
        st.error("⚠️ Access Denied! Sirf Admin (Jiten) hi files delete kar sakta hai.")
    else:
        files = [f for f in os.listdir(CSV_FOLDER) if f.endswith('.csv')]
        if not files:
            st.info("No CSV files found in database.")
        else:
            for file in files:
                file_path = os.path.join(CSV_FOLDER, file)
                timestamp = os.path.getmtime(file_path)
                date_str = datetime.fromtimestamp(timestamp).strftime("%d %b %Y, %I:%M %p")
                
                col1, col2, col3 = st.columns([3, 2, 1])
                with col1:
                    st.markdown(f"**{file}**")
                with col2:
                    st.text(date_str)
                with col3:
                    if st.button("Delete ❌", key=f"del_{file}"):
                        os.remove(file_path)
                        st.toast(f"{file} deleted forever!")
                        st.rerun()