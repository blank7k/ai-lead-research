from typing import Literal
from loguru import logger
from langgraph.graph import StateGraph, END
from schemas.agent_state import AgentState
from agents.brand_researcher import brand_research_node
from agents.contact_retriever import contact_retriever_node


def router(state: AgentState) -> Literal["contact_retriever", "end"]:
    """Conditional router that decides which node to visit next."""
    next_step = state.next_step
    
    if next_step == "contact_retriever":
        return "contact_retriever"
    
    return "end"


def build_research_graph() -> StateGraph:
    """
    Construct and compile the LangGraph workflow for lead research.
    
    Returns:
        A compiled LangGraph StateGraph instance ready for execution.
    """
    logger.info("Initializing multi-agent StateGraph.")
    
    # 1. Initialize the StateGraph with the AgentState schema
    workflow = StateGraph(AgentState)
    
    # 2. Add node functions
    workflow.add_node("brand_researcher", brand_research_node)
    workflow.add_node("contact_retriever", contact_retriever_node)
    
    # 3. Configure entrypoint and edges
    workflow.set_entry_point("brand_researcher")
    
    # 4. Add conditional routing from researcher
    workflow.add_conditional_edges(
        "brand_researcher",
        router,
        {
            "contact_retriever": "contact_retriever",
            "end": END
        }
    )
    
    # 5. Connect contact retriever to finish line
    workflow.add_edge("contact_retriever", END)
    
    # 6. Compile graph
    compiled_graph = workflow.compile()
    logger.info("LangGraph workflow compiled successfully.")
    
    return compiled_graph


# Pre-compiled graph instance
research_graph = build_research_graph()
