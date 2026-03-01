"""
Intake Agent
============
Responsible for:
  - Parsing patient demographics and chief complaint
  - Dynamically selecting follow-up questions using the symptom tree
  - Structuring raw answers into SymptomDetail objects
  - Performing fast red-flag keyword detection before LLM call
"""

import uuid
from typing import Any
from backend.models.schemas import (
    IntakeState, PatientDemographics, SymptomDetail
)
from backend.utils.ollama_client import llm_client
from backend.utils.logger import get_logger
from config.settings import RED_FLAG_KEYWORDS, SYMPTOM_TREE

logger = get_logger("agent.intake")


def detect_red_flags(text: str) -> list[str]:
    """
    Fast rule-based red-flag detection.
    Scans free-text for any of the predefined emergency keywords.
    Returns list of matched flags (empty if none).
    """
    text_lower = text.lower()
    return [kw for kw in RED_FLAG_KEYWORDS if kw in text_lower]


def classify_complaint_category(chief_complaint: str) -> str:
    """
    Map the chief complaint to a symptom-tree category for
    dynamic follow-up question selection.
    """
    cc = chief_complaint.lower()
    if any(w in cc for w in ["chest", "heart", "palpitation"]):
        return "chest"
    if any(w in cc for w in ["head", "migraine", "headache"]):
        return "head"
    if any(w in cc for w in ["stomach", "abdomen", "belly", "nausea", "vomit"]):
        return "abdomen"
    if any(w in cc for w in ["breath", "breathing", "wheeze", "cough", "lung"]):
        return "breathing"
    return "general"


def run_intake_agent(raw_input: dict) -> IntakeState:
    """
    Entry point for the Intake Agent node in the LangGraph workflow.

    Args:
        raw_input: Dict containing patient form data from the frontend.
            Expected keys: age, sex, chief_complaint, symptom_answers,
                           medical_history, current_medications, allergies

    Returns:
        IntakeState populated with structured patient data.
    """
    logger.info("Intake Agent started")

    # ── Step 1: Build demographics ───────────────────────────────────────────
    demographics = PatientDemographics(
        age=int(raw_input.get("age", 0)),
        sex=raw_input.get("sex", "Other"),
        chief_complaint=raw_input.get("chief_complaint", ""),
    )

    # ── Step 2: Quick red-flag scan on all free text ─────────────────────────
    all_text = " ".join([
        demographics.chief_complaint,
        raw_input.get("medical_history", ""),
        " ".join(raw_input.get("symptom_answers", {}).values()),
    ])
    red_flags = detect_red_flags(all_text)
    if red_flags:
        logger.warning(f"Red flags detected by keyword scan: {red_flags}")

    # ── Step 3: Use LLM to extract structured symptoms from free-text answers ─
    symptom_answers_text = "\n".join(
        f"Q: {q}\nA: {a}"
        for q, a in raw_input.get("symptom_answers", {}).items()
    )

    symptoms: list[SymptomDetail] = []
    if symptom_answers_text.strip():
        try:
            prompt = f"""
You are a medical intake parser. Extract structured symptom details from the patient's answers.
Return a JSON array of symptom objects. Each object must have:
  - "name": symptom name (string)
  - "duration": how long (string or null)
  - "severity": 1-10 integer or null
  - "onset": "sudden" or "gradual" or null
  - "associated_factors": any relevant context (string or null)

Patient Q&A:
{symptom_answers_text}

Return ONLY valid JSON array. No explanation.
"""
            parsed = llm_client.generate_json(prompt)
            if isinstance(parsed, list):
                for item in parsed:
                    try:
                        symptoms.append(SymptomDetail(**item))
                    except Exception as e:
                        logger.warning(f"Skipping malformed symptom entry: {e}")
            else:
                # Fallback: create a single symptom from chief complaint
                symptoms.append(SymptomDetail(name=demographics.chief_complaint))
        except Exception as e:
            logger.error(f"LLM symptom parsing failed: {e}")
            symptoms.append(SymptomDetail(name=demographics.chief_complaint))
    else:
        symptoms.append(SymptomDetail(name=demographics.chief_complaint))

    # ── Step 4: Assemble IntakeState ─────────────────────────────────────────
    state = IntakeState(
        session_id=raw_input.get("session_id") or str(uuid.uuid4()),
        demographics=demographics,
        symptoms=symptoms,
        medical_history=raw_input.get("medical_history"),
        current_medications=raw_input.get("current_medications"),
        allergies=raw_input.get("allergies"),
        red_flags_detected=red_flags,
        intake_complete=True,
        escalation_triggered=len(red_flags) > 0,
    )

    logger.info(
        f"Intake complete. Session={state.session_id} | "
        f"Symptoms={len(state.symptoms)} | "
        f"Red flags={state.red_flags_detected}"
    )
    return state


def get_dynamic_questions(chief_complaint: str) -> list[str]:
    """
    Returns the appropriate follow-up question set for the given complaint.
    Used by the frontend to render dynamic question cards.
    """
    category = classify_complaint_category(chief_complaint)
    return SYMPTOM_TREE.get(category, SYMPTOM_TREE["general"])
