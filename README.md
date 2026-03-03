# 🏥 MedTriage – Agentic AI Clinical Decision Support System

> **⚠️ PROTOTYPE ONLY** — This is a clinical decision support prototype for research and educational purposes. It is NOT a real medical diagnostic system and must NOT be used for actual medical decisions.

---

## Overview

An Agentic AI-powered medical triage system that orchestrates multiple specialized agents using a hybrid neuro-symbolic architecture to assess symptoms, detect emergencies, assign urgency levels, and generate structured clinical briefings — all running locally with Ollama.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Streamlit Frontend                       │
│   Multi-step card UI → Demographics → Symptoms → History → ...  │
└─────────────────────────────────┬───────────────────────────────┘
                                  │ REST API
                                  ▼
┌─────────────────────────────────────────────────────────────────┐
│                        FastAPI Backend                          │
│                  /api/questions  /api/triage                    │
└─────────────────────────────────┬───────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────┐
│                    LangGraph Workflow Engine                    │
│                                                                 │
│   ┌──────────┐     ┌──────────┐     ┌──────────┐                │
│   │  Intake  │────▶│  Critic  │────▶│  Triage │                │
│   │  Agent   │     │  Agent   │     │  Agent   │                │
│   └──────────┘◀────└──────────┘     └────┬─────┘               │
│       ▲  (reflection loop)               │                      │
│       │                                  ▼                      │
│   ┌───┴──────┐                    ┌──────────────┐              │
│   │Escalation│                    │  Synthesis   │              │
│   │ Handler  │                    │    Agent     │              │
│   └──────────┘                    └──────────────┘              │
└─────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Ollama (Local LLM)                           │
│                  llama3.2 (or any model)                        │
└─────────────────────────────────────────────────────────────────┘
```

## 🧠 Agentic AI Architecture

This system implements a true multi-agent architecture where independent agents operate with defined roles, shared state, and iterative routing.

Each agent:
- Operates autonomously within its responsibility boundary
- Communicates via structured Pydantic state objects
- Participates in a controlled LangGraph workflow
- Can trigger routing changes (e.g., escalation, reflection loop)

This design mirrors real-world clinical workflow systems rather than simple prompt-based chatbots.

### Agent Roles

| Agent | Role |
|-------|------|
| **Intake Agent** | Parses demographics, detects red flags via keyword scan, uses LLM to extract structured symptom details |
| **Critic Agent** | Reviews intake for clinical gaps, detects missed red flags via LLM, drives the reflection loop |
| **Triage Agent** | Hybrid rule+LLM urgency classification (EMERGENCY → NON_URGENT) + department routing |
| **Synthesis Agent** | Generates full structured medical briefing with differentials, workup recommendations, and clinician notes |

### LangGraph Flow

```
intake → [escalation?] → critic → [approved?] → triage → synthesis → END
              ↑               └── [rejected, loop back] ──┘
              └── (red flags → fast-path EMERGENCY)
```

---

## Project Structure

```
medical_triage/
├── main.py                          # API server entrypoint
├── requirements.txt
├── .env.example
│
├── config/
│   ├── __init__.py
│   └── settings.py                  # All config, red flags, symptom tree
│
├── backend/
│   ├── __init__.py
│   ├── agents/
│   │   ├── intake_agent.py          # Patient intake + red flag detection
│   │   ├── critic_agent.py          # Quality review + reflection loop
│   │   ├── triage_agent.py          # Urgency + department classification
│   │   └── synthesis_agent.py       # Clinical briefing generation
│   ├── graph/
│   │   └── workflow.py              # LangGraph StateGraph orchestration
│   ├── models/
│   │   └── schemas.py               # All Pydantic data models
│   ├── api/
│   │   └── server.py                # FastAPI endpoints
│   └── utils/
│       ├── logger.py                # Structured logging
│       └── ollama_client.py         # Ollama REST client
│
└── frontend/
    └── app.py                       # Streamlit multi-step card UI
```

---

## Setup & Installation

### Prerequisites

- Python 3.11+
- [Ollama](https://ollama.ai) installed and running
- 8GB+ RAM recommended

### Step 1 — Clone & Install

```bash
git clone https://github.com/bharath2957s/MedTriage-Agentic-AI
cd medical_triage

python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

pip install -r requirements.txt
```

### Step 2 — Set Up Ollama

```bash
# Install Ollama from https://ollama.ai
# Then pull the model:
ollama pull llama3.2

# Start Ollama server (if not already running):
ollama serve
```

### Step 3 — Configure Environment

```bash
cp .env.example .env
# Edit .env to change model name, ports, etc. if needed
```

### Step 4 — Run the API Server

```bash
# From project root:
python main.py

# Or with uvicorn directly:
uvicorn backend.api.server:app --host 0.0.0.0 --port 8000 --reload
```

Verify: Open http://localhost:8000/docs

### Step 5 — Run the Streamlit Frontend

```bash
# In a new terminal, from project root:
streamlit run frontend/app.py --server.port 8501
```

Open: http://localhost:8501

---

## How to Use

1. **Demographics** — Enter patient age, sex, and chief complaint
2. **Symptoms** — Answer dynamically generated follow-up questions
3. **History** — Enter past medical history, medications, and allergies
4. **Analysis** — Watch the AI agents process the case in real-time
5. **Results** — View triage urgency, department routing, and clinical briefing

The **Doctor Dashboard** tab provides the full structured clinical report including differentials, recommended workup, and clinician notes — downloadable as JSON.

---

## Testing Without Ollama

If Ollama is not running, the system gracefully falls back to the `/api/demo` endpoint, which returns a realistic pre-built cardiac emergency example for UI testing.

---

## Configuration Options

| Variable | Default | Description |
|----------|---------|-------------|
| `OLLAMA_MODEL` | `llama3.2` | Any Ollama-compatible model |
| `OLLAMA_TEMP` | `0.3` | Lower = more deterministic |
| `MAX_CRITIC_ITERATIONS` | `2` | Reflection loop depth |
| `API_PORT` | `8000` | Backend API port |
| `DEBUG` | `false` | Enable hot reload |

**Recommended models** (in order of quality/speed):
- `llama3.2` — Fast, good quality (recommended)
- `llama3.1:8b` — Slightly slower, higher quality
- `mistral` — Alternative good option
- `phi3` — Fastest, lighter quality

---

## Pydantic Data Models

| Model | Purpose |
|-------|---------|
| `IntakeState` | Full patient session state passed through the graph |
| `TriageDecision` | Urgency level + department + rationale + confidence |
| `MedicalSummary` | Complete final briefing with all agent outputs |
| `CriticFeedback` | Critique results from the reflection loop |
| `SymptomDetail` | Structured individual symptom with severity/duration |

---

## Emergency Escalation Logic

The system uses a two-layer neuro-symbolic emergency detection architecture:

1. **Deterministic Pattern-Based Rule Engine (Clinical Rule Layer)** — Structured, normalized pattern matching for life-threatening presentations (e.g., crushing chest pain, stroke symptoms, uncontrolled bleeding, respiratory failure, suicidal intent). Triggers immediate escalation without relying on LLM output.
2. **LLM Contextual Detection (Critic + Triage Agents)** — Identifies subtle, progressive, or context-dependent red flags not explicitly captured by deterministic patterns (e.g., concerning severity progression, high-risk comorbidities, neurologic warning signs).

When escalation triggers:
- LLM reasoning is bypassed (deterministic fast path)
- Triage Agent returns EMERGENCY immediately
- Emergency department routing is enforced
- High-priority actions are generated automatically
- A prominent emergency alert is displayed in the frontend.

---

## API Reference

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/api/questions` | POST | Get dynamic symptom questions |
| `/api/triage` | POST | Run full triage workflow |
| `/api/demo` | GET | Demo result (no LLM needed) |
| `/docs` | GET | Interactive Swagger UI |

---

## Disclaimer

This system is a **research prototype** demonstrating multi-agent AI orchestration patterns. It:
- Does NOT replace professional medical judgment
- Should NOT be used for real medical decisions
- Has NOT been validated clinically
- Is intended for educational and research purposes only

Always consult a licensed healthcare professional for medical concerns.
