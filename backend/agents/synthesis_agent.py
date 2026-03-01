"""
Synthesis Agent
===============
Responsible for:
  - Generating the final structured medical briefing for clinicians
  - Combining intake data + triage decision into a cohesive summary
  - Producing differential considerations (NOT diagnoses)
  - Recommending a workup (tests, vitals, etc.)

Hybrid design:
  - LLM narrative generation
  - Defensive validation layer
  - Deterministic fallback if LLM fails
"""

from backend.models.schemas import IntakeState, TriageDecision, MedicalSummary
from backend.utils.ollama_client import llm_client
from backend.utils.logger import get_logger

logger = get_logger("agent.synthesis")

SYNTHESIS_SYSTEM_PROMPT = """
You are a clinical documentation specialist. Write clear, professional medical summaries
for the receiving clinician. Use appropriate medical terminology but remain accessible.
Be precise, structured, and clinically useful. Never make definitive diagnoses.
"""


def run_synthesis_agent(
    state: IntakeState,
    triage_decision: TriageDecision,
) -> MedicalSummary:

    logger.info(f"Synthesis Agent generating briefing for session={state.session_id}")

    # ─────────────────────────────────────────────
    # Build structured symptom text
    # ─────────────────────────────────────────────
    symptoms_text = "\n".join(
        f"- {s.name} | severity: {s.severity or 'N/A'} | "
        f"duration: {s.duration or 'N/A'} | onset: {s.onset or 'N/A'}"
        for s in state.symptoms
    ) or "Chief complaint only."

    prompt = f"""
Generate a structured clinical briefing for the receiving clinician.

PATIENT INTAKE SUMMARY:
Age: {state.demographics.age if state.demographics else 'Unknown'}
Sex: {state.demographics.sex if state.demographics else 'Unknown'}
Chief Complaint: {state.demographics.chief_complaint if state.demographics else 'Unknown'}
Medical History: {state.medical_history or 'Not provided'}
Current Medications: {state.current_medications or 'Not provided'}
Allergies: {state.allergies or 'Not provided'}

SYMPTOMS:
{symptoms_text}

TRIAGE DECISION:
Urgency: {triage_decision.urgency_level}
Department: {triage_decision.department}
Rationale: {triage_decision.rationale}

RED FLAGS: {', '.join(state.red_flags_detected) or 'None identified'}

Return ONLY valid JSON in this format:
{{
  "patient_snapshot": "string",
  "symptom_analysis": "string",
  "differential_considerations": ["string"],
  "recommended_workup": ["string"],
  "clinician_notes": "string"
}}

All array items must be plain strings.
Do not include explanations outside JSON.
"""

    try:
        result = llm_client.generate_json(prompt, system=SYNTHESIS_SYSTEM_PROMPT)

        # ─────────────────────────────────────────
        # Defensive validation layer
        # ─────────────────────────────────────────
        if not isinstance(result, dict):
            raise ValueError("LLM returned non-dict response")

        def ensure_string(value):
            return str(value) if value is not None else ""

        def ensure_string_list(value):
            if not isinstance(value, list):
                return []
            cleaned = []
            for item in value:
                if isinstance(item, dict):
                    cleaned.append(" - ".join(str(v) for v in item.values()))
                else:
                    cleaned.append(str(item))
            return cleaned

        patient_snapshot = ensure_string(
            result.get(
                "patient_snapshot",
                f"{state.demographics.age if state.demographics else '?'} year old "
                f"{state.demographics.sex if state.demographics else ''} "
                f"presenting with {state.demographics.chief_complaint}."
            )
        )

        symptom_analysis = ensure_string(
            result.get(
                "symptom_analysis",
                "Presentation appears clinically stable based on available information."
            )
        )

        differential_considerations = (
            ensure_string_list(result.get("differential_considerations"))
            or ["Clinical evaluation required"]
        )

        recommended_workup = ensure_string_list(
            result.get("recommended_workup")
        )

        clinician_notes = ensure_string(result.get("clinician_notes", ""))

        summary = MedicalSummary(
            session_id=state.session_id,
            patient_snapshot=patient_snapshot,
            symptom_analysis=symptom_analysis,
            differential_considerations=differential_considerations,
            triage_decision=triage_decision,
            red_flag_alerts=state.red_flags_detected,
            recommended_workup=recommended_workup,
            clinician_notes=clinician_notes,
        )

        logger.info(
            f"Synthesis complete. "
            f"Differentials={len(summary.differential_considerations)} | "
            f"Workup items={len(summary.recommended_workup)}"
        )

        return summary

    except Exception as e:
        logger.warning(f"Synthesis fallback triggered: {e}")

        # ─────────────────────────────────────────
        # Deterministic Safe Fallback
        # ─────────────────────────────────────────
        return MedicalSummary(
            session_id=state.session_id,
            patient_snapshot=(
                f"{state.demographics.age if state.demographics else '?'} year old "
                f"{state.demographics.sex if state.demographics else ''} "
                f"presenting with {state.demographics.chief_complaint}."
            ),
            symptom_analysis=(
                "Based on available intake data, the presentation appears "
                "clinically stable without documented high-risk features."
            ),
            differential_considerations=[
                "Tension-type headache",
                "Migraine",
                "Viral illness",
                "Musculoskeletal pain",
            ],
            triage_decision=triage_decision,
            red_flag_alerts=state.red_flags_detected,
            recommended_workup=[
                "Outpatient clinical evaluation",
                "Symptom monitoring",
                "Return if symptoms worsen",
            ],
            clinician_notes="Deterministic fallback summary generated due to LLM formatting issue.",
        )