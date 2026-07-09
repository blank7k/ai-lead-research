import os
import time
import sys
import concurrent.futures
from typing import List, Optional
from loguru import logger

from models.domain import Lead
from schemas.agent_state import AgentState
from agents.orchestrator import research_graph
from batch.checkpoint_manager import CheckpointManager
from batch.csv_loader import CSVLoader
from batch.csv_exporter import CSVExporter
from batch.benchmark import BenchmarkCollector
from services.sheets_service import GoogleSheetsService


# Ensure logging to logs/batch.log is active
os.makedirs("logs", exist_ok=True)
logger.add(
    "logs/batch.log", 
    format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {message}", 
    level="DEBUG",
    rotation="10 MB"
)


class BatchProcessor:
    """Processor running research runs concurrently over batches of target D2C brands."""

    def __init__(
        self,
        workers: int = 3,
        delay_between_batches: float = 2.0,
        timeout: float = 120.0,
        checkpoint_filepath: str = "data/checkpoint.json",
        results_filepath: str = "data/results.csv"
    ) -> None:
        self.workers = workers
        self.delay_between_batches = delay_between_batches
        self.timeout = timeout
        
        self.checkpoint_manager = CheckpointManager(checkpoint_filepath)
        self.csv_exporter = CSVExporter()
        self.sheets_service = GoogleSheetsService()
        self.results_filepath = results_filepath
        
        self._setup_tool_profiling()

    def _setup_tool_profiling(self) -> None:
        """
        Dynamically wraps IResearchTool.execute calls at runtime.
        Measures the precise duration of each tool's run without modifying core frozen classes.
        """
        from tools.registry import tool_registry
        for tool_name in tool_registry.list_tools():
            tool = tool_registry.get_tool(tool_name)
            
            # Avoid wrapping a tool more than once if initialized repeatedly
            if not hasattr(tool, "_original_execute"):
                tool._original_execute = tool.execute
                
                # Create scoped wrapper preserving closure values
                def make_wrapper(t_name, original_exec):
                    def wrapper(lead: Lead):
                        logger.info(f"Start tool execution: '{t_name}' for brand: '{lead.brand_name}'")
                        start = time.time()
                        try:
                            updated_lead, trace = original_exec(lead)
                            return updated_lead, trace
                        except Exception as e:
                            logger.error(f"Tool '{t_name}' execution failed for brand '{lead.brand_name}': {e}")
                            raise e
                        finally:
                            elapsed = time.time() - start
                            lead.enrichments.setdefault("tool_durations", {})[t_name] = elapsed
                            logger.info(f"Tool execution complete: '{t_name}' for brand: '{lead.brand_name}' | Runtime: {elapsed:.2f}s")
                    return wrapper
                    
                tool.execute = make_wrapper(tool.name, tool._original_execute)
                logger.debug(f"Applied runtime profiling wrapper to tool: '{tool.name}'")

    def _run_brand_with_timeout(self, brand_name: str) -> Lead:
        """Runs the LangGraph research graph for a single brand within a strict timeout block."""
        # 1. Instantiate state
        lead = Lead(brand_name=brand_name)
        state = AgentState(lead=lead)
        
        # 2. Define target function to run in inner executor
        def invoke_graph():
            return research_graph.invoke(state)

        # 3. Execute with thread timeout guard
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as inner_executor:
            future = inner_executor.submit(invoke_graph)
            try:
                final_state = future.result(timeout=self.timeout)
                return final_state["lead"]
            except concurrent.futures.TimeoutError as te:
                logger.error(f"Brand '{brand_name}' research run timed out after {self.timeout}s.")
                raise TimeoutError(f"Timeout of {self.timeout}s exceeded.") from te
            except Exception as e:
                logger.error(f"Brand '{brand_name}' graph execution error: {e}")
                raise e

    def _process_single_brand(self, brand_name: str) -> Optional[Lead]:
        """Wrapper worker function processing a single brand, exporting to Sheets and updating checkpoints."""
        logger.info(f"Starting research run for brand: '{brand_name}'")
        start_time = time.time()
        
        try:
            lead = self._run_brand_with_timeout(brand_name)
            elapsed = time.time() - start_time
            
            # Immediately add to local checkpoint persistence
            self.checkpoint_manager.add_completed(brand_name)
            
            # Immediately append to Google Sheets
            try:
                self.sheets_service.append_leads(None, [lead])
            except Exception as se:
                # Log Sheets error, do NOT fail the batch run
                logger.error(f"Failed to append brand '{brand_name}' to Google Sheets: {se}")
                
            logger.info(f"Completed research run for brand: '{brand_name}' | Runtime: {elapsed:.2f}s | Confidence: {lead.confidence_score:.2f}")
            return lead
            
        except Exception as e:
            logger.error(f"Failure processing brand '{brand_name}': {e}")
            # Return None to signal a failed run
            return None

    def run_batch(self, input_csv_path: str) -> dict:
        """
        Executes a batch run over brands loaded from the input CSV file.
        Respects concurrency limits, handles timeouts, supports resumes, and prints benchmark report.
        """
        logger.info("Initializing Batch Processing Session.")
        start_time = time.time()
        
        # 1. Load target brands
        all_brands = CSVLoader.load_brands(input_csv_path)
        if not all_brands:
            logger.warning("No brands found to process.")
            return {}
            
        # 2. Check resume history
        completed_brands = self.checkpoint_manager.load_completed()
        
        remaining_brands = [b for b in all_brands if b not in completed_brands]
        skipped_count = len(all_brands) - len(remaining_brands)
        
        logger.info(f"Total Target Brands: {len(all_brands)} | Completed (Skipped): {skipped_count} | Remaining to Run: {len(remaining_brands)}")
        
        leads: List[Lead] = []
        failures_count = 0
        
        # 3. Concurrently run target brands in a thread pool
        if remaining_brands:
            # We can group remaining brands into batch sizes to implement batch throttling delays
            batch_size = self.workers
            for i in range(0, len(remaining_brands), batch_size):
                batch_subset = remaining_brands[i:i+batch_size]
                
                if i > 0 and self.delay_between_batches > 0:
                    logger.info(f"Throttling Batch. Sleeping for {self.delay_between_batches}s...")
                    time.sleep(self.delay_between_batches)
                    
                with concurrent.futures.ThreadPoolExecutor(max_workers=self.workers) as executor:
                    # Map the execution function across the current batch
                    future_to_brand = {executor.submit(self._process_single_brand, b): b for b in batch_subset}
                    
                    for future in concurrent.futures.as_completed(future_to_brand):
                        brand = future_to_brand[future]
                        try:
                            lead_result = future.result()
                            if lead_result:
                                leads.append(lead_result)
                            else:
                                failures_count += 1
                        except Exception as e:
                            logger.error(f"ThreadPool exception for brand '{brand}': {e}")
                            failures_count += 1
                            
        total_runtime = time.time() - start_time
        
        # 4. Load all leads that have completed across runs to compile the full results export
        # If we resumed, we want the CSV export to contain all results. For this simple model, 
        # we export what we processed in this run. If desired, we can merge with past exports.
        self.csv_exporter.export_leads(leads, self.results_filepath)
        
        # 5. Calculate and output benchmark metrics
        metrics = BenchmarkCollector.calculate_metrics(leads, total_runtime, failures_count, skipped_count)
        BenchmarkCollector.print_report(metrics)
        
        return metrics
