"""
SQL Generation & Guardrails Tool.
Generates DuckDB SQL from natural language, enforces read-only guardrails, and self-corrects on syntax errors.
"""
import re
import pandas as pd
import duckdb
from backend.llm_client import call_llm

SQL_LLM_TIMEOUT = 90.0  # seconds; main SQL generation is the call that matters most


SQL_GUARDRAIL_FORBIDDEN = [
    r"\bDROP\b", r"\bDELETE\b", r"\bINSERT\b", r"\bUPDATE\b",
    r"\bALTER\b", r"\bTRUNCATE\b", r"\bCREATE\b", r"\bGRANT\b", r"\bREVOKE\b"
]

def validate_sql_guardrails(sql: str) -> tuple[bool, str]:
    """
    Validates that the SQL query is strictly a read-only SELECT statement.
    """
    cleaned_sql = sql.strip().strip(";").upper()
    
    for pattern in SQL_GUARDRAIL_FORBIDDEN:
        if re.search(pattern, cleaned_sql):
            return False, "Forbidden keyword detected in query. Only read-only SELECT queries are allowed."
            
    if not cleaned_sql.startswith("SELECT") and not cleaned_sql.startswith("WITH"):
        return False, "Query must begin with SELECT or WITH."
        
    return True, ""

def enforce_limit(sql: str, max_limit: int = 500) -> str:
    """
    Ensures query has a LIMIT clause capping results.
    """
    if "LIMIT" not in sql.upper():
        sql = sql.strip().rstrip(";") + f" LIMIT {max_limit}"
    return sql

_STOPWORDS = {
    'the', 'a', 'an', 'of', 'in', 'on', 'for', 'to', 'and', 'or', 'is', 'are', 'was', 'were', 'be',
    'what', 'which', 'who', 'how', 'me', 'my', 'us', 'all', 'each', 'per', 'by', 'with', 'from', 'out',
    'show', 'give', 'tell', 'list', 'state', 'different', 'distinct', 'unique', 'table', 'data', 'dataset',
    'top', 'bottom', 'highest', 'lowest', 'average', 'avg', 'mean', 'total', 'sum', 'count', 'many', 'much',
    'isolate', 'examine', 'find', 'get', 'please', 'any', 'there', 'that', 'this', 'it', 'their', 'its',
}
_NUM_TYPES = ('INT', 'FLOAT', 'DOUBLE', 'DECIMAL', 'NUMERIC', 'REAL')


def _question_tokens(text: str) -> list:
    """Lower-cased alphabetic tokens with naive plural stripping (methods -> method)."""
    tokens = []
    for w in re.findall(r"[a-z]+", text.lower()):
        if len(w) > 3 and w.endswith('s') and not w.endswith('ss'):
            w = w[:-1]
        tokens.append(w)
    return tokens


def _score_column(col_name: str, q_tokens: set) -> int:
    """Number of the column-name words (split on _ / camelCase) that appear in the question."""
    spaced = re.sub(r"([a-z])([A-Z])", r"\1 \2", col_name)
    return len(set(_question_tokens(spaced)) & q_tokens)


def build_smart_fallback_sql(question: str, schema_str: str, conn: duckdb.DuckDBPyConnection = None) -> str:
    """
    Constructs a highly relevant analytical SQL query based on table schema and natural language question.
    Prevents generic 'SELECT *' queries when LLM is unavailable or offline.
    """
    tables_info = {}
    current_table = None
    
    for line in schema_str.splitlines():
        line = line.strip()
        t_match = re.match(r"^Table:\s*([a-zA-Z0-9_]+)", line)
        if t_match:
            current_table = t_match.group(1)
            tables_info[current_table] = []
            continue
            
        c_match = re.match(r"^-\s*([a-zA-Z0-9_]+)\s*\(([^)]+)\)", line)
        if c_match and current_table:
            col_name = c_match.group(1)
            col_type = c_match.group(2).upper()
            tables_info[current_table].append((col_name, col_type))
            
    if not tables_info:
        # Last-resort: return a schema-free count query
        return "SELECT COUNT(*) AS total_rows FROM data_table LIMIT 1;"
        
    # Multi-table: pick the table whose columns/name best match the question's words
    q_tokens = set(_question_tokens(question)) - _STOPWORDS
    best_table, best_score = list(tables_info.keys())[0], -1
    for tname, tcols in tables_info.items():
        score = sum(_score_column(c[0], q_tokens) for c in tcols)
        score += 2 * len(set(_question_tokens(tname)) & q_tokens)
        if score > best_score:
            best_table, best_score = tname, score
    table_name = best_table
    cols = tables_info[table_name]
    
    if not cols:
        return f'SELECT * FROM "{table_name}" LIMIT 10;'

    num_keywords = ['amount', 'sales', 'total', 'price', 'cost', 'profit', 'count', 'qty', 'quantity', 'revenue', 'units', 'score', 'rating', 'value', 'val']
    date_keywords = ['date', 'time', 'year', 'month', 'day', 'created']
    
    num_cols = [c[0] for c in cols if any(t in c[1] for t in ['INT', 'FLOAT', 'DOUBLE', 'DECIMAL', 'NUMERIC', 'REAL']) or any(k in c[0].lower() for k in num_keywords)]
    date_cols = [c[0] for c in cols if any(t in c[1] for t in ['DATE', 'TIME']) or any(k in c[0].lower() for k in date_keywords)]
    cat_cols = [c[0] for c in cols if c[0] not in num_cols and c[0] not in date_cols and not c[0].lower().endswith('_id') and c[0].lower() != 'id']

    if not cat_cols:
        cat_cols = [c[0] for c in cols if c[0] not in num_cols and c[0] not in date_cols]

    q_lower = question.lower()

    target_cat = cat_cols[0] if cat_cols else None
    target_num = num_cols[0] if num_cols else None
    target_date = date_cols[0] if date_cols else None

    # Check if user explicitly mentioned specific column name
    for c in cols:
        col_name = c[0]
        if col_name.lower() in q_lower and col_name != 'id':
            if c[0] in num_cols:
                target_num = col_name
            else:
                target_cat = col_name

    # Columns whose name words best match the question (e.g. 'payment methods' -> Payment_Method)
    max_col_score = max((_score_column(c[0], q_tokens) for c in cols), default=0)
    matched_cols = [c for c in cols if max_col_score > 0 and _score_column(c[0], q_tokens) == max_col_score]
    match_num = [c[0] for c in matched_cols if any(t in c[1] for t in _NUM_TYPES)]
    match_cat = [c[0] for c in matched_cols if not any(t in c[1] for t in _NUM_TYPES)]
    if match_num:
        target_num = match_num[0]
    if match_cat:
        target_cat = match_cat[0]

    q_words = set(re.findall(r"[a-z]+", q_lower))
    agg_words = {'average', 'avg', 'mean', 'sum', 'total', 'count', 'how', 'many', 'top', 'highest', 'lowest',
                 'outlier', 'outliers', 'anomaly', 'max', 'min', 'maximum', 'minimum', 'forecast', 'correlation', 'trend'}
    distinct_words = {'different', 'distinct', 'unique', 'list', 'types', 'kinds', 'state', 'categories', 'options', 'varieties'}

    # "List the different payment methods" -> distinct values with frequency
    if (q_words & distinct_words) and not (q_words & agg_words) and match_cat:
        c = match_cat[0]
        return f'SELECT "{c}", COUNT(*) AS count FROM "{table_name}" GROUP BY "{c}" ORDER BY count DESC LIMIT 100'

    # "Average delivery days" -> AVG of the matched numeric column (optionally by a matched category)
    if (q_words & {'average', 'avg', 'mean'}) and match_num:
        n = match_num[0]
        if match_cat:
            c = match_cat[0]
            return f'SELECT "{c}", ROUND(AVG("{n}"), 2) AS avg_{n} FROM "{table_name}" GROUP BY "{c}" ORDER BY avg_{n} DESC LIMIT 50'
        return f'SELECT ROUND(AVG("{n}"), 2) AS avg_{n} FROM "{table_name}"'

    # "Latest/earliest/most recent ..." -> return the actual row holding the extreme date
    recency_words = {'latest', 'newest', 'recent', 'last'}
    oldest_words = {'earliest', 'oldest', 'first'}
    if target_date and (q_words & (recency_words | oldest_words)):
        direction = 'DESC' if (q_words & recency_words) else 'ASC'
        show = [c[0] for c in cols if c[0] != target_date and c[0] in cat_cols][:3]
        sel = ", ".join(f'"{c}"' for c in show + [target_date])
        return f'SELECT {sel} FROM "{table_name}" ORDER BY "{target_date}" {direction} LIMIT 1'

    # Specific date filter in question (e.g. "on 12/02/2026", "2026-02-12")
    date_pat = re.search(r"\b(\d{1,4})[/-](\d{1,2})[/-](\d{2,4})\b", question)
    if date_pat and target_date:
        p1, p2, p3 = date_pat.group(1), date_pat.group(2), date_pat.group(3)
        if len(p1) == 4:
            parsed_iso = f"{p1}-{int(p2):02d}-{int(p3):02d}"
        else:
            y = p3 if len(p3) == 4 else f"20{p3}"
            parsed_iso = f"{y}-{int(p2):02d}-{int(p1):02d}"
        sel_cols = ", ".join(f'"{c[0]}"' for c in cols[:6])
        return f'SELECT {sel_cols} FROM "{table_name}" WHERE "{target_date}" = \'{parsed_iso}\' LIMIT 100'

    # Entity/Filter detection (e.g. "what are the products ordered in North region?", "what did nina nina buy?")
    if conn:
        active_filters = []
        filter_cols = set()
        for c in cat_cols:
            try:
                distinct_vals = conn.execute(f'SELECT DISTINCT "{c}" FROM "{table_name}" WHERE "{c}" IS NOT NULL LIMIT 100').fetchall()
                for (v,) in distinct_vals:
                    if v and len(str(v).strip()) >= 2:
                        val_str = str(v).strip()
                        if re.search(rf"\b{re.escape(val_str)}\b", question, re.IGNORECASE):
                            clean_v = val_str.replace("'", "''")
                            active_filters.append(f'LOWER("{c}") = \'{clean_v.lower()}\'')
                            filter_cols.add(c)
                            break
            except Exception:
                pass

        if active_filters:
            where_sql = " AND ".join(active_filters)
            target_proj = [c[0] for c in matched_cols if c[0] not in filter_cols]
            if not target_proj:
                target_proj = [c[0] for c in cols if c[0] not in filter_cols][:4]
            if not target_proj:
                target_proj = [c[0] for c in cols[:4]]
            sel = ", ".join(f'"{c}"' for c in target_proj)
            return f'SELECT {sel} FROM "{table_name}" WHERE {where_sql} LIMIT 100'

    # Analytical intent detection (Phase 4)
    if any(k in q_lower for k in ['forecast', 'predict', 'projection', 'future trend', 'next month', 'future sales']):
        if target_date and target_num:
            return f'SELECT "{target_date}", SUM("{target_num}") AS total_{target_num} FROM "{table_name}" GROUP BY "{target_date}" ORDER BY "{target_date}" ASC LIMIT 100'
        elif target_date:
            return f'SELECT "{target_date}", COUNT(*) AS total_count FROM "{table_name}" GROUP BY "{target_date}" ORDER BY "{target_date}" ASC LIMIT 100'

    if any(k in q_lower for k in ['correlation', 'correlate', 'relationship between', 'covariance']):
        num_cols = [c[0] for c in cols if any(t in c[1].lower() for t in ['int', 'double', 'float', 'decimal', 'numeric', 'hugeint'])]
        if len(num_cols) >= 2:
            sel_cols = ", ".join(f'"{c}"' for c in num_cols[:6])
            return f'SELECT {sel_cols} FROM "{table_name}" LIMIT 200'

    if any(k in q_lower for k in ['outlier', 'anomaly', 'anomalies', 'abnormal', 'extreme value']):
        if target_num:
            id_cols = [c[0] for c in cols if c[0] != target_num][:2]
            sel_cols = ", ".join([f'"{c}"' for c in id_cols] + [f'"{target_num}"']) if id_cols else f'*'
            return f'SELECT {sel_cols} FROM "{table_name}" ORDER BY "{target_num}" DESC LIMIT 200'

    # Intent detection
    if any(k in q_lower for k in ['top', 'highest', 'best', 'most', 'max', 'largest']):
        if target_cat and target_num:
            return f'SELECT "{target_cat}", SUM("{target_num}") AS total_{target_num} FROM "{table_name}" GROUP BY "{target_cat}" ORDER BY total_{target_num} DESC LIMIT 10'
        elif target_num:
            sel_cols = ", ".join(f'"{c[0]}"' for c in cols[:4])
            return f'SELECT {sel_cols} FROM "{table_name}" ORDER BY "{target_num}" DESC LIMIT 10'
        elif target_cat:
            return f'SELECT "{target_cat}", COUNT(*) AS count FROM "{table_name}" GROUP BY "{target_cat}" ORDER BY count DESC LIMIT 10'

    if any(k in q_lower for k in ['lowest', 'least', 'worst', 'min', 'smallest']):
        if target_cat and target_num:
            return f'SELECT "{target_cat}", SUM("{target_num}") AS total_{target_num} FROM "{table_name}" GROUP BY "{target_cat}" ORDER BY total_{target_num} ASC LIMIT 10'
        elif target_num:
            sel_cols = ", ".join(f'"{c[0]}"' for c in cols[:4])
            return f'SELECT {sel_cols} FROM "{table_name}" ORDER BY "{target_num}" ASC LIMIT 10'

    if any(k in q_lower for k in ['average', 'avg', 'mean']):
        if target_cat and target_num:
            return f'SELECT "{target_cat}", ROUND(AVG("{target_num}"), 2) AS avg_{target_num} FROM "{table_name}" GROUP BY "{target_cat}" ORDER BY avg_{target_num} DESC LIMIT 10'
        elif target_num:
            return f'SELECT ROUND(AVG("{target_num}"), 2) AS average_{target_num} FROM "{table_name}"'

    if any(k in q_lower for k in ['count', 'how many', 'total number']):
        if target_cat:
            return f'SELECT "{target_cat}", COUNT(*) AS total_count FROM "{table_name}" GROUP BY "{target_cat}" ORDER BY total_count DESC LIMIT 10'
        return f'SELECT COUNT(*) AS total_count FROM "{table_name}"'

    if any(k in q_lower for k in ['sum', 'total', 'revenue', 'sales', 'amount']):
        if target_cat and target_num:
            return f'SELECT "{target_cat}", SUM("{target_num}") AS total_{target_num} FROM "{table_name}" GROUP BY "{target_cat}" ORDER BY total_{target_num} DESC LIMIT 10'
        elif target_num:
            return f'SELECT SUM("{target_num}") AS total_{target_num} FROM "{table_name}"'

    if any(k in q_lower for k in ['trend', 'over time', 'daily', 'monthly', 'date']):
        if target_date and target_num:
            return f'SELECT "{target_date}", SUM("{target_num}") AS total_{target_num} FROM "{table_name}" GROUP BY "{target_date}" ORDER BY "{target_date}" ASC LIMIT 30'
        elif target_date:
            return f'SELECT "{target_date}", COUNT(*) AS total_count FROM "{table_name}" GROUP BY "{target_date}" ORDER BY "{target_date}" ASC LIMIT 30'

    # Default group by or structured projection
    if target_cat and target_num:
        return f'SELECT "{target_cat}", SUM("{target_num}") AS total_{target_num} FROM "{table_name}" GROUP BY "{target_cat}" ORDER BY total_{target_num} DESC LIMIT 10'
    
    sel_cols = ", ".join(f'"{c[0]}"' for c in cols[:5])
    return f'SELECT {sel_cols} FROM "{table_name}" LIMIT 50'



def _swap_day_month_literals(sql: str) -> str:
    """Swaps month/day in 'YYYY-MM-DD' literals when both parts are <= 12 (and differ)."""
    def _swap(m):
        y, mo, d = m.group(1), m.group(2), m.group(3)
        if int(mo) <= 12 and int(d) <= 12 and mo != d:
            return f"'{y}-{d}-{mo}'"
        return m.group(0)
    return re.sub(r"'(\d{4})-(\d{2})-(\d{2})'", _swap, sql)


def generate_and_run_sql(
    question: str,
    schema_str: str,
    conn: duckdb.DuckDBPyConnection,
    max_retries: int = 3,
    plan: dict = None
) -> tuple[str, pd.DataFrame, int, str]:
    """
    Generates SQL from user question using LLM or smart fallback, runs guardrails,
    executes on DuckDB, and self-corrects if execution fails.
    
    Returns (generated_sql, result_df, retries_taken, error_msg)
    """
    # Build a full multi-table schema block so the LLM sees every table + every column
    all_tables_block = []
    for line in schema_str.splitlines():
        all_tables_block.append(line)
    full_schema = "\n".join(all_tables_block)

    system_instruction = (
        "You are an expert DuckDB SQL analyst. Your ONLY job is to write a single, correct, executable DuckDB SQL query.\n"
        "STRICT RULES — violating any rule makes the answer wrong:\n"
        "1. Use ONLY table names and column names that exist in the provided schema. Never invent column or table names.\n"
        "2. NEVER write 'SELECT *' unless the user explicitly asks for raw row samples.\n"
        "3. NEVER output 'SELECT 1' or any placeholder query.\n"
        "4. For multi-table schemas, pick the correct table(s) based on which columns the question references.\n"
        "5. Always select meaningful columns that directly answer the question (SUM, COUNT, DISTINCT, etc.).\n"
        "6. Wrap column and table names that contain spaces or special characters in double quotes.\n"
        "7. Dates written with slashes (e.g. 12/02/2026) are DD/MM/YYYY (12 February 2026). Convert them to ISO 'YYYY-MM-DD' (2026-02-12).\n"
        "8. Output ONLY the SQL inside a ```sql ... ``` block. No explanations."
    )
    
    plan_context = ""
    if plan:
        plan_context = (
            f"\nAnalysis Strategy:\n"
            f"- Goal: {plan.get('intent')}\n"
            f"- Key Metrics to compute: {', '.join(plan.get('metrics', []))}\n"
            f"- Dimensions to group by: {', '.join(plan.get('dimensions', []))}\n"
            f"- Operations: {', '.join(plan.get('operations', []))}\n"
        )

    prompt = (
        f"Database Schema (use ONLY these exact table/column names):\n{full_schema}\n"
        f"{plan_context}\n"
        f"User Question: {question}\n\n"
        f"Write the DuckDB SQL query:"
    )
    
    last_error = ""
    current_prompt = prompt
    retries = 0

    while retries <= max_retries:
        try:
            try:
                raw_sql = call_llm(current_prompt, system_instruction, timeout=SQL_LLM_TIMEOUT)
            except Exception as llm_err:
                # LLM unreachable/too slow: retrying the same call won't help -> go to smart fallback
                last_error = f"LLM unavailable: {llm_err}"
                break
            
            # Clean markdown formatting
            cleaned_sql = raw_sql.strip()
            match = re.search(r"```(?:sql)?\s*(.*?)\s*```", cleaned_sql, re.DOTALL | re.IGNORECASE)
            if match:
                cleaned_sql = match.group(1).strip()
            elif cleaned_sql.startswith("```"):
                cleaned_sql = re.sub(r"^```[a-zA-Z]*\n?", "", cleaned_sql)
                cleaned_sql = re.sub(r"\n?```$", "", cleaned_sql).strip()
            
            # Fix data_table placeholder if present
            table_match = re.search(r"Table:\s*([a-zA-Z0-9_]+)", schema_str)
            if table_match:
                first_table = table_match.group(1)
                cleaned_sql = re.sub(r"\bdata_table\b", first_table, cleaned_sql)

            # Validate guardrails
            is_valid, guard_err = validate_sql_guardrails(cleaned_sql)
            if not is_valid:
                raise ValueError(f"Guardrail violation: {guard_err}")
                
            final_sql = enforce_limit(cleaned_sql)
            
            # Execute SQL
            result_df = conn.execute(final_sql).fetchdf()
            if result_df.empty:
                swapped_sql = _swap_day_month_literals(final_sql)
                if swapped_sql != final_sql:
                    swapped_df = conn.execute(swapped_sql).fetchdf()
                    if not swapped_df.empty:
                        return swapped_sql, swapped_df, retries, ""
            return final_sql, result_df, retries, ""
            
        except Exception as e:
            last_error = str(e)
            retries += 1
            if retries <= max_retries:
                current_prompt = (
                    f"Schema:\n{schema_str}\n\n"
                    f"User Question:\n{question}\n\n"
                    f"The previous SQL query failed with error:\n{last_error}\n\n"
                    f"Please fix the query and return ONLY corrected SQL:"
                )

    # Fallback to Smart Heuristic Query Generator if LLM fails or is unavailable
    try:
        fallback_sql = build_smart_fallback_sql(question, schema_str, conn=conn)
        is_valid, guard_err = validate_sql_guardrails(fallback_sql)
        if is_valid:
            final_sql = enforce_limit(fallback_sql)
            result_df = conn.execute(final_sql).fetchdf()
            if result_df.empty:
                swapped_sql = _swap_day_month_literals(final_sql)
                if swapped_sql != final_sql:
                    swapped_df = conn.execute(swapped_sql).fetchdf()
                    if not swapped_df.empty:
                        return swapped_sql, swapped_df, retries, ""
            return final_sql, result_df, retries, ""
    except Exception as fb_err:
        last_error += f" | Fallback error: {fb_err}"

    return "", pd.DataFrame(), retries, f"Failed after retries. Last error: {last_error}"

