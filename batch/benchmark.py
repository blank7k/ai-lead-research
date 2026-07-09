from typing import List, Dict
from loguru import logger
from models.domain import Lead


class BenchmarkCollector:
    """Calculates research metrics, fields coverage, and tool execution profiles."""

    @staticmethod
    def calculate_metrics(leads: List[Lead], total_runtime: float, failures: int, skipped: int) -> dict:
        """Computes system-wide coverage percentages and tool timings averages."""
        processed_count = len(leads)
        
        website_count = sum(1 for l in leads if l.website and l.website != "unknown")
        email_count = sum(1 for l in leads if l.contacts.emails)
        phone_count = sum(1 for l in leads if l.contacts.phones)
        address_count = sum(1 for l in leads if l.contacts.addresses)
        founder_count = sum(1 for l in leads if l.founder_name)
        linkedin_count = sum(1 for l in leads if l.socials.linkedin)
        bp_count = sum(1 for l in leads if l.socials.google_maps or l.enrichments.get("rating") is not None)
        
        # Calculate coverage percentages
        website_pct = (website_count / processed_count * 100) if processed_count > 0 else 0.0
        email_pct = (email_count / processed_count * 100) if processed_count > 0 else 0.0
        phone_pct = (phone_count / processed_count * 100) if processed_count > 0 else 0.0
        address_pct = (address_count / processed_count * 100) if processed_count > 0 else 0.0
        founder_pct = (founder_count / processed_count * 100) if processed_count > 0 else 0.0
        linkedin_pct = (linkedin_count / processed_count * 100) if processed_count > 0 else 0.0
        bp_pct = (bp_count / processed_count * 100) if processed_count > 0 else 0.0
        
        avg_confidence = (sum(l.confidence_score for l in leads) / processed_count) if processed_count > 0 else 0.0
        avg_runtime = (total_runtime / processed_count) if processed_count > 0 else 0.0
        
        # Collect and average tool durations
        tool_sums: Dict[str, float] = {}
        tool_counts: Dict[str, int] = {}
        for lead in leads:
            tool_durations = lead.enrichments.get("tool_durations", {})
            for tool_name, duration in tool_durations.items():
                tool_sums[tool_name] = tool_sums.get(tool_name, 0.0) + duration
                tool_counts[tool_name] = tool_counts.get(tool_name, 0) + 1
                
        tool_averages = {}
        for tool_name, total_duration in tool_sums.items():
            count = tool_counts[tool_name]
            tool_averages[tool_name] = total_duration / count if count > 0 else 0.0
            
        return {
            "processed": processed_count,
            "website_coverage": website_pct,
            "email_coverage": email_pct,
            "phone_coverage": phone_pct,
            "address_coverage": address_pct,
            "founder_coverage": founder_pct,
            "linkedin_coverage": linkedin_pct,
            "bp_coverage": bp_pct,
            "avg_confidence": avg_confidence,
            "failures": failures,
            "skipped": skipped,
            "avg_runtime": avg_runtime,
            "total_runtime": total_runtime,
            "tool_averages": tool_averages
        }

    @staticmethod
    def print_report(metrics: dict) -> None:
        """Formats and prints the metrics summary report exactly to specifications."""
        print("\n" + "=" * 50)
        print("Lead Intelligence Benchmark")
        print("=" * 50)
        print(f"Processed: {metrics['processed']}\n")
        print(f"Website Coverage: {metrics['website_coverage']:.0f}%")
        print(f"Email Coverage: {metrics['email_coverage']:.0f}%")
        print(f"Phone Coverage: {metrics['phone_coverage']:.0f}%")
        print(f"Address Coverage: {metrics['address_coverage']:.0f}%")
        print(f"Founder Coverage: {metrics['founder_coverage']:.0f}%")
        print(f"LinkedIn Coverage: {metrics['linkedin_coverage']:.0f}%")
        print(f"Business Profile Coverage: {metrics['bp_coverage']:.0f}%\n")
        print(f"Failures: {metrics['failures']}")
        print(f"Skipped: {metrics['skipped']}\n")
        print(f"Average Confidence: {metrics['avg_confidence']:.2f}")
        
        # Render average and total durations in minutes if they are high
        avg_rt = metrics['avg_runtime']
        total_rt = metrics['total_runtime']
        
        if avg_rt >= 60.0:
            print(f"Average Runtime: {avg_rt/60:.1f} min")
        else:
            print(f"Average Runtime: {avg_rt:.1f} sec")
            
        if total_rt >= 60.0:
            print(f"Total Runtime: {int(total_rt/60)}m")
        else:
            print(f"Total Runtime: {total_rt:.1f} sec")
            
        print("=" * 50)
        print("\nTool Timings\n")
        
        # Display each registered tool profile duration average
        tool_names_mapping = {
            "search_tool": "Search Tool",
            "website_tool": "Website Tool",
            "business_profile_tool": "Business Profile Tool"
        }
        for key, display in tool_names_mapping.items():
            avg_time = metrics["tool_averages"].get(key, 0.0)
            print(f"{display}:")
            print(f"{avg_time:.1f} sec\n")
            
        print("=" * 50 + "\n")
