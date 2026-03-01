"""
LangGraph Workflow Orchestration
=================================
Defines the multi-agent graph with:
  - State management via TypedDict
  - Conditional routing (escalation → bypass, critic → loop)
  - Reflection loop controlled by Critic Agent
  - Clear node separation for each agent

Graph flow:
  intake → critic → [loop back OR triage] → synthesis → END
  (escalation path: intake → escalation_handler → END)
"""

from typing import TypedDict, Annotated, Any
from langgraph.graph import StateGraph, END
import operator

from backend.agents.intake_agent import run_intake_agent
from backend.agents.critic_agent import run_critic_agent
from backend.agents.triage_agent import run_triage_agent
from backend.agents.synthesis_agent import run_synthesis_agent
from backend.models.schemas import IntakeState, TriageDecision, MedicalSummary
from backend.utils.logger import get_logger
from config.settings import app_config

logger = get_logger("graph.workflow")


# ─── LangGraph State Schema ───────────────────────────────────────────────────
class WorkflowState(TypedDict):
    """
    The shared state object passed between all graph nodes.
    Each node reads from and writes to this dict.
    """
    raw_input: dict                         # Original frontend payload
    intake_state: IntakeState | None        # Output of Intake Agent
    triage_decision: TriageDecision | None  # Output of Triage Agent
    final_summary: MedicalSummary | None    # Output of Synthesis Agent
    critic_iterations: int                  # Loop counter
    error: str | None                       # Error message if any step fails


# ─── Graph Node Functions ──────────────────────────────────────────────────────

def node_intake(state: WorkflowState) -> WorkflowState:
    """Intake Agent node — processes raw patient input."""
    logger.info("═══ NODE: Intake Agent ═══")
    try:
        intake_state = run_intake_agent(state["raw_input"])
        intake_state.iterations = state.get("critic_iterations", 0)
        return {**state, "intake_state": intake_state}
    except Exception as e:
        logger.error(f"Intake node error: {e}")
        return {**state, "error": str(e)}


def node_critic(state: WorkflowState) -> WorkflowState:
    """Critic Agent node — reviews intake and provides feedback."""
    logger.info("═══ NODE: Critic Agent ═══")
    intake = state.get("intake_state")
    if not intake:
        return {**state, "error": "No intake state available for Critic."}

    try:
        feedback = run_critic_agent(intake)
        iterations = state.get("critic_iterations", 0) + 1

        # Update intake state based on feedback
        intake.critic_approved = feedback.approved
        intake.iterations = iterations

        # If Critic found new red flags → escalate
        if feedback.missed_red_flags:
            intake.red_flags_detected.extend(
                f for f in feedback.missed_red_flags
                if f not in intake.red_flags_detected
            )
            if len(intake.red_flags_detected) > 0:
                intake.escalation_triggered = True

        return {
            **state,
            "intake_state": intake,
            "critic_iterations": iterations,
        }
    except Exception as e:
        logger.error(f"Critic node error: {e}")
        return {**state, "error": str(e)}


def node_triage(state: WorkflowState) -> WorkflowState:
    """Triage Agent node — assigns urgency and department."""
    logger.info("═══ NODE: Triage Agent ═══")
    intake = state.get("intake_state")
    if not intake:
        return {**state, "error": "No intake state for triage."}

    try:
        decision = run_triage_agent(intake)
        return {**state, "triage_decision": decision}
    except Exception as e:
        logger.error(f"Triage node error: {e}")
        return {**state, "error": str(e)}


def node_synthesis(state: WorkflowState) -> WorkflowState:
    """Synthesis Agent node — generates final medical briefing."""
    logger.info("═══ NODE: Synthesis Agent ═══")
    intake = state.get("intake_state")
    triage = state.get("triage_decision")

    if not intake or not triage:
        return {**state, "error": "Missing intake or triage data for synthesis."}

    try:
        summary = run_synthesis_agent(intake, triage)
        return {**state, "final_summary": summary}
    except Exception as e:
        logger.error(f"Synthesis node error: {e}")
        return {**state, "error": str(e)}


def node_escalation(state: WorkflowState) -> WorkflowState:
    """
    Emergency escalation handler.
    Runs a fast-path triage + summary for red-flag cases.
    """
    logger.warning("═══ NODE: Emergency Escalation ═══")
    intake = state.get("intake_state")
    if not intake:
        return {**state, "error": "No intake state for escalation."}

    triage = run_triage_agent(intake)  # Will return EMERGENCY
    summary = run_synthesis_agent(intake, triage)
    return {**state, "triage_decision": triage, "final_summary": summary}


# ─── Conditional Routing Functions ────────────────────────────────────────────

def route_after_intake(state: WorkflowState) -> str:
    """After intake: check for immediate escalation."""
    intake = state.get("intake_state")
    if state.get("error"):
        return END
    if intake and intake.escalation_triggered:
        logger.warning("Routing to ESCALATION path.")
        return "escalation"
    return "critic"


def route_after_critic(state: WorkflowState) -> str:
    """After critic: loop back to intake if rejected, else proceed to triage."""
    if state.get("error"):
        return END

    intake = state.get("intake_state")
    if not intake:
        return END

    iterations = state.get("critic_iterations", 0)

    if intake.critic_approved or iterations >= app_config.max_critic_iterations:
        logger.info(f"Critic approved (iterations={iterations}). Routing to triage.")
        return "triage"
    else:
        logger.info(f"Critic rejected. Routing back to intake (iteration {iterations}).")
        return "intake"


# ─── Graph Construction ────────────────────────────────────────────────────────

def build_workflow() -> StateGraph:
    """
    Assembles and compiles the LangGraph StateGraph.
    Returns a compiled graph ready for invocation.
    """
    graph = StateGraph(WorkflowState)

    # Register nodes
    graph.add_node("intake", node_intake)
    graph.add_node("critic", node_critic)
    graph.add_node("triage", node_triage)
    graph.add_node("synthesis", node_synthesis)
    graph.add_node("escalation", node_escalation)

    # Entry point
    graph.set_entry_point("intake")

    # Conditional edges
    graph.add_conditional_edges(
        "intake",
        route_after_intake,
        {
            "critic": "critic",
            "escalation": "escalation",
            END: END,
        },
    )

    graph.add_conditional_edges(
        "critic",
        route_after_critic,
        {
            "intake": "intake",   # Reflection loop
            "triage": "triage",
            END: END,
        },
    )

    # Linear edges
    graph.add_edge("triage", "synthesis")
    graph.add_edge("synthesis", END)
    graph.add_edge("escalation", END)

    logger.info("LangGraph workflow compiled successfully.")
    return graph.compile()


# Singleton compiled graph
triage_workflow = build_workflow()


def run_workflow(raw_input: dict) -> WorkflowState:
    """
    Public entry point to execute the full triage workflow.

    Args:
        raw_input: Patient data dict from the frontend/API.

    Returns:
        Final WorkflowState with all agent outputs.
    """
    logger.info("Starting triage workflow execution.")
    initial_state: WorkflowState = {
        "raw_input": raw_input,
        "intake_state": None,
        "triage_decision": None,
        "final_summary": None,
        "critic_iterations": 0,
        "error": None,
    }
    result = triage_workflow.invoke(initial_state)
    logger.info("Triage workflow execution complete.")
    return result
