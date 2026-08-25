"""
Follow-up Question Generator.
After each successful analysis, suggests 3 contextually relevant follow-up questions
the user could ask next, making the agent feel conversational and alive.
"""
import re
from backend.llm_client import call_llm

FOLLOWUP_SYSTEM_PROMPT = """You are a helpful data analyst assistant.
Given a user's original question and the resulting SQL query + business summary, 
suggest exactly 3 insightful follow-up questions the user might want to explore next.

Rules:
1. Each question must be directly related to the data or the analysis just performed.
2. Questions should progressively deepen the analysis (drill down, compare, forecast, etc.).
3. Return ONLY a JSON array of 3 strings. No preamble, no markdown, no extra text.

Example output:
["Which region had the highest growth rate last quarter?", "How does this compare to last year?", "Which product category is driving the most revenue?"]
"""


def generate_followup_suggestions(question: str, sql: str, summary: str) -> list[str]:
    """
    Generates 3 contextually relevant follow-up questions after a successful analysis.
    Returns a list of question strings (falls back to generic suggestions on error).
    """
    fallback = [
        "How does this compare across different time periods?",
        "Which segment contributes the most to these results?",
        "Can you break this down further by a different dimension?",
    ]

    try:
        prompt = f"""Original Question: "{question}"

Generated SQL:
{sql}

Business Summary:
{summary}

Suggest 3 follow-up questions as a JSON array:"""

        raw = call_llm(prompt, system_instruction=FOLLOWUP_SYSTEM_PROMPT)
        cleaned = raw.strip()

        # Strip markdown if present
        if "```" in cleaned:
            match = re.search(r"```(?:json)?\s*(\[.*?\])\s*```", cleaned, re.DOTALL)
            if match:
                cleaned = match.group(1)
            else:
                cleaned = cleaned.replace("```json", "").replace("```", "").strip()

        import json
        suggestions = json.loads(cleaned)
        if isinstance(suggestions, list) and len(suggestions) >= 2:
            return [str(q).strip() for q in suggestions[:3]]
    except Exception:
        pass

    return fallback
