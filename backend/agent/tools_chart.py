"""
Chart Generation Tool: Uses LLM to generate matplotlib visualizations from tabular SQL results.
"""
import base64
import io
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import re
from backend.llm_client import call_llm

def generate_chart(question: str, df: pd.DataFrame) -> str:
    """
    Given user question and result dataframe, asks LLM if visualization is helpful.
    If yes, generates Matplotlib code, executes it, and returns base64 PNG string.
    Returns None if chart is not appropriate or if dataframe is empty.
    """
    if df.empty or len(df) < 1:
        return None

    # Limit rows passed to LLM for code generation prompt
    sample_data = df.head(10).to_string(index=False)
    columns_info = list(df.columns)

    system_instruction = (
        "You are a Matplotlib Python chart generator. Given a pandas DataFrame `df` and user question, "
        "write Python code using `ax` (an existing Matplotlib Axes object) or `plt` to create a clean bar, line, or pie chart.\n"
        "Rules:\n"
        "1. Output ONLY Python code inside ```python ... ``` block.\n"
        "2. `df`, `fig`, `ax`, `plt` are already defined.\n"
        "3. Use `ax.set_title()`, `ax.set_xlabel()`, `ax.set_ylabel()`, `plt.xticks(rotation=45)` as appropriate.\n"
        "4. If no chart is appropriate (e.g. single number result), output strictly: NO_CHART"
    )

    prompt = (
        f"User Question: {question}\n"
        f"Columns: {columns_info}\n"
        f"Sample Data:\n{sample_data}\n\n"
        f"Python Plot Code:"
    )

    try:
        response = call_llm(prompt, system_instruction).strip()
        
        if "NO_CHART" in response or not response:
            return None

        # Clean python code block formatting if present
        py_code = response.strip()
        match = re.search(r"```(?:python)?\s*(.*?)\s*```", py_code, re.DOTALL | re.IGNORECASE)
        if match:
            py_code = match.group(1).strip()
        elif py_code.startswith("```"):
            py_code = re.sub(r"^```[a-zA-Z]*\n?", "", py_code)
            py_code = re.sub(r"\n?```$", "", py_code).strip()

        # Setup figure
        fig, ax = plt.subplots(figsize=(8, 4.5), dpi=120)
        
        # Local execution namespace
        exec_globals = {
            "df": df.copy(),
            "plt": plt,
            "fig": fig,
            "ax": ax
        }

        exec(py_code, exec_globals)

        plt.tight_layout()
        
        buffer = io.BytesIO()
        plt.savefig(buffer, format="png")
        plt.close(fig)
        buffer.seek(0)
        
        encoded_image = base64.b64encode(buffer.read()).decode("utf-8")
        return encoded_image
    except Exception as e:
        plt.close("all")
        print(f"Chart generation error: {e}")
        return None
