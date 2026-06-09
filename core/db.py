"""
SQLite 岗位数据库
持久化存储、去重、状态管理、截止日期追踪
"""

import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from core import DATA_DIR

DB_PATH = DATA_DIR / "jobs.db"


def _conn():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("""CREATE TABLE IF NOT EXISTS jobs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company TEXT NOT NULL,
        title TEXT NOT NULL,
        department TEXT DEFAULT '',
        location TEXT DEFAULT '',
        url TEXT DEFAULT '',
        source TEXT DEFAULT '',
        first_seen TEXT NOT NULL,
        last_seen TEXT NOT NULL,
        status TEXT DEFAULT '待关注',
        deadline TEXT DEFAULT '',
        match_level TEXT DEFAULT '',
        llm_reason TEXT DEFAULT '',
        notes TEXT DEFAULT '',
        UNIQUE(company, title)
    )""")
    conn.execute("""CREATE TABLE IF NOT EXISTS scrape_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        scraped_at TEXT NOT NULL,
        total_jobs INTEGER,
        new_jobs INTEGER,
        source TEXT DEFAULT 'lite'
    )""")
    conn.execute("""CREATE TABLE IF NOT EXISTS push_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        pushed_at TEXT NOT NULL,
        channel TEXT DEFAULT '',
        title TEXT DEFAULT '',
        content_preview TEXT DEFAULT '',
        success INTEGER DEFAULT 1,
        error TEXT DEFAULT ''
    )""")
    try:
        conn.execute("ALTER TABLE jobs ADD COLUMN deadline TEXT DEFAULT ''")
    except sqlite3.OperationalError:
        pass
    conn.commit()
    return conn


def upsert_jobs(jobs: list) -> dict:
    conn = _conn()
    now = datetime.now().isoformat()
    new_count = 0
    for j in jobs:
        company = j.get("company", "")
        title = j.get("title", "")
        if not company or not title:
            continue
        try:
            conn.execute(
                "INSERT INTO jobs (company,title,department,location,url,source,first_seen,last_seen) VALUES (?,?,?,?,?,?,?,?)",
                (company, title, j.get("department", ""), j.get("location", ""),
                 j.get("url", ""), j.get("source", ""), now, now))
            new_count += 1
        except sqlite3.IntegrityError:
            conn.execute(
                "UPDATE jobs SET last_seen=?, url=CASE WHEN url='' THEN ? ELSE url END, "
                "location=CASE WHEN location='' THEN ? ELSE location END WHERE company=? AND title=?",
                (now, j.get("url", ""), j.get("location", ""), company, title))
    conn.execute("INSERT INTO scrape_log (scraped_at,total_jobs,new_jobs) VALUES (?,?,?)",
                 (now, len(jobs), new_count))
    conn.commit()
    conn.close()
    return {"total": len(jobs), "new": new_count}


def get_all_jobs(status: str = "", company: str = "") -> list:
    conn = _conn()
    q = "SELECT * FROM jobs WHERE 1=1"
    p = []
    if status:
        q += " AND status=?"; p.append(status)
    if company:
        q += " AND company=?"; p.append(company)
    q += " ORDER BY first_seen DESC"
    rows = conn.execute(q, p).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_new_jobs(since: str = "") -> list:
    conn = _conn()
    if not since:
        since = (datetime.now() - timedelta(days=1)).isoformat()
    rows = conn.execute("SELECT * FROM jobs WHERE first_seen > ? ORDER BY first_seen DESC", (since,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def update_job_status(job_id: int, status: str) -> bool:
    conn = _conn()
    conn.execute("UPDATE jobs SET status=? WHERE id=?", (status, job_id))
    conn.commit()
    conn.close()
    return True


def update_job_deadline(job_id: int, deadline: str) -> bool:
    conn = _conn()
    conn.execute("UPDATE jobs SET deadline=? WHERE id=?", (deadline, job_id))
    conn.commit()
    conn.close()
    return True


def update_job_notes(job_id: int, notes: str) -> bool:
    conn = _conn()
    conn.execute("UPDATE jobs SET notes=? WHERE id=?", (notes, job_id))
    conn.commit()
    conn.close()
    return True


def get_expiring_jobs(days: int = 3) -> list:
    """获取 N 天内截止的岗位"""
    conn = _conn()
    now = datetime.now().strftime("%Y-%m-%d")
    future = (datetime.now() + timedelta(days=days)).strftime("%Y-%m-%d")
    rows = conn.execute(
        "SELECT * FROM jobs WHERE deadline != '' AND deadline >= ? AND deadline <= ? AND status NOT IN ('已挂','offer') ORDER BY deadline",
        (now, future)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_stats() -> dict:
    conn = _conn()
    total = conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]
    by_status = {}
    for row in conn.execute("SELECT status, COUNT(*) as cnt FROM jobs GROUP BY status"):
        by_status[row["status"]] = row["cnt"]
    by_company = {}
    for row in conn.execute("SELECT company, COUNT(*) as cnt FROM jobs GROUP BY company ORDER BY cnt DESC"):
        by_company[row["company"]] = row["cnt"]
    # Expiring
    now = datetime.now().strftime("%Y-%m-%d")
    future3 = (datetime.now() + timedelta(days=3)).strftime("%Y-%m-%d")
    expiring = conn.execute(
        "SELECT COUNT(*) FROM jobs WHERE deadline != '' AND deadline >= ? AND deadline <= ?",
        (now, future3)).fetchone()[0]
    history = []
    for row in conn.execute("SELECT scraped_at, total_jobs, new_jobs FROM scrape_log ORDER BY scraped_at DESC LIMIT 30"):
        history.append(dict(row))
    conn.close()
    return {"total": total, "by_status": by_status, "by_company": by_company,
            "expiring": expiring, "history": history}


def get_companies_list() -> list:
    conn = _conn()
    rows = conn.execute("SELECT DISTINCT company FROM jobs ORDER BY company").fetchall()
    conn.close()
    return [r["company"] for r in rows]


def log_push(channel: str, title: str, content_preview: str, success: bool, error: str = ""):
    conn = _conn()
    conn.execute("INSERT INTO push_log (pushed_at,channel,title,content_preview,success,error) VALUES (?,?,?,?,?,?)",
                 (datetime.now().isoformat(), channel, title, content_preview[:200], 1 if success else 0, error))
    conn.commit()
    conn.close()


def get_push_history(limit: int = 20) -> list:
    conn = _conn()
    rows = conn.execute("SELECT * FROM push_log ORDER BY pushed_at DESC LIMIT ?", (limit,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]
