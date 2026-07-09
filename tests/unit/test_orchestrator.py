from langgraph.graph import StateGraph
from agents.orchestrator import research_graph
from agents.decision_engine import DecisionEngine
from models.domain import Lead
from schemas.agent_state import AgentState
from tools.registry import tool_registry


def test_research_graph_build():
    """Verify that the compiled LangGraph object has the new agentic node structure."""
    assert research_graph is not None
    
    graph_info = research_graph.get_graph()
    assert graph_info is not None
    
    nodes = list(graph_info.nodes.keys())
    assert "research_agent" in nodes
    assert "tool_executor" in nodes
    assert "__start__" in nodes


def test_decision_engine_sequence():
    """Verify that DecisionEngine selects tools in the correct order based on gaps."""
    # 1. Missing website -> search_tool
    lead = Lead(brand_name="Test Brand")
    assert DecisionEngine.get_next_tool(lead) == "search_tool"

    # 2. Has website, missing emails/phones -> website_tool
    lead.website = "https://test.com"
    assert DecisionEngine.get_next_tool(lead) == "website_tool"

    lead.execution_trace.append("website_tool")
    # 3. Phone, address, or maps missing -> business_profile_tool
    assert DecisionEngine.get_next_tool(lead) == "business_profile_tool"

    lead.execution_trace.append("business_profile_tool")
    # 4. Email or phone STILL missing -> contact_discovery_tool (Capability #4)
    assert DecisionEngine.get_next_tool(lead) == "contact_discovery_tool"

    lead.execution_trace.append("contact_discovery_tool")
    # 5. Founder still missing -> linkedin_tool
    assert DecisionEngine.get_next_tool(lead) == "linkedin_tool"

    lead.execution_trace.append("linkedin_tool")
    # All tools exhausted -> None
    assert DecisionEngine.get_next_tool(lead) is None


def test_stub_tool_executions():
    """Verify that stub tools return correct stubs and do not modify the lead."""
    lead = Lead(brand_name="Zara")
    
    # 1. Instagram Stub
    instagram_tool = tool_registry.get_tool("instagram_tool")
    updated_lead, trace = instagram_tool.execute(lead)
    assert "Instagram Tool" in trace
    assert "(Not Implemented)" in trace
    
    # 2. LinkedIn Stub
    linkedin_tool = tool_registry.get_tool("linkedin_tool")
    updated_lead, trace = linkedin_tool.execute(lead)
    assert "LinkedIn Tool" in trace
    assert "(Not Implemented)" in trace
