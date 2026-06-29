import streamlit as st
import pypdf
import json
import time
import pandas as pd
import google.generativeai as genai

# -----------------------------------------------------------------------------
# 1. PAGE SETUP & SESSION STATE INITIALIZATION
# -----------------------------------------------------------------------------
st.set_page_config(page_title="CFA Level I Mock Simulator", layout="wide")

if "step" not in st.session_state:
    st.session_state.step = "upload"  # upload -> exam -> dashboard
if "questions" not in st.session_state:
    st.session_state.questions = []
if "user_answers" not in st.session_state:
    st.session_state.user_answers = {}
if "flags" not in st.session_state:
    st.session_state.flags = {}
if "time_logs" not in st.session_state:
    st.session_state.time_logs = {}
if "current_index" not in st.session_state:
    st.session_state.current_index = 0
if "exam_start_time" not in st.session_state:
    st.session_state.exam_start_time = 0
if "last_switch_time" not in st.session_state:
    st.session_state.last_switch_time = 0

# -----------------------------------------------------------------------------
# 2. HELPER FUNCTIONS: PDF PARSING & AI ENGINE
# -----------------------------------------------------------------------------
def extract_text_from_pdf(file):
    reader = pypdf.PdfReader(file)
    text = ""
    for page in reader.pages:
        text += page.extract_text() + "\n"
    return text

def parse_pdfs_with_ai(api_key, q_text, a_text):
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    prompt = f"""
    You are an expert CFA Level 1 preparation engine. Pair the following question texts with their respective correct answers and solutions. Split them into an exact list of individual structural questions.
    
    CRITICAL SCHEMA: You must return valid JSON matching this exact structure:
    [
      {{
        "question_id": 1,
        "topic_area": "Exact CFA Topic Name (e.g., Quantitative Methods, Financial Statement Analysis, Fixed Income, Corporate Issuers, Economics, Derivatives, Alternative Investments, Equity Investments, Portfolio Management, Ethical and Professional Standards)",
        "stem": "The clear question text",
        "options": {{"A": "Option text A", "B": "Option text B", "C": "Option text C"}},
        "correct_answer": "A, B, or C",
        "concept_or_formula_tested": "Specific name of formula or concept tested",
        "explanation_correct": "Clear narrative why the correct option is right.",
        "explanation_incorrect": "Clear narrative why the other two options are wrong."
      }}
    ]

    QUESTION PDF TEXT:
    {q_text[:40000]}
    
    ANSWER PDF TEXT:
    {a_text[:40000]}
    """
    
    response = model.generate_content(
        prompt, 
        generation_config={"response_mime_type": "application/json"}
    )
    return json.loads(response.text)

# -----------------------------------------------------------------------------
# STEP 1: UPLOAD SCREEN
# -----------------------------------------------------------------------------
if st.session_state.step == "upload":
    st.title("📚 CFA Level I Mock Simulator Configuration")
    st.write("Upload your mock exam documents to generate your custom testing portal.")
    
    api_key = st.text_input("Enter Gemini API Key", type="password", help="Get a free key from Google AI Studio")
    
    col1, col2 = st.columns(2)
    with col1:
        q_file = st.file_uploader("Upload Questions PDF", type=["pdf"])
    with col2:
        a_file = st.file_uploader("Upload Answers & Solutions PDF", type=["pdf"])
        
    if st.button("Build Exam Environment", type="primary"):
        if not api_key or not q_file or not a_file:
            st.error("Please fill in all fields and upload both files.")
        else:
            with st.spinner("AI is breaking down the exam papers into structural data... Please wait."):
                try:
                    q_text = extract_text_from_pdf(q_file)
                    a_text = extract_text_from_pdf(a_file)
                    parsed_data = parse_pdfs_with_ai(api_key, q_text, a_text)
                    
                    st.session_state.questions = parsed_data
                    # Initialize user states
                    for q in parsed_data:
                        qid = q["question_id"]
                        st.session_state.user_answers[qid] = None
                        st.session_state.flags[qid] = False
                        st.session_state.time_logs[qid] = 0.0
                    
                    st.session_state.step = "exam"
                    st.session_state.exam_start_time = time.time()
                    st.session_state.last_switch_time = time.time()
                    st.rerun()
                except Exception as e:
                    st.error(f"Parsing error: {str(e)}. Please check your file sizes or key.")

# -----------------------------------------------------------------------------
# STEP 2: PROMETRIC-STYLE EXAM ENVIRONMENT
# -----------------------------------------------------------------------------
elif st.session_state.step == "exam":
    # Global Timer Calculation (135 minutes = 8100 seconds)
    elapsed_total = time.time() - st.session_state.exam_start_time
    remaining_total = max(8100 - elapsed_total, 0)
    
    if remaining_total <= 0:
        st.session_state.step = "dashboard"
        st.rerun()
        
    mins, secs = divmod(int(remaining_total), 60)
    hours, mins = divmod(mins, 60)
    
    # Header bar
    h_col1, h_col2, h_col3 = st.columns([2, 2, 1])
    with h_col1:
        st.subheader("CFA Institute Official Mock Simulation Environment")
    with h_col2:
        st.metric("Time Remaining", f"{hours:02d}:{mins:02d}:{secs:02d}")
    with h_col3:
        if st.button("Submit Exam", type="secondary"):
            # Log time for the final active question before leaving
            current_q_id = st.session_state.questions[st.session_state.current_index]["question_id"]
            now = time.time()
            st.session_state.time_logs[current_q_id] += (now - st.session_state.last_switch_time)
            st.session_state.step = "dashboard"
            st.rerun()

    st.markdown("---")
    
    # Active Question Data Load
    q_data = st.session_state.questions[st.session_state.current_index]
    qid = q_data["question_id"]
    
    # Body Architecture
    body_col1, body_col2 = st.columns([3, 1])
    
    with body_col1:
        st.caption(f"Topic Focus: **{q_data['topic_area']}**")
        st.markdown(f"### Question {qid}")
        st.markdown(q_data["stem"])
        
        # Options mapping
        opts = q_data["options"]
        current_selection = st.session_state.user_answers[qid]
        
        # Convert A, B, C selections back to index numbers for radio component stability
        opt_index = None
        if current_selection == "A": opt_index = 0
        elif current_selection == "B": opt_index = 1
        elif current_selection == "C": opt_index = 2
            
        choice = st.radio(
            "Select your answer:",
            options=["A", "B", "C"],
            format_func=lambda x: f"{x}) {opts[x]}",
            index=opt_index,
            key=f"radio_{qid}"
        )
        st.session_state.user_answers[qid] = choice
        
        # Lower Action Bar
        st.write("")
        b_col1, b_col2, b_col3 = st.columns(3)
        
        with b_col1:
            if st.button("◀ Previous", disabled=(st.session_state.current_index == 0)):
                now = time.time()
                st.session_state.time_logs[qid] += (now - st.session_state.last_switch_time)
                st.session_state.current_index -= 1
                st.session_state.last_switch_time = now
                st.rerun()
        with b_col2:
            st.session_state.flags[qid] = st.checkbox("🚩 Flag for Review", value=st.session_state.flags[qid], key=f"flag_{qid}")
        with b_col3:
            if st.button("Next ▶", disabled=(st.session_state.current_index == len(st.session_state.questions) - 1)):
                now = time.time()
                st.session_state.time_logs[qid] += (now - st.session_state.last_switch_time)
                st.session_state.current_index += 1
                st.session_state.last_switch_time = now
                st.rerun()

    with body_col2:
        st.markdown("##### Navigation Grid")
        # Build out a grid matrix visualizer
        num_questions = len(st.session_state.questions)
        grid_cols = st.columns(5)
        for idx in range(num_questions):
            q_num = idx + 1
            target_id = st.session_state.questions[idx]["question_id"]
            
            # Formulate UI indicators based on user status
            status_label = f"{q_num}"
            if st.session_state.flags[target_id]:
                status_label += " 🚩"
            elif st.session_state.user_answers[target_id] is not None:
                status_label += " 🔹"
                
            col_target = grid_cols[idx % 5]
            if col_target.button(status_label, key=f"nav_btn_{idx}"):
                now = time.time()
                st.session_state.time_logs[qid] += (now - st.session_state.last_switch_time)
                st.session_state.current_index = idx
                st.session_state.last_switch_time = now
                st.rerun()

# -----------------------------------------------------------------------------
# STEP 3: PERFORMANCE METRICS & DASHBOARD REVIEW
# -----------------------------------------------------------------------------
elif st.session_state.step == "dashboard":
    st.title("📊 Official CFA Performance Analytics Dashboard")
    
    # Process scores datasets
    records = []
    for q in st.session_state.questions:
        qid = q["question_id"]
        u_ans = st.session_state.user_answers[qid]
        c_ans = q["correct_answer"]
        is_correct = (u_ans == c_ans)
        
        records.append({
            "Question ID": qid,
            "Topic Area": q["topic_area"],
            "Concept/Formula": q["concept_or_formula_tested"],
            "Your Answer": u_ans if u_ans else "Unanswered",
            "Correct Answer": c_ans,
            "Status": "Correct" if is_correct else "Incorrect",
            "Time Spent (s)": round(st.session_state.time_logs[qid], 1),
            "Explanation Correct": q["explanation_correct"],
            "Explanation Incorrect": q["explanation_incorrect"]
        })
        
    df = pd.DataFrame(records)
    
    # Global Level Aggregations
    total_q = len(df)
    correct_q = len(df[df["Status"] == "Correct"])
    score_percentage = (correct_q / total_q) * 100 if total_q > 0 else 0
    
    m1, m2, m3 = st.columns(3)
    m1.metric("Overall Score Achievement", f"{score_percentage:.1f}%", help="CFA Minimum Pass Score typically ranges between 65%-70%")
    m2.metric("Total Questions Graded", f"{correct_q} / {total_q}")
    m3.metric("Total Study Testing Time Allocated", f"{round(df['Time Spent (s)'].sum() / 60, 1)} minutes")
    
    st.markdown("---")
    
    tab1, tab2 = st.tabs(["📋 Question-Wise Analysis", "⚠️ Topics to Revisit Matrix"])
    
    with tab1:
        st.subheader("Granular Question Breakdown")
        st.write("Click on any row element below to review individual metrics, duration metrics, formulas, and deep logic breakdowns.")
        
        for index, row in df.iterrows():
            status_color = "🟢" if row["Status"] == "Correct" else "🔴"
            expander_title = f"{status_color} Question {row['Question ID']} | Topic: {row['Topic Area']} | Time: {row['Time Spent (s)']}s"
            
            with st.expander(expander_title):
                st.write(f"**Target Concept / Formula Demanded:** `{row['Concept/Formula']}`")
                st.write(f"**Your Choice:** `{row['Your Answer']}` | **Correct Choice:** `{row['Correct Answer']}`")
                st.markdown("##### Performance Rationales")
                st.info(f"**Why the correct option is right:**\n{row['Explanation Correct']}")
                st.warning(f"**Why alternative options failed criteria:**\n{row['Explanation Incorrect']}")
                
    with tab2:
        st.subheader("Actionable Remediation Roadmap")
        st.write("These concepts were missed during your simulation. Focus core studies here to optimize recovery before exam day.")
        
        incorrect_df = df[df["Status"] == "Incorrect"]
        
        if len(incorrect_df) == 0:
            st.success("Excellent performance profile. Zero high-risk category items detected.")
        else:
            # Table View
            display_table = incorrect_df[["Topic Area", "Concept/Formula", "Time Spent (s)"]].reset_index(drop=True)
            st.table(display_table)
            
            # Text List Summarization
            st.markdown("🔍 **Bullet Checklist for Active Review:**")
            for topic in display_table["Topic Area"].unique():
                concepts = display_table[display_table["Topic Area"] == topic]["Concept/Formula"].tolist()
                st.markdown(f"* **{topic}**: Re-study expressions related to *{', '.join(concepts)}*")
                
    if st.button("Restart New Session Run"):
        st.session_state.clear()
        st.rerun()