import os
import time
from typing import Literal
from loguru import logger
from langgraph.graph import StateGraph, END

from schemas.agent_state import AgentState
from models.domain import Lead
from agents.decision_engine import DecisionEngine
from tools.registry import tool_registry
from tools.executor import ToolExecutor


# Instantiate the global ToolExecutor
tool_executor = ToolExecutor()


def research_agent_node(state: AgentState) -> dict:
    """
    Research Agent node. Inspects the Lead, runs the Decision Engine,
    and writes the decision trace logs.
    """
    lead = state.lead
    logger.info(f"[ResearchAgent] Inspecting lead for brand '{lead.brand_name}'...")
    
    # 1. Run Decision Engine
    next_tool_key = DecisionEngine.get_next_tool(lead)
    
    trace_logs = []
    logs = []
    
    if next_tool_key:
        # Resolve reason and formatted display name
        missing = lead.missing_fields
        reason = "Gaps detected"
        if "website" in missing and next_tool_key == "search_tool":
            reason = "Website Missing"
        elif ("emails" in missing or "phones" in missing) and next_tool_key == "website_tool":
            reason = "Contact Info Missing"
        elif ("phones" in missing or "addresses" in missing or "google_maps" in missing) and next_tool_key == "business_profile_tool":
            reason = "Phone or Address Missing"
        elif "emails" in missing and next_tool_key == "instagram_tool":
            reason = "Email Still Missing"
        elif "founder" in missing and next_tool_key == "linkedin_tool":
            reason = "Founder Missing"
            
        # Resolve display name
        tool_display = next_tool_key.replace("_", " ").title()
        
        if next_tool_key not in ["search_tool", "website_tool"]:
            decision_trace = f"Decision:\n{reason}\n→ {tool_display}"
            trace_logs.append(decision_trace)
        logs.append(f"Decision: Execute {next_tool_key} due to {reason}")
    else:
        trace_logs.append("Research Complete")
        logs.append("Decision: Research Complete")
        
        # If complete, log the Finish relative offset to timeline
        run_start = lead.enrichments.get("run_start_time")
        if run_start:
            offset = time.time() - run_start
            lead.enrichments.setdefault("timeline", []).append(f"{offset:.1f} Finish")
        
    return {
        "next_tool": next_tool_key,
        "trace_logs": trace_logs,
        "logs": logs
    }


def tool_executor_node(state: AgentState) -> dict:
    """
    Generic tool execution node. Delegates tool execution to the central ToolExecutor.
    """
    tool_key = state.next_tool
    if not tool_key:
        logger.warning("[ToolExecutor] Executor triggered but no next_tool set in state.")
        return {}
        
    logger.info(f"[ToolExecutor] Dispatching tool: '{tool_key}'")
    
    # 1. Look up tool in registry
    tool_instance = tool_registry.get_tool(tool_key)
    
    # 2. Execute tool using the wrapper ToolExecutor
    updated_lead, trace_summary = tool_executor.execute(tool_instance, state.lead)
    
    # 3. Add to tool execution trace list (preventing duplicate runs)
    updated_lead.execution_trace.append(tool_key)
    
    return {
        "lead": updated_lead,
        "trace_logs": [trace_summary],
        "logs": [f"Executed {tool_key}"]
    }


def router(state: AgentState) -> Literal["tool_executor", "end"]:
    """Conditional edge router. Determines if a tool needs execution or if graph finishes."""
    if state.next_tool:
        return "tool_executor"
    return "end"


def save_graph_visuals(compiled_graph) -> None:
    """Generates StateGraph representation files in the data/ directory."""
    try:
        os.makedirs("data", exist_ok=True)
        
        # 1. Save Mermaid string
        mermaid_code = compiled_graph.get_graph().draw_mermaid()
        with open("data/graph.mermaid", "w", encoding="utf-8") as f:
            f.write(mermaid_code)
        logger.info("Saved StateGraph visual layout: data/graph.mermaid")
        
        # 2. Attempt rendering PNG diagram (requires pyppeteer/pygraphviz)
        try:
            png_bytes = compiled_graph.get_graph().draw_mermaid_png()
            with open("data/graph.png", "wb") as f:
                f.write(png_bytes)
            logger.info("Saved visual graph image: data/graph.png")
        except Exception as pe:
            logger.warning(f"Could not render graph to PNG image: {pe}")
            
    except Exception as e:
        logger.error(f"Failed to generate visual graph drawings: {e}")


def build_research_graph() -> StateGraph:
    """
    Constructs and compiles the dynamic Agentic Lead Research graph.
    
    Research Agent Node -> Router -> Tool Executor -> Research Agent Node (Loop)
    """
    logger.info("Initializing Agentic StateGraph.")
    
    workflow = StateGraph(AgentState)
    
    # Add Nodes
    workflow.add_node("research_agent", research_agent_node)
    workflow.add_node("tool_executor", tool_executor_node)
    
    # Configure Entrypoint
    workflow.set_entry_point("research_agent")
    
    # Configure Routing and Loop
    workflow.add_conditional_edges(
        "research_agent",
        router,
        {
            "tool_executor": "tool_executor",
            "end": END
        }
    )
    
    # Complete loop: tool execution always returns back to the agent node
    workflow.add_edge("tool_executor", "research_agent")
    
    # Compile
    compiled_graph = workflow.compile()
    logger.info("Agentic LangGraph workflow compiled successfully.")
    
    # Export Mermaid diagrams
    save_graph_visuals(compiled_graph)
    
    return compiled_graph


# Pre-compiled agent graph
research_graph = build_research_graph()
