"""
SQLite logging database to track agent runs, latency, retries, and success rates.
"""
import sqlite3
import os
import json
from datetime import datetime

LOG_DB_PATH = os.getenv("LOG_DB_PATH", "./agent_runs.db")

def init_db():
    conn = sqlite3.connect(LOG_DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS agent_runs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT,
        dataset_id TEXT,
        question TEXT,
        sql TEXT,
        latency_seconds REAL,
        retries INTEGER,
        success INTEGER,
        error TEXT
    )
    """)
    conn.commit()
    conn.close()

def log_run(dataset_id: str, question: str, sql: str, latency: float, retries: int, success: bool, error: str = None):
    init_db()
    conn = sqlite3.connect(LOG_DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO agent_runs (timestamp, dataset_id, question, sql, latency_seconds, retries, success, error)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        datetime.utcnow().isoformat(),
        dataset_id,
        question,
        sql or "",
        latency,
        retries,
        1 if success else 0,
        error or ""
    ))
    conn.commit()
    conn.close()

def get_stats():
    init_db()
    conn = sqlite3.connect(LOG_DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM agent_runs")
    total_runs = cursor.fetchone()[0] or 0
    
    if total_runs == 0:
        conn.close()
        return {
            "total_runs": 0,
            "successful_runs": 0,
            "failed_runs": 0,
            "success_rate": 0.0,
            "avg_latency_seconds": 0.0,
            "avg_retries": 0.0,
            "recent_failures": []
        }
        
    cursor.execute("SELECT COUNT(*) FROM agent_runs WHERE success = 1")
    successful_runs = cursor.fetchone()[0] or 0
    
    failed_runs = total_runs - successful_runs
    success_rate = round((successful_runs / total_runs) * 100, 2)
    
    cursor.execute("SELECT AVG(latency_seconds) FROM agent_runs")
    avg_latency = round(cursor.fetchone()[0] or 0.0, 2)
    
    cursor.execute("SELECT AVG(retries) FROM agent_runs")
    avg_retries = round(cursor.fetchone()[0] or 0.0, 2)
    
    cursor.execute("SELECT id, timestamp, question, sql, error FROM agent_runs WHERE success = 0 ORDER BY id DESC LIMIT 10")
    failures_rows = cursor.fetchall()
    recent_failures = [
        {"id": row[0], "timestamp": row[1], "question": row[2], "sql": row[3], "error": row[4]}
        for row in failures_rows
    ]
    
    conn.close()
    return {
        "total_runs": total_runs,
        "successful_runs": successful_runs,
        "failed_runs": failed_runs,
        "success_rate": success_rate,
        "avg_latency_seconds": avg_latency,
        "avg_retries": avg_retries,
        "recent_failures": recent_failures
    }
