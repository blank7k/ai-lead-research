from langgraph.graph import StateGraph
from agents.orchestrator import research_graph


def test_research_graph_build():
    """Verify that the compiled LangGraph object is correctly loaded and has the required structure."""
    assert research_graph is not None
    
    # StateGraph compiles to a CompiledStateGraph or similar wrapper
    # We can check that nodes are defined correctly
    graph_info = research_graph.get_graph()
    assert graph_info is not None
    
    nodes = list(graph_info.nodes.keys())
    assert "brand_researcher" in nodes
    assert "contact_retriever" in nodes
    assert "__start__" in nodes
