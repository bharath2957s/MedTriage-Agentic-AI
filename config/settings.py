"""
Central configuration for the Medical Triage system.
Uses environment variables with sensible defaults.
"""

"""
Central configuration for the Medical Triage system.
Uses environment variables with sensible defaults.
"""

import os
from dataclasses import dataclass
from dotenv import load_dotenv

# 🔥 ADD THIS LINE
load_dotenv()


@dataclass
class OllamaConfig:
    base_url: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    model: str = os.getenv("OLLAMA_MODEL", "llama3.2")
    temperature: float = float(os.getenv("OLLAMA_TEMP", "0.3"))
    timeout: int = int(os.getenv("OLLAMA_TIMEOUT", "120"))


@dataclass
class AppConfig:
    api_host: str = os.getenv("API_HOST", "0.0.0.0")
    api_port: int = int(os.getenv("API_PORT", "8000"))
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    max_critic_iterations: int = int(os.getenv("MAX_CRITIC_ITERATIONS", "2"))
    debug: bool = os.getenv("DEBUG", "false").lower() == "true"


ollama_config = OllamaConfig()
app_config = AppConfig()

# ─── Red-flag symptom keywords (rule-based fast path) ───────────────────────
# These trigger immediate EMERGENCY escalation without LLM inference.
RED_FLAG_KEYWORDS = [
    "chest pain", "crushing chest", "chest pressure",
    "can't breathe", "cannot breathe", "shortness of breath",
    "difficulty breathing", "stopped breathing",
    "stroke", "face drooping", "arm weakness", "speech difficulty",
    "sudden severe headache", "worst headache of my life", "thunderclap headache",
    "unconscious", "unresponsive", "passed out", "fainting",
    "suicidal", "suicide", "self-harm", "overdose",
    "severe bleeding", "uncontrolled bleeding", "blood loss",
    "anaphylaxis", "allergic reaction", "throat closing", "swollen throat",
    "seizure", "convulsions",
    "crushing pain", "tearing pain",
    "coughing blood", "vomiting blood", "blood in stool",
    "paralysis", "loss of sensation",
    "sudden vision loss", "sudden blindness",
]

# ─── Symptom tree for dynamic intake questioning ─────────────────────────────
# Maps chief complaint categories to follow-up question sets.
SYMPTOM_TREE = {
    "chest": [
        "Is the pain sharp, dull, or pressure-like?",
        "Does the pain radiate to your arm, jaw, or back?",
        "Rate the pain 1–10. How long have you had it?",
        "Are you short of breath or sweating?",
        "Do you have a history of heart disease?",
    ],
    "head": [
        "Is this the worst headache of your life?",
        "Did it come on suddenly or gradually?",
        "Do you have vision changes, nausea, or neck stiffness?",
        "Have you had a recent head injury?",
        "Do you have a fever alongside the headache?",
    ],
    "abdomen": [
        "Where exactly is the pain — upper, lower, left, right?",
        "Is the pain constant or does it come and go?",
        "Do you have nausea, vomiting, or diarrhea?",
        "Any blood in stool or urine?",
        "When did you last eat, and did it worsen after eating?",
    ],
    "breathing": [
        "When did the breathing difficulty start?",
        "Is it worse lying flat or with activity?",
        "Do you hear any wheezing or stridor?",
        "Do you have a cough? Any blood?",
        "Do you have asthma, COPD, or prior lung issues?",
    ],
    "general": [
        "How long have you had this symptom?",
        "Did it start suddenly or gradually?",
        "Rate your discomfort from 1–10.",
        "Has anything made it better or worse?",
        "Any other symptoms you've noticed?",
    ],
}
