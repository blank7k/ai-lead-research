import time
from typing import Tuple
from loguru import logger
from models.domain import Lead
from tools.registry import IResearchTool


class ToolExecutor:
    """Coordinates tool execution, measuring timings, and recording relative timeline observability."""

    def execute(self, tool: IResearchTool, lead: Lead) -> Tuple[Lead, str]:
        """
        Executes a research tool on the given lead, measuring duration and timeline offsets.
        
        Args:
            tool: Concrete IResearchTool to execute.
            lead: The current Lead state.
            
        Returns:
            Tuple[Lead, str]: Updated Lead object and execution trace summary.
        """
        # 1. Establish the timeline start if this is the first tool run
        run_start = lead.enrichments.get("run_start_time")
        if run_start is None:
            run_start = time.time()
            lead.enrichments["run_start_time"] = run_start
            lead.enrichments.setdefault("timeline", []).append("0.0 Start")
            
        # 2. Record tool start offset on timeline
        offset = time.time() - run_start
        tool_display = tool.name.replace("_", " ").title()
        lead.enrichments.setdefault("timeline", []).append(f"{offset:.1f} {tool_display}")
        
        logger.info(f"Start tool execution: '{tool.name}' for brand: '{lead.brand_name}'")
        start_tool_time = time.time()
        
        try:
            # 3. Execute the tool concretely
            updated_lead, trace_summary = tool.execute(lead)
            return updated_lead, trace_summary
            
        except Exception as e:
            logger.error(f"Error during tool execution '{tool.name}' on brand '{lead.brand_name}': {e}")
            raise e
            
        finally:
            # 4. Measure duration and record tool profiling
            duration = time.time() - start_tool_time
            lead.enrichments.setdefault("tool_durations", {})[tool.name] = duration
            logger.info(f"Completed tool execution: '{tool.name}' for brand: '{lead.brand_name}' | Duration: {duration:.2f}s")
