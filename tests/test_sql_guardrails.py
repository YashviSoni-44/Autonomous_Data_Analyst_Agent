"""
Unit tests for SQL guardrails validation.
"""
import pytest
from backend.agent.tools_sql import validate_sql_guardrails, enforce_limit

def test_guardrails_allow_valid_select():
    sql = "SELECT category, SUM(sales_amount) FROM sales GROUP BY category;"
    is_valid, msg = validate_sql_guardrails(sql)
    assert is_valid is True
    assert msg == ""

def test_guardrails_allow_with_clause():
    sql = "WITH top_sales AS (SELECT * FROM sales) SELECT * FROM top_sales;"
    is_valid, msg = validate_sql_guardrails(sql)
    assert is_valid is True
    assert msg == ""

def test_guardrails_reject_drop_table():
    sql = "DROP TABLE sales;"
    is_valid, msg = validate_sql_guardrails(sql)
    assert is_valid is False
    assert "Forbidden keyword" in msg

def test_guardrails_reject_delete():
    sql = "DELETE FROM sales WHERE sales_amount < 10;"
    is_valid, msg = validate_sql_guardrails(sql)
    assert is_valid is False

def test_guardrails_reject_insert():
    sql = "INSERT INTO sales VALUES (1, 'test');"
    is_valid, msg = validate_sql_guardrails(sql)
    assert is_valid is False

def test_enforce_limit_adds_limit():
    sql = "SELECT * FROM sales"
    limited = enforce_limit(sql, max_limit=100)
    assert "LIMIT 100" in limited

def test_enforce_limit_preserves_existing():
    sql = "SELECT * FROM sales LIMIT 20"
    limited = enforce_limit(sql, max_limit=100)
    assert "LIMIT 20" in limited

def test_guardrails_reject_multi_statement_injection():
    sql = "SELECT * FROM sales; DROP TABLE sales;"
    is_valid, msg = validate_sql_guardrails(sql)
    assert is_valid is False
    assert "Forbidden" in msg or "Multiple" in msg

def test_guardrails_reject_alter_table():
    sql = "ALTER TABLE sales ADD COLUMN hack TEXT;"
    is_valid, msg = validate_sql_guardrails(sql)
    assert is_valid is False

def test_guardrails_reject_create_table():
    sql = "CREATE TABLE malicious (id INT);"
    is_valid, msg = validate_sql_guardrails(sql)
    assert is_valid is False

