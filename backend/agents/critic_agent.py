"""
Critic Agent
============
Responsible for:
  - Reviewing the completed IntakeState for clinical completeness
  - Detecting any missed red-flag symptoms not caught by keyword scan
  - Suggesting additional questions if critical information is absent
  - Approving or rejecting the intake for downstream triage

The Critic Agent drives the reflection loop in LangGraph:
  If not approved → Intake Agent reruns with additional questions.
  If approved (or max iterations reached) → flow continues to Triage.
"""

from backend.models.schemas import IntakeState, CriticFeedback
from backend.utils.ollama_client import llm_client
from backend.utils.logger import get_logger
from config.settings import app_config

logger = get_logger("agent.critic")

CRITIC_SYSTEM_PROMPT = """
You are a senior emergency medicine physician reviewing a patient intake form.
Your job is to identify:
1. Any MISSED red-flag symptoms that were not asked about or reported
2. Critical missing information that would change triage urgency
3. Logical inconsistencies in the reported symptoms

Be conservative — err on the side of safety. If in doubt, flag it.
"""


def run_critic_agent(state: IntakeState) -> CriticFeedback:
    """
    Reviews the current IntakeState and returns structured critique.

    Args:
        state: The current IntakeState from the Intake Agent.

    Returns:
        CriticFeedback with approval decision and improvement suggestions.
    """
    logger.info(f"Critic Agent reviewing session={state.session_id} | "
                f"iteration={state.iterations}")

    # ── If escalation already triggered, auto-approve to fast-track ──────────
    if state.escalation_triggered:
        logger.warning("Escalation triggered — Critic bypassing for fast path.")
        return CriticFeedback(
            approved=True,
            critique_notes="Escalation path — bypassing extended critique.",
        )

    # ── Max iterations guard ──────────────────────────────────────────────────
    if state.iterations >= app_config.max_critic_iterations:
        logger.info("Max critic iterations reached — forcing approval.")
        return CriticFeedback(
            approved=True,
            critique_notes=f"Auto-approved after {state.iterations} iterations.",
        )

    # ── Build context for LLM ─────────────────────────────────────────────────
    symptoms_text = "\n".join(
        f"- {s.name} | severity: {s.severity}/10 | duration: {s.duration} | "
        f"onset: {s.onset}"
        for s in state.symptoms
    )

    prompt = f"""
Review this patient intake and identify any clinical gaps or missed red flags.

PATIENT:
Age: {state.demographics.age if state.demographics else 'Unknown'}
Sex: {state.demographics.sex if state.demographics else 'Unknown'}
Chief Complaint: {state.demographics.chief_complaint if state.demographics else 'Unknown'}

REPORTED SYMPTOMS:
{symptoms_text or 'None structured'}

MEDICAL HISTORY: {state.medical_history or 'Not provided'}
MEDICATIONS: {state.current_medications or 'Not provided'}
ALLERGIES: {state.allergies or 'Not provided'}
ALREADY FLAGGED RED FLAGS: {', '.join(state.red_flags_detected) or 'None'}

Return a JSON object with:
{{
  "approved": true/false,
  "missed_red_flags": ["list of any red flag symptoms not yet explored"],
  "suggested_questions": ["questions to clarify missing critical info"],
  "critique_notes": "brief clinical reasoning"
}}

Return ONLY valid JSON. No explanation outside JSON.
"""

    try:
        result = llm_client.generate_json(prompt, system=CRITIC_SYSTEM_PROMPT)

        # Handle fallback raw response
        if "raw_response" in result:
            logger.warning("Critic LLM returned non-JSON, defaulting to approval.")
            return CriticFeedback(
                approved=True,
                critique_notes="Could not parse LLM critique — defaulting to approved.",
            )

        feedback = CriticFeedback(
            approved=result.get("approved", True),
            missed_red_flags=result.get("missed_red_flags", []),
            suggested_questions=result.get("suggested_questions", []),
            critique_notes=result.get("critique_notes", ""),
        )

        # If new red flags found by LLM, merge them
        if feedback.missed_red_flags:
            for flag in feedback.missed_red_flags:
                if flag not in state.red_flags_detected:
                    state.red_flags_detected.append(flag)
                    logger.warning(f"Critic found additional red flag: {flag}")

        logger.info(
            f"Critic decision: approved={feedback.approved} | "
            f"missed_flags={feedback.missed_red_flags}"
        )
        return feedback

    except Exception as e:
        logger.error(f"Critic Agent LLM error: {e}")
        # Default to approved on error to avoid blocking the pipeline
        return CriticFeedback(
            approved=True,
            critique_notes=f"Critic encountered error: {str(e)} — defaulting to approved.",
        )
