"""
Compatibility alias forwarding tools_critics to tools_critic.
"""
from backend.agent.tools_critic import (
    extract_numbers_from_text,
    extract_numbers_from_dataframe,
    extract_numbers_from_analytics,
    verify_analysis_output,
    self_correct_summary,
)

__all__ = [
    "extract_numbers_from_text",
    "extract_numbers_from_dataframe",
    "extract_numbers_from_analytics",
    "verify_analysis_output",
    "self_correct_summary",
]
