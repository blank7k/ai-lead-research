import sys
import io
import time
from typing import List
from loguru import logger

# Reconfigure stdout/stderr to support Unicode characters in Windows terminal
if hasattr(sys.stdout, 'buffer'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
if hasattr(sys.stderr, 'buffer'):
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

from config.settings import settings
from models.domain import Lead, Contacts, Socials
from schemas.agent_state import AgentState
from agents.orchestrator import research_graph


def run_lead_research_agent(brand_name: str) -> Lead:
    """
    Executes the Agentic Lead Research workflow using LangGraph.
    
    The Research Agent inspects the Lead data, determines missing fields,
    calls the appropriate tools via registry, and traces execution.
    
    Args:
        brand_name: The name of the brand to research.
        
    Returns:
        The final Lead object with trace logs and collected contact information.
    """
    logger.info(f"=== Starting Agentic Research for brand: '{brand_name}' ===")
    
    # 1. Initialize domain Lead model
    # Leave website/contacts/socials/founder empty so the agent detects missing data
    lead = Lead(brand_name=brand_name)
    
    # 2. Initialize AgentState
    state = AgentState(lead=lead)
    
    # 3. Invoke Compiled StateGraph
    try:
        final_state = research_graph.invoke(state)
        final_lead = final_state.get("lead") or lead
        
        # Merge trace_logs from LangGraph state into the printed output
        trace_logs = final_state.get("trace_logs") or []
        
        print("\n" + "=" * 50)
        print(f"AGENT EXECUTION TRACE FOR: {brand_name.upper()}")
        print("=" * 50)
        for log in trace_logs:
            print(log)
            print() # Print empty line for spacing
        print("=" * 50)
        
        # Save trace logs into final lead execution trace for record
        final_lead.execution_trace = trace_logs
        return final_lead
        
    except Exception as e:
        logger.error(f"Failed during agentic research loop for '{brand_name}': {e}")
        raise e


def main():
    """Main CLI entry point."""
    args = sys.argv[1:]
    if args:
        targets = args
    else:
        # Default target D2C brands
        targets = ["ROSANI", "Perte D'ego", "POMCHA"]
        
    logger.info(f"Initializing Agentic Lead Research System for: {targets}")
    
    for idx, brand_name in enumerate(targets):
        if idx > 0:
            # Respect search throttle limit between brands
            logger.info("Throttling request. Sleeping for 5 seconds to prevent rate limiting...")
            time.sleep(5)
            
        try:
            lead = run_lead_research_agent(brand_name)
            
            # Print the final Lead JSON structure
            print("\n" + "=" * 50)
            print(f"CONSOLIDATED LEAD RESULT: {brand_name.upper()}")
            print("=" * 50)
            print(lead.model_dump_json(indent=2))
            print("=" * 50 + "\n")
            
        except Exception as e:
            logger.error(f"Failed to process brand '{brand_name}': {e}")
            
    logger.info("Agentic Lead Research System execution complete.")


if __name__ == "__main__":
    main()
