"""
Medical Triage System — Streamlit Frontend
==========================================
Multi-step card-based interface with:
  - Step 1: Patient demographics
  - Step 2: Chief complaint + dynamic follow-up questions
  - Step 3: Medical history
  - Step 4: Processing animation
  - Step 5: Results dashboard (patient view)
  - Doctor Dashboard tab: Full structured report

Design: Clean healthcare UI, soft blue-white theme, professional spacing.
"""

import streamlit as st
import requests
import time
import json
from datetime import datetime

# ─── Page Configuration ───────────────────────────────────────────────────────
st.set_page_config(
    page_title="MedTriage AI",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="collapsed",
)

API_BASE = "http://localhost:8000"

# ─── CSS Styling ──────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600;700&family=DM+Serif+Display:ital@0;1&display=swap');

/* ── Reset & Base ── */
* { box-sizing: border-box; }

.stApp {
    background: #f0f4f8;
    font-family: 'DM Sans', sans-serif;
}

/* ── Hide Streamlit chrome ── */
#MainMenu, footer, header { visibility: hidden; }
.block-container {
    padding: 2rem 3rem !important;
    max-width: 1100px !important;
}

/* ── Top Navigation Bar ── */
.nav-bar {
    background: white;
    border-radius: 16px;
    padding: 1rem 2rem;
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 2rem;
    box-shadow: 0 1px 20px rgba(0,80,160,0.08);
    border: 1px solid #e2eaf4;
}
.nav-logo {
    font-family: 'DM Serif Display', serif;
    font-size: 1.5rem;
    color: #1a56a0;
    letter-spacing: -0.5px;
}
.nav-logo span { color: #e74c3c; }
.nav-badge {
    background: #fef3cd;
    color: #856404;
    font-size: 0.72rem;
    font-weight: 600;
    padding: 4px 12px;
    border-radius: 20px;
    border: 1px solid #fde68a;
    letter-spacing: 0.3px;
}

/* ── Progress Bar ── */
.progress-container {
    background: white;
    border-radius: 12px;
    padding: 1.25rem 2rem;
    margin-bottom: 2rem;
    box-shadow: 0 1px 12px rgba(0,80,160,0.06);
    border: 1px solid #e2eaf4;
}
.progress-label {
    font-size: 0.8rem;
    font-weight: 600;
    color: #64748b;
    letter-spacing: 0.5px;
    text-transform: uppercase;
    margin-bottom: 0.75rem;
}
.progress-steps {
    display: flex;
    align-items: center;
    gap: 0;
}
.step-item {
    display: flex;
    flex-direction: column;
    align-items: center;
    flex: 1;
    position: relative;
}
.step-circle {
    width: 32px;
    height: 32px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 0.8rem;
    font-weight: 700;
    z-index: 2;
    transition: all 0.3s ease;
}
.step-circle.active {
    background: #1a56a0;
    color: white;
    box-shadow: 0 0 0 4px rgba(26,86,160,0.15);
}
.step-circle.done {
    background: #10b981;
    color: white;
}
.step-circle.pending {
    background: #e2eaf4;
    color: #94a3b8;
}
.step-label {
    font-size: 0.7rem;
    color: #64748b;
    margin-top: 4px;
    font-weight: 500;
    white-space: nowrap;
}
.step-line {
    height: 2px;
    flex: 1;
    margin-top: -16px;
    z-index: 1;
}
.step-line.done { background: #10b981; }
.step-line.pending { background: #e2eaf4; }

/* ── Cards ── */
.card {
    background: white;
    border-radius: 20px;
    padding: 2rem 2.5rem;
    box-shadow: 0 2px 24px rgba(0,80,160,0.07);
    border: 1px solid #e2eaf4;
    margin-bottom: 1.5rem;
    animation: slideUp 0.4s ease;
}
@keyframes slideUp {
    from { opacity: 0; transform: translateY(16px); }
    to { opacity: 1; transform: translateY(0); }
}

.card-title {
    font-family: 'DM Serif Display', serif;
    font-size: 1.4rem;
    color: #1a2b4a;
    margin-bottom: 0.25rem;
}
.card-subtitle {
    font-size: 0.875rem;
    color: #64748b;
    margin-bottom: 1.75rem;
}

/* ── Section Divider ── */
.section-label {
    font-size: 0.72rem;
    font-weight: 700;
    color: #94a3b8;
    letter-spacing: 1px;
    text-transform: uppercase;
    margin: 1.25rem 0 0.75rem 0;
    padding-bottom: 0.5rem;
    border-bottom: 1px solid #f1f5f9;
}

/* ── Form Inputs ── */
.stTextInput > div > div > input,
.stTextArea > div > div > textarea,
.stSelectbox > div > div {
    border: 1.5px solid #e2eaf4 !important;
    border-radius: 10px !important;
    font-family: 'DM Sans', sans-serif !important;
    font-size: 0.9rem !important;
    transition: border-color 0.2s ease !important;
}
.stTextInput > div > div > input:focus,
.stTextArea > div > div > textarea:focus {
    border-color: #1a56a0 !important;
    box-shadow: 0 0 0 3px rgba(26,86,160,0.08) !important;
}

/* ── Slider ── */
.stSlider > div { padding: 0 !important; }

/* ── Buttons ── */
.stButton > button {
    background: linear-gradient(135deg, #1a56a0, #2563eb) !important;
    color: white !important;
    border: none !important;
    border-radius: 10px !important;
    padding: 0.65rem 2rem !important;
    font-family: 'DM Sans', sans-serif !important;
    font-weight: 600 !important;
    font-size: 0.9rem !important;
    letter-spacing: 0.2px !important;
    transition: all 0.2s ease !important;
    box-shadow: 0 4px 14px rgba(26,86,160,0.25) !important;
}
.stButton > button:hover {
    transform: translateY(-1px) !important;
    box-shadow: 0 6px 20px rgba(26,86,160,0.35) !important;
}
.stButton > button[kind="secondary"] {
    background: white !important;
    color: #1a56a0 !important;
    border: 1.5px solid #1a56a0 !important;
    box-shadow: none !important;
}

/* ── Emergency Alert ── */
.emergency-banner {
    background: linear-gradient(135deg, #dc2626, #b91c1c);
    color: white;
    border-radius: 16px;
    padding: 1.5rem 2rem;
    margin-bottom: 1.5rem;
    animation: pulse 2s infinite;
    box-shadow: 0 8px 32px rgba(220,38,38,0.3);
}
@keyframes pulse {
    0%, 100% { box-shadow: 0 8px 32px rgba(220,38,38,0.3); }
    50% { box-shadow: 0 8px 48px rgba(220,38,38,0.5); }
}
.emergency-title {
    font-family: 'DM Serif Display', serif;
    font-size: 1.5rem;
    font-weight: 700;
    margin-bottom: 0.5rem;
}
.emergency-text { font-size: 0.95rem; opacity: 0.92; }

/* ── Urgency Badges ── */
.urgency-badge {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 6px 16px;
    border-radius: 50px;
    font-weight: 700;
    font-size: 0.85rem;
    letter-spacing: 0.5px;
}
.urgency-EMERGENCY { background: #fee2e2; color: #dc2626; border: 1.5px solid #fca5a5; }
.urgency-URGENT { background: #ffedd5; color: #ea580c; border: 1.5px solid #fdba74; }
.urgency-SEMI_URGENT { background: #fef9c3; color: #ca8a04; border: 1.5px solid #fde047; }
.urgency-NON_URGENT { background: #dcfce7; color: #16a34a; border: 1.5px solid #86efac; }

/* ── Results Cards ── */
.result-section {
    background: #f8fafc;
    border-radius: 12px;
    padding: 1.25rem 1.5rem;
    margin-bottom: 1rem;
    border: 1px solid #e2eaf4;
}
.result-section-title {
    font-size: 0.75rem;
    font-weight: 700;
    color: #64748b;
    letter-spacing: 0.8px;
    text-transform: uppercase;
    margin-bottom: 0.75rem;
}

/* ── Differential Pills ── */
.diff-pill {
    display: inline-block;
    background: #eff6ff;
    color: #1d4ed8;
    border: 1px solid #bfdbfe;
    border-radius: 8px;
    padding: 4px 12px;
    font-size: 0.82rem;
    font-weight: 500;
    margin: 3px;
}

/* ── Workup Items ── */
.workup-item {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 0.5rem 0;
    border-bottom: 1px solid #f1f5f9;
    font-size: 0.88rem;
    color: #374151;
}
.workup-item:last-child { border-bottom: none; }
.workup-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: #1a56a0;
    flex-shrink: 0;
}

/* ── Confidence Bar ── */
.conf-bar-container { margin: 0.5rem 0; }
.conf-bar-label {
    display: flex;
    justify-content: space-between;
    font-size: 0.8rem;
    color: #64748b;
    margin-bottom: 4px;
}
.conf-bar-track {
    height: 6px;
    background: #e2eaf4;
    border-radius: 3px;
    overflow: hidden;
}
.conf-bar-fill {
    height: 100%;
    border-radius: 3px;
    background: linear-gradient(90deg, #1a56a0, #10b981);
    transition: width 1s ease;
}

/* ── Doctor Dashboard ── */
.dashboard-header {
    background: linear-gradient(135deg, #0f2d5c, #1a56a0);
    color: white;
    border-radius: 20px;
    padding: 2rem 2.5rem;
    margin-bottom: 1.5rem;
}
.dashboard-title {
    font-family: 'DM Serif Display', serif;
    font-size: 1.8rem;
    margin-bottom: 0.25rem;
}
.dashboard-meta { font-size: 0.875rem; opacity: 0.8; }

.metric-grid {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 1rem;
    margin-bottom: 1.5rem;
}
.metric-card {
    background: white;
    border-radius: 14px;
    padding: 1.25rem 1.5rem;
    border: 1px solid #e2eaf4;
    box-shadow: 0 1px 8px rgba(0,80,160,0.05);
}
.metric-label {
    font-size: 0.72rem;
    font-weight: 700;
    color: #94a3b8;
    letter-spacing: 0.8px;
    text-transform: uppercase;
    margin-bottom: 0.5rem;
}
.metric-value {
    font-size: 1.25rem;
    font-weight: 700;
    color: #1a2b4a;
}

/* ── Disclaimer ── */
.disclaimer-box {
    background: #fffbeb;
    border: 1px solid #fde68a;
    border-radius: 10px;
    padding: 1rem 1.25rem;
    font-size: 0.8rem;
    color: #92400e;
    margin-top: 1.5rem;
    line-height: 1.5;
}

/* ── Loading Spinner ── */
.loading-card {
    background: white;
    border-radius: 20px;
    padding: 4rem 2rem;
    text-align: center;
    box-shadow: 0 2px 24px rgba(0,80,160,0.07);
    border: 1px solid #e2eaf4;
}
.loading-icon {
    font-size: 3rem;
    animation: spin 2s linear infinite;
    display: inline-block;
}
@keyframes spin {
    from { transform: rotate(0deg); }
    to { transform: rotate(360deg); }
}
.loading-title {
    font-family: 'DM Serif Display', serif;
    font-size: 1.5rem;
    color: #1a2b4a;
    margin: 1rem 0 0.5rem;
}
.loading-subtitle { color: #64748b; font-size: 0.9rem; }

/* ── Question Cards ── */
.question-card {
    background: #f8fafc;
    border-radius: 12px;
    padding: 1rem 1.25rem;
    margin-bottom: 0.75rem;
    border-left: 3px solid #1a56a0;
    font-size: 0.9rem;
    color: #374151;
    font-weight: 500;
}

/* ── Tab Styling ── */
.stTabs [data-baseweb="tab-list"] {
    background: white !important;
    border-radius: 12px !important;
    padding: 6px !important;
    gap: 4px !important;
    box-shadow: 0 1px 12px rgba(0,80,160,0.06) !important;
    border: 1px solid #e2eaf4 !important;
    margin-bottom: 1.5rem !important;
}
.stTabs [data-baseweb="tab"] {
    border-radius: 8px !important;
    font-family: 'DM Sans', sans-serif !important;
    font-weight: 600 !important;
}
.stTabs [aria-selected="true"] {
    background: #1a56a0 !important;
    color: white !important;
}
</style>
""", unsafe_allow_html=True)


# ─── Session State Init ────────────────────────────────────────────────────────
def init_state():
    defaults = {
        "step": 1,
        "age": 30,
        "sex": "Male",
        "chief_complaint": "",
        "questions": [],
        "answers": {},
        "medical_history": "",
        "medications": "",
        "allergies": "",
        "result": None,
        "processing": False,
        "error": None,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

init_state()


# ─── Helper Components ─────────────────────────────────────────────────────────

def nav_bar():
    st.markdown("""
    <div class="nav-bar">
        <div class="nav-logo">Med<span>Triage</span> AI</div>
        <div class="nav-badge">⚠️ CLINICAL PROTOTYPE </div>
    </div>
    """, unsafe_allow_html=True)


STEP_LABELS = ["Demographics", "Symptoms", "History", "Analysis", "Results"]

def progress_bar(current_step: int):
    steps_html = ""
    for i, label in enumerate(STEP_LABELS, 1):
        if i < current_step:
            circle_class = "done"
            icon = "✓"
        elif i == current_step:
            circle_class = "active"
            icon = str(i)
        else:
            circle_class = "pending"
            icon = str(i)

        steps_html += f"""
        <div class="step-item">
            <div class="step-circle {circle_class}">{icon}</div>
            <div class="step-label">{label}</div>
        </div>
        """
        if i < len(STEP_LABELS):
            line_class = "done" if i < current_step else "pending"
            steps_html += f'<div class="step-line {line_class}"></div>'

    st.markdown(f"""
    <div class="progress-container">
        <div class="progress-label">Step {current_step} of {len(STEP_LABELS)}</div>
        <div class="progress-steps">{steps_html}</div>
    </div>
    """, unsafe_allow_html=True)


def urgency_badge(level: str) -> str:
    icons = {
        "EMERGENCY": "🚨",
        "URGENT": "🔴",
        "SEMI_URGENT": "🟡",
        "NON_URGENT": "🟢",
    }
    labels = {
        "EMERGENCY": "EMERGENCY",
        "URGENT": "URGENT",
        "SEMI_URGENT": "SEMI-URGENT",
        "NON_URGENT": "NON-URGENT",
    }
    icon = icons.get(level, "⚪")
    label = labels.get(level, level)
    return f'<span class="urgency-badge urgency-{level}">{icon} {label}</span>'


def confidence_bar(score: float):
    pct = int(score * 100)
    color = "#10b981" if pct >= 80 else "#f59e0b" if pct >= 60 else "#ef4444"
    st.markdown(f"""
    <div class="conf-bar-container">
        <div class="conf-bar-label">
            <span>Confidence Score</span>
            <span style="font-weight:700;color:{color}">{pct}%</span>
        </div>
        <div class="conf-bar-track">
            <div class="conf-bar-fill" style="width:{pct}%;background:{color}"></div>
        </div>
    </div>
    """, unsafe_allow_html=True)


# ─── API Calls ─────────────────────────────────────────────────────────────────

def fetch_questions(complaint: str) -> list[str]:
    try:
        r = requests.post(
            f"{API_BASE}/api/questions",
            json={"chief_complaint": complaint},
            timeout=10,
        )
        return r.json().get("questions", [])
    except Exception:
        return [
            "How long have you had this symptom?",
            "Rate your discomfort from 1-10.",
            "Did it start suddenly or gradually?",
            "Has anything made it better or worse?",
        ]


def submit_triage() -> dict:
    payload = {
        "age": st.session_state.age,
        "sex": st.session_state.sex,
        "chief_complaint": st.session_state.chief_complaint,
        "symptom_answers": st.session_state.answers,
        "medical_history": st.session_state.medical_history,
        "current_medications": st.session_state.medications,
        "allergies": st.session_state.allergies,
    }
    try:
        r = requests.post(f"{API_BASE}/api/triage", json=payload, timeout=180)
        r.raise_for_status()
        return r.json()
    except requests.exceptions.ConnectionError:
        # Fallback to demo data if API is not running
        r = requests.get(f"{API_BASE}/api/demo", timeout=5)
        return r.json()


# ─── Step Renderers ────────────────────────────────────────────────────────────

def render_step1():
    """Patient Demographics"""
    st.markdown("""
    <div class="card">
        <div class="card-title">👤 Patient Demographics</div>
        <div class="card-subtitle">Please enter basic patient information to begin.</div>
    </div>
    """, unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        st.session_state.age = st.number_input(
            "Age", min_value=0, max_value=130,
            value=st.session_state.age, step=1,
        )
    with col2:
        st.session_state.sex = st.selectbox(
            "Biological Sex",
            ["Male", "Female", "Other"],
            index=["Male", "Female", "Other"].index(st.session_state.sex),
        )

    st.session_state.chief_complaint = st.text_area(
        "Chief Complaint",
        value=st.session_state.chief_complaint,
        placeholder="Describe the primary reason for this visit in detail...",
        height=100,
    )

    col_btn1, col_btn2 = st.columns([4, 1])
    with col_btn2:
        if st.button("Next →", key="step1_next", use_container_width=True):
            if not st.session_state.chief_complaint.strip():
                st.error("Please enter the chief complaint.")
            else:
                with st.spinner("Loading personalized questions..."):
                    st.session_state.questions = fetch_questions(
                        st.session_state.chief_complaint
                    )
                st.session_state.step = 2
                st.rerun()


def render_step2():
    """Dynamic Symptom Questionnaire"""
    st.markdown("""
    <div class="card">
        <div class="card-title">🩺 Symptom Assessment</div>
        <div class="card-subtitle">Answer the questions below based on your current condition.</div>
    </div>
    """, unsafe_allow_html=True)

    questions = st.session_state.questions
    if not questions:
        questions = [
            "How long have you had this symptom?",
            "Rate your discomfort from 1-10.",
            "Did it start suddenly or gradually?",
        ]

    for i, q in enumerate(questions):
        st.markdown(f'<div class="question-card">Q{i+1}. {q}</div>', unsafe_allow_html=True)
        answer = st.text_input(
            label=f"Answer {i+1}",
            label_visibility="collapsed",
            key=f"q_{i}",
            value=st.session_state.answers.get(q, ""),
            placeholder="Type your answer here...",
        )
        st.session_state.answers[q] = answer

    # Pain scale slider
    st.markdown('<div class="section-label">Pain / Discomfort Scale</div>', unsafe_allow_html=True)
    pain_score = st.slider("Rate overall discomfort", 0, 10, 5, key="pain_slider")
    st.session_state.answers["Overall discomfort score (1-10)"] = str(pain_score)

    col1, col2 = st.columns(2)
    with col1:
        if st.button("← Back", key="step2_back"):
            st.session_state.step = 1
            st.rerun()
    with col2:
        if st.button("Next →", key="step2_next", use_container_width=True):
            st.session_state.step = 3
            st.rerun()


def render_step3():
    """Medical History"""
    st.markdown("""
    <div class="card">
        <div class="card-title">📋 Medical History</div>
        <div class="card-subtitle">This information helps provide a more accurate assessment.</div>
    </div>
    """, unsafe_allow_html=True)

    st.session_state.medical_history = st.text_area(
        "Past Medical History",
        value=st.session_state.medical_history,
        placeholder="e.g. Hypertension, Type 2 Diabetes, previous surgeries...",
        height=100,
    )

    st.session_state.medications = st.text_area(
        "Current Medications",
        value=st.session_state.medications,
        placeholder="e.g. Metformin 500mg daily, Lisinopril 10mg daily...",
        height=80,
    )

    st.session_state.allergies = st.text_input(
        "Known Allergies",
        value=st.session_state.allergies,
        placeholder="e.g. Penicillin, Aspirin, Latex — or 'None known'",
    )

    col1, col2 = st.columns(2)
    with col1:
        if st.button("← Back", key="step3_back"):
            st.session_state.step = 2
            st.rerun()
    with col2:
        if st.button("Run AI Triage →", key="step3_next", use_container_width=True):
            st.session_state.step = 4
            st.session_state.processing = True
            st.rerun()


def render_step4():
    """Processing Animation"""
    stages = [
        ("🔍", "Intake Agent", "Parsing and structuring patient data..."),
        ("🧠", "Critic Agent", "Reviewing for missed red-flag symptoms..."),
        ("⚖️", "Triage Agent", "Classifying urgency and routing department..."),
        ("📝", "Synthesis Agent", "Generating clinical briefing..."),
    ]

    placeholder = st.empty()

    for icon, agent, desc in stages:
        with placeholder.container():
            st.markdown(f"""
            <div class="loading-card">
                <div class="loading-icon">{icon}</div>
                <div class="loading-title">{agent}</div>
                <div class="loading-subtitle">{desc}</div>
                <div style="margin-top:1.5rem;color:#94a3b8;font-size:0.8rem;">
                    Multi-agent AI system processing...
                </div>
            </div>
            """, unsafe_allow_html=True)
        time.sleep(1.2)

    with placeholder.container():
        st.markdown("""
        <div class="loading-card">
            <div class="loading-icon">✅</div>
            <div class="loading-title">Analysis Complete</div>
            <div class="loading-subtitle">Preparing your report...</div>
        </div>
        """, unsafe_allow_html=True)

    try:
        result = submit_triage()
        st.session_state.result = result
        st.session_state.error = None
    except Exception as e:
        st.session_state.error = str(e)

    st.session_state.step = 5
    st.session_state.processing = False
    st.rerun()


def render_step5():
    """Results View"""
    result = st.session_state.result
    if not result:
        st.error("No result available. Please try again.")
        if st.button("Start Over"):
            for k in list(st.session_state.keys()):
                del st.session_state[k]
            st.rerun()
        return

    triage = result.get("triage_decision", {})
    urgency = triage.get("urgency_level", "NON_URGENT")

    # Emergency Banner
    if urgency == "EMERGENCY":
        st.markdown("""
        <div class="emergency-banner">
            <div class="emergency-title">🚨 EMERGENCY — Immediate Action Required</div>
            <div class="emergency-text">
                Critical red-flag symptoms detected. Call emergency services (112/911) immediately
                or proceed to the nearest Emergency Department without delay.
            </div>
        </div>
        """, unsafe_allow_html=True)

    # Tabs
    tab1, tab2 = st.tabs(["📊 Patient Summary", "🏥 Doctor Dashboard"])

    # ── Patient Summary Tab ──────────────────────────────────────────────────
    with tab1:
        # Header card
        st.markdown(f"""
        <div class="card">
            <div style="display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:1rem;">
                <div>
                    <div class="card-title">Triage Assessment Complete</div>
                    <div class="card-subtitle">
                        Session · {result.get('session_id', 'N/A')[:16]}...
                        &nbsp;·&nbsp; {datetime.now().strftime('%d %b %Y, %H:%M')}
                    </div>
                </div>
                <div>{urgency_badge(urgency)}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        col1, col2 = st.columns([3, 2])

        with col1:
            # Patient snapshot
            st.markdown(f"""
            <div class="result-section">
                <div class="result-section-title">🧍 Patient Snapshot</div>
                <p style="font-size:0.9rem;color:#374151;line-height:1.6;margin:0">
                    {result.get('patient_snapshot', '—')}
                </p>
            </div>
            """, unsafe_allow_html=True)

            # Symptom analysis
            st.markdown(f"""
            <div class="result-section">
                <div class="result-section-title">🔬 Symptom Analysis</div>
                <p style="font-size:0.88rem;color:#374151;line-height:1.65;margin:0">
                    {result.get('symptom_analysis', '—')}
                </p>
            </div>
            """, unsafe_allow_html=True)

        with col2:
            # Triage decision
            dept = triage.get("department", "General Practice")
            rationale = triage.get("rationale", "—")
            conf = triage.get("confidence_score", 0.0)
            wait = triage.get("estimated_wait", "—")

            st.markdown(f"""
            <div class="result-section">
                <div class="result-section-title">📍 Department Routing</div>
                <div style="font-weight:700;font-size:1rem;color:#1a2b4a;margin-bottom:0.5rem">
                    {dept}
                </div>
                <div style="font-size:0.82rem;color:#64748b;margin-bottom:1rem">
                    ⏱ {wait}
                </div>
            """, unsafe_allow_html=True)
            confidence_bar(conf)
            st.markdown("</div>", unsafe_allow_html=True)

            # Red flag alerts
            red_flags = result.get("red_flag_alerts", [])
            if red_flags:
                flags_html = "".join(
                    f'<div style="background:#fee2e2;color:#dc2626;border:1px solid #fca5a5;'
                    f'border-radius:6px;padding:4px 10px;font-size:0.8rem;'
                    f'font-weight:600;margin-bottom:4px">⚠ {f}</div>'
                    for f in red_flags
                )
                st.markdown(f"""
                <div class="result-section">
                    <div class="result-section-title">🚩 Red Flags Detected</div>
                    {flags_html}
                </div>
                """, unsafe_allow_html=True)

            # Recommended actions
            actions = triage.get("recommended_actions", [])
            if actions:
                actions_html = "".join(
                    f'<div class="workup-item"><div class="workup-dot"></div>{a}</div>'
                    for a in actions
                )
                st.markdown(f"""
                <div class="result-section">
                    <div class="result-section-title">✅ Immediate Actions</div>
                    {actions_html}
                </div>
                """, unsafe_allow_html=True)

        # Differentials
        diffs = result.get("differential_considerations", [])
        if diffs:
            pills = "".join(f'<span class="diff-pill">{d}</span>' for d in diffs)
            st.markdown(f"""
            <div class="result-section">
                <div class="result-section-title">🔭 Differential Considerations</div>
                <div style="margin-top:0.25rem">{pills}</div>
                <div style="font-size:0.75rem;color:#94a3b8;margin-top:0.75rem">
                    These are possibilities to investigate — not diagnoses.
                </div>
            </div>
            """, unsafe_allow_html=True)

        # Disclaimer
        st.markdown(f"""
        <div class="disclaimer-box">
            {result.get('disclaimer', '⚠️ Clinical decision support prototype only.')}
        </div>
        """, unsafe_allow_html=True)

    # ── Doctor Dashboard Tab ─────────────────────────────────────────────────
    with tab2:
        st.markdown(f"""
        <div class="dashboard-header">
            <div class="dashboard-title">🏥 Clinical Briefing</div>
            <div class="dashboard-meta">
                Session ID: {result.get('session_id', 'N/A')} &nbsp;·&nbsp;
                Generated: {result.get('generated_at', '—')[:16].replace('T',' ')} UTC &nbsp;·&nbsp;
                AI System: MedTriage v1.0
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Metrics row
        conf_val = triage.get("confidence_score", 0)
        flags_count = len(result.get("red_flag_alerts", []))
        workup_count = len(result.get("recommended_workup", []))

        st.markdown(f"""
        <div class="metric-grid">
            <div class="metric-card">
                <div class="metric-label">Urgency Level</div>
                <div>{urgency_badge(urgency)}</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">AI Confidence</div>
                <div class="metric-value">{int(conf_val*100)}%</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Red Flags</div>
                <div class="metric-value" style="color:{'#dc2626' if flags_count>0 else '#10b981'}">
                    {flags_count} {'Detected' if flags_count>0 else 'Clear'}
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        col1, col2 = st.columns(2)

        with col1:
            # Full symptom analysis
            st.markdown(f"""
            <div class="result-section">
                <div class="result-section-title">📋 Clinical Assessment</div>
                <p style="font-size:0.88rem;color:#1e293b;line-height:1.7;margin:0">
                    {result.get('symptom_analysis', '—')}
                </p>
            </div>
            """, unsafe_allow_html=True)

            # Rationale
            st.markdown(f"""
            <div class="result-section">
                <div class="result-section-title">⚖️ Triage Rationale</div>
                <p style="font-size:0.88rem;color:#1e293b;line-height:1.65;margin:0">
                    {triage.get('rationale', '—')}
                </p>
            </div>
            """, unsafe_allow_html=True)

            # Clinician notes
            notes = result.get("clinician_notes", "")
            if notes:
                st.markdown(f"""
                <div class="result-section" style="border-left:3px solid #f59e0b">
                    <div class="result-section-title">📌 Clinician Notes</div>
                    <p style="font-size:0.88rem;color:#1e293b;line-height:1.65;margin:0">
                        {notes}
                    </p>
                </div>
                """, unsafe_allow_html=True)

        with col2:
            # Recommended workup
            workup = result.get("recommended_workup", [])
            if workup:
                items_html = "".join(
                    f'<div class="workup-item"><div class="workup-dot"></div>{w}</div>'
                    for w in workup
                )
                st.markdown(f"""
                <div class="result-section">
                    <div class="result-section-title">🧪 Recommended Workup ({workup_count} items)</div>
                    {items_html}
                </div>
                """, unsafe_allow_html=True)

            # Differentials
            diffs = result.get("differential_considerations", [])
            if diffs:
                diffs_html = "".join(
                    f'<div style="padding:0.5rem;border-bottom:1px solid #f1f5f9;font-size:0.87rem;'
                    f'color:#1e293b">{i+1}. {d}</div>'
                    for i, d in enumerate(diffs)
                )
                st.markdown(f"""
                <div class="result-section">
                    <div class="result-section-title">🔭 Differentials</div>
                    {diffs_html}
                    <div style="font-size:0.73rem;color:#94a3b8;margin-top:0.75rem">
                        For clinical consideration only — not diagnostic conclusions.
                    </div>
                </div>
                """, unsafe_allow_html=True)

        # Export JSON
        st.markdown('<div class="section-label" style="margin-top:1rem">Export</div>', unsafe_allow_html=True)
        st.download_button(
            label="⬇ Download Full Report (JSON)",
            data=json.dumps(result, indent=2),
            file_name=f"triage_report_{result.get('session_id', 'report')}.json",
            mime="application/json",
        )

        st.markdown(f"""
        <div class="disclaimer-box">
            {result.get('disclaimer', '⚠️ Clinical decision support prototype only.')}
        </div>
        """, unsafe_allow_html=True)

    # Start over
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("🔄 New Triage Session", key="restart"):
        for k in list(st.session_state.keys()):
            del st.session_state[k]
        st.rerun()


# ─── Main App ─────────────────────────────────────────────────────────────────

def main():
    nav_bar()
    progress_bar(st.session_state.step)

    step = st.session_state.step

    if step == 1:
        render_step1()
    elif step == 2:
        render_step2()
    elif step == 3:
        render_step3()
    elif step == 4:
        render_step4()
    elif step == 5:
        if st.session_state.error:
            st.error(f"Error: {st.session_state.error}")
            if st.button("Try Again"):
                st.session_state.step = 3
                st.rerun()
        else:
            render_step5()


if __name__ == "__main__":
    main()
