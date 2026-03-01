"""
Triage Agent
============
Hybrid clinical triage engine:

1) Deterministic emergency rule engine (pattern-based)
2) LLM refinement for non-emergency cases
3) Safe fallback if LLM fails

Production-safe and clinically realistic.
"""

import re
from dataclasses import dataclass
from typing import List

from backend.models.schemas import (
    IntakeState,
    TriageDecision,
    UrgencyLevel,
    Department,
)
from backend.utils.ollama_client import llm_client
from backend.utils.logger import get_logger

logger = get_logger("agent.triage")


# ─────────────────────────────────────────────────────────────
# TEXT NORMALIZATION
# ─────────────────────────────────────────────────────────────

def normalize_text(text: str) -> str:
    text = text.lower()
    text = text.replace("’", "'")
    text = re.sub(r"[^\w\s']", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


# ─────────────────────────────────────────────────────────────
# CLINICAL RULE STRUCTURE
# ─────────────────────────────────────────────────────────────

@dataclass
class ClinicalRule:
    name: str
    patterns: List[str]
    urgency: UrgencyLevel
    department: Department
    rationale: str
    confidence: float = 0.98


# ─────────────────────────────────────────────────────────────
# CLINICALLY REALISTIC EMERGENCY RULES
# ─────────────────────────────────────────────────────────────

CLINICAL_RULES = [

    # CARDIAC
    ClinicalRule(
        name="acute_coronary_syndrome",
        patterns=[
            "chest pain",
            "pressure in chest",
            "crushing chest pain",
            "pain radiating to left arm",
            "jaw pain with chest pain",
            "sweating with chest pain"
        ],
        urgency=UrgencyLevel.EMERGENCY,
        department=Department.EMERGENCY,
        rationale="Symptoms concerning for acute coronary syndrome."
    ),

    # STROKE
    ClinicalRule(
        name="stroke_symptoms",
        patterns=[
            "sudden weakness",
            "one side weak",
            "facial droop",
            "slurred speech",
            "cannot speak",
            "sudden vision loss",
            "confusion with sudden onset"
        ],
        urgency=UrgencyLevel.EMERGENCY,
        department=Department.EMERGENCY,
        rationale="Focal neurological deficit suspicious for stroke."
    ),

    # THUNDERCLAP HEADACHE
    ClinicalRule(
        name="thunderclap_headache",
        patterns=[
            "worst headache of my life",
            "sudden severe headache",
            "thunderclap headache"
        ],
        urgency=UrgencyLevel.EMERGENCY,
        department=Department.EMERGENCY,
        rationale="Sudden severe headache concerning for intracranial hemorrhage."
    ),

    # SEIZURE
    ClinicalRule(
        name="seizure_event",
        patterns=[
            "seizure",
            "convulsion",
            "shaking episode"
        ],
        urgency=UrgencyLevel.EMERGENCY,
        department=Department.EMERGENCY,
        rationale="Active or recent seizure event."
    ),

    # RESPIRATORY DISTRESS
    ClinicalRule(
        name="respiratory_distress",
        patterns=[
            "cannot breathe",
            "can't breathe",
            "gasping for air",
            "blue lips",
            "struggling to breathe"
        ],
        urgency=UrgencyLevel.EMERGENCY,
        department=Department.EMERGENCY,
        rationale="Signs of acute respiratory distress."
    ),

    # UNCONTROLLED BLEEDING
    ClinicalRule(
        name="uncontrolled_bleeding",
        patterns=[
            "heavy bleeding",
            "severe bleeding",
            "bleeding won't stop",
            "bleeding that won't stop",
            "continuous bleeding",
            "profuse bleeding",
            "losing blood rapidly"
        ],
        urgency=UrgencyLevel.EMERGENCY,
        department=Department.EMERGENCY,
        rationale="Uncontrolled bleeding requiring immediate intervention."
    ),

    # ANAPHYLAXIS
    ClinicalRule(
        name="anaphylaxis",
        patterns=[
            "throat swelling",
            "allergic reaction with breathing difficulty",
            "anaphylaxis",
            "lip swelling with breathing trouble"
        ],
        urgency=UrgencyLevel.EMERGENCY,
        department=Department.EMERGENCY,
        rationale="Possible anaphylactic reaction."
    ),

    # SUICIDAL / OVERDOSE
    ClinicalRule(
        name="suicidal_risk",
        patterns=[
            "suicidal",
            "want to kill myself",
            "overdose attempt",
            "took too many pills"
        ],
        urgency=UrgencyLevel.EMERGENCY,
        department=Department.PSYCHIATRY,
        rationale="Active suicidal ideation or overdose risk."
    ),
]


# ─────────────────────────────────────────────────────────────
# RULE ENGINE
# ─────────────────────────────────────────────────────────────

def apply_clinical_rules(state: IntakeState) -> TriageDecision | None:

    complaint = state.demographics.chief_complaint if state.demographics else ""
    symptoms_text = " ".join(s.name for s in state.symptoms)

    full_text = normalize_text(complaint + " " + symptoms_text)

    for rule in CLINICAL_RULES:
        for pattern in rule.patterns:
            if normalize_text(pattern) in full_text:

                logger.warning(f"Clinical emergency rule triggered: {rule.name}")

                return TriageDecision(
                    urgency_level=rule.urgency,
                    department=rule.department,
                    rationale=rule.rationale,
                    confidence_score=rule.confidence,
                    rule_triggered=rule.name,
                    recommended_actions=[
                        "Immediate emergency evaluation required",
                        "Do not delay transport",
                        "Continuous monitoring advised"
                    ],
                    estimated_wait="Immediate — do not wait",
                )

    return None


# ─────────────────────────────────────────────────────────────
# MAIN TRIAGE FUNCTION
# ─────────────────────────────────────────────────────────────

TRIAGE_SYSTEM_PROMPT = """
You are a senior emergency triage nurse.
Assess urgency and department based on symptoms.
Be conservative and patient-safe.
Return only valid JSON.
"""


def run_triage_agent(state: IntakeState) -> TriageDecision:

    logger.info(f"Triage Agent running for session={state.session_id}")

    # 1️⃣ Deterministic emergency rules first
    clinical_decision = apply_clinical_rules(state)
    if clinical_decision:
        return clinical_decision

    # 2️⃣ LLM-based triage for non-emergency nuanced cases
    symptoms_text = "\n".join(
        f"- {s.name} | severity: {s.severity} | duration: {s.duration} | onset: {s.onset}"
        for s in state.symptoms
    )

    prompt = f"""
Patient:
Age: {state.demographics.age if state.demographics else 'Unknown'}
Sex: {state.demographics.sex if state.demographics else 'Unknown'}
Chief Complaint: {state.demographics.chief_complaint}
Medical History: {state.medical_history or 'None'}

Symptoms:
{symptoms_text or 'Chief complaint only'}

Available urgency levels:
{[u.value for u in UrgencyLevel]}

Available departments:
{[d.value for d in Department]}

Return JSON:
{{
  "urgency_level": "...",
  "department": "...",
  "rationale": "...",
  "confidence_score": 0.0-1.0,
  "recommended_actions": ["..."],
  "estimated_wait": "..."
}}
"""

    try:
        result = llm_client.generate_json(prompt, system=TRIAGE_SYSTEM_PROMPT)

        urgency = UrgencyLevel(result.get("urgency_level", "NON_URGENT"))

        department_str = result.get("department", "General Practice")
        dept = Department.GENERAL
        for d in Department:
            if d.value == department_str or d.name == department_str:
                dept = d
                break

        return TriageDecision(
            urgency_level=urgency,
            department=dept,
            rationale=result.get("rationale", "LLM-based triage assessment."),
            confidence_score=float(result.get("confidence_score", 0.75)),
            recommended_actions=result.get("recommended_actions", []),
            estimated_wait=result.get("estimated_wait"),
        )

    except Exception as e:
        logger.error(f"Triage LLM error: {e} — fallback triggered")

        return TriageDecision(
            urgency_level=UrgencyLevel.SEMI_URGENT,
            department=Department.GENERAL,
            rationale="Fallback triage due to LLM formatting error.",
            confidence_score=0.5,
            recommended_actions=[
                "Seek medical evaluation within 24 hours"
            ],
        ) 