"""
FastAPI Backend Server
======================
Exposes REST endpoints consumed by the Streamlit frontend.
All heavy lifting is delegated to the LangGraph workflow.
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import uvicorn

from backend.graph.workflow import run_workflow
from backend.agents.intake_agent import get_dynamic_questions
from backend.utils.logger import get_logger
from config.settings import app_config

logger = get_logger("api.server")

app = FastAPI(
    title="Autonomous Medical Triage System",
    description="Clinical decision support prototype — NOT for real medical use.",
    version="1.0.0",
)

# Allow Streamlit frontend to call the API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── Request / Response Models ────────────────────────────────────────────────

class TriageRequest(BaseModel):
    session_id: Optional[str] = None
    age: int
    sex: str
    chief_complaint: str
    symptom_answers: dict = {}
    medical_history: Optional[str] = None
    current_medications: Optional[str] = None
    allergies: Optional[str] = None


class QuestionsRequest(BaseModel):
    chief_complaint: str


# ─── Endpoints ─────────────────────────────────────────────────────────────────

@app.get("/health")
def health_check():
    """Simple health check."""
    return {"status": "ok", "service": "medical-triage-api"}


@app.post("/api/questions")
def get_questions(req: QuestionsRequest):
    """
    Returns dynamic follow-up questions for a given chief complaint.
    Called by frontend after patient enters chief complaint.
    """
    logger.info(f"Questions requested for: {req.chief_complaint}")
    questions = get_dynamic_questions(req.chief_complaint)
    return {"questions": questions}


@app.post("/api/triage")
def run_triage(req: TriageRequest):
    """
    Main triage endpoint.
    Runs the full LangGraph multi-agent workflow and returns the medical summary.
    """
    logger.info(f"Triage request received — complaint: {req.chief_complaint}")

    try:
        raw_input = req.model_dump()
        result = run_workflow(raw_input)

        if result.get("error"):
            raise HTTPException(
                status_code=500,
                detail=f"Workflow error: {result['error']}"
            )

        if not result.get("final_summary"):
            raise HTTPException(
                status_code=500,
                detail="Workflow completed but no summary was generated."
            )

        summary = result["final_summary"]
        return summary.model_dump()

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Triage endpoint error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/demo")
def demo_result():
    """
    Returns a pre-built demo result for UI testing without LLM.
    Useful for frontend development when Ollama is not running.
    """
    return {
        "session_id": "demo-session-001",
        "generated_at": "2025-01-01T00:00:00",
        "patient_snapshot": "45-year-old male presenting with acute chest pain radiating to the left arm, onset 30 minutes ago.",
        "symptom_analysis": "The patient presents with classic symptoms consistent with acute coronary syndrome. The substernal chest pressure with radiation to the left arm and associated diaphoresis are hallmark features of myocardial ischemia. Immediate cardiac workup is warranted.",
        "differential_considerations": [
            "Acute Myocardial Infarction (STEMI/NSTEMI)",
            "Unstable Angina",
            "Pulmonary Embolism",
            "Aortic Dissection",
        ],
        "triage_decision": {
            "urgency_level": "EMERGENCY",
            "department": "Emergency Medicine",
            "rationale": "Classic ACS presentation with high-risk features. Immediate evaluation required.",
            "confidence_score": 0.96,
            "rule_triggered": "chest_pain_rule",
            "recommended_actions": [
                "Immediate 12-lead ECG",
                "Cardiac monitoring",
                "IV access × 2",
                "Aspirin 324mg PO",
                "Cardiology consult STAT",
            ],
            "estimated_wait": "Immediate",
        },
        "red_flag_alerts": ["chest pain", "radiating to arm"],
        "recommended_workup": [
            "12-lead ECG (immediate)",
            "Troponin I/T × 2 (0h and 3h)",
            "CBC, BMP, coagulation panel",
            "Chest X-ray (portable)",
            "Echocardiogram if available",
        ],
        "clinician_notes": "Patient appears anxious and diaphoretic. Vitals pending. Do not delay ECG for IV access.",
        "disclaimer": "⚠️ This is a clinical decision support prototype. Not a substitute for professional medical judgment.",
    }


if __name__ == "__main__":
    uvicorn.run(
        "backend.api.server:app",
        host=app_config.api_host,
        port=app_config.api_port,
        reload=app_config.debug,
        log_level=app_config.log_level.lower(),
    )
