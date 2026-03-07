#!/usr/bin/env python3
"""
Persistent Memory Store - Self-contained SQLite + GitHub backup.
Pipeline brain: every module reads/writes state here. On startup loads from local SQLite.
On demand serializes to JSON and pushes to GitHub as backup.
"""

import sqlite3
import json
import os
import base64
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

try:
    import httpx
except ImportError:
    httpx = None

DB_FILENAME = "pipeline_memory.db"
BACKUP_FILENAME = "memory_backup.json"
GITHUB_REPO = "uerzer/adult-pipeline"
GITHUB_BACKUP_PATH = "data/memory_backup.json"


class MemoryStore:
    def __init__(self, db_path=None):
        self.db_path = db_path or os.path.join(os.path.dirname(os.path.abspath(__file__)), DB_FILENAME)
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA foreign_keys=ON")
        self._init_tables()

    def _init_tables(self):
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS config (
                key TEXT PRIMARY KEY, value TEXT NOT NULL,
                encrypted INTEGER DEFAULT 0, updated_at TEXT DEFAULT (datetime('now'))
            );
            CREATE TABLE IF NOT EXISTS accounts (
                id INTEGER PRIMARY KEY AUTOINCREMENT, platform TEXT NOT NULL,
                username TEXT NOT NULL, status TEXT DEFAULT 'active', cookies TEXT,
                metadata TEXT DEFAULT '{}', created_at TEXT DEFAULT (datetime('now')),
                updated_at TEXT DEFAULT (datetime('now')), UNIQUE(platform, username)
            );
            CREATE TABLE IF NOT EXISTS content (
                id INTEGER PRIMARY KEY AUTOINCREMENT, content_type TEXT NOT NULL,
                body TEXT NOT NULL, metadata TEXT DEFAULT '{}',
                used INTEGER DEFAULT 0, created_at TEXT DEFAULT (datetime('now'))
            );
            CREATE TABLE IF NOT EXISTS posts (
                id INTEGER PRIMARY KEY AUTOINCREMENT, platform TEXT NOT NULL,
                target TEXT NOT NULL, url TEXT, post_type TEXT DEFAULT 'image',
                content_id INTEGER REFERENCES content(id), status TEXT DEFAULT 'posted',
                upvotes INTEGER DEFAULT 0, comments INTEGER DEFAULT 0, clicks INTEGER DEFAULT 0,
                metadata TEXT DEFAULT '{}', posted_at TEXT DEFAULT (datetime('now')), checked_at TEXT
            );
            CREATE TABLE IF NOT EXISTS schedule (
                id INTEGER PRIMARY KEY AUTOINCREMENT, action TEXT NOT NULL,
                target TEXT NOT NULL, scheduled_for TEXT NOT NULL,
                payload TEXT DEFAULT '{}', status TEXT DEFAULT 'pending',
                created_at TEXT DEFAULT (datetime('now')), executed_at TEXT
            );
            CREATE TABLE IF NOT EXISTS metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT NOT NULL,
                platform TEXT NOT NULL, metric_type TEXT NOT NULL,
                value REAL NOT NULL, metadata TEXT DEFAULT '{}',
                UNIQUE(date, platform, metric_type)
            );
            CREATE TABLE IF NOT EXISTS memory (
                id INTEGER PRIMARY KEY AUTOINCREMENT, category TEXT DEFAULT 'general',
                content TEXT NOT NULL, source TEXT, confidence REAL DEFAULT 1.0,
                created_at TEXT DEFAULT (datetime('now')), expires_at TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_posts_platform ON posts(platform);
            CREATE INDEX IF NOT EXISTS idx_posts_posted_at ON posts(posted_at);
            CREATE INDEX IF NOT EXISTS idx_content_type ON content(content_type);
            CREATE INDEX IF NOT EXISTS idx_schedule_status ON schedule(status);
            CREATE INDEX IF NOT EXISTS idx_memory_category ON memory(category);
            CREATE INDEX IF NOT EXISTS idx_metrics_date ON metrics(date);
        """)
        self.conn.commit()

    # -- Config --------------------------------------------------------
    def set_config(self, key, value, encrypt=False):
        stored = base64.b64encode(value.encode()).decode() if encrypt else value
        self.conn.execute(
            "INSERT INTO config (key,value,encrypted,updated_at) VALUES (?,?,?,datetime('now')) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value,encrypted=excluded.encrypted,updated_at=datetime('now')",
            (key, stored, 1 if encrypt else 0))
        self.conn.commit()

    def get_config(self, key, default=None):
        row = self.conn.execute("SELECT value,encrypted FROM config WHERE key=?", (key,)).fetchone()
        if not row: return default
        return base64.b64decode(row["value"].encode()).decode() if row["encrypted"] else row["value"]

    def get_all_config(self):
        rows = self.conn.execute("SELECT key,value,encrypted FROM config").fetchall()
        return {r["key"]: (base64.b64decode(r["value"].encode()).decode() if r["encrypted"] else r["value"]) for r in rows}

    # -- Accounts ------------------------------------------------------
    def upsert_account(self, platform, username, **kw):
        self.conn.execute(
            "INSERT INTO accounts (platform,username,status,cookies,metadata,updated_at) VALUES (?,?,?,?,?,datetime('now')) "
            "ON CONFLICT(platform,username) DO UPDATE SET status=excluded.status,"
            "cookies=CASE WHEN excluded.cookies!='' THEN excluded.cookies ELSE accounts.cookies END,"
            "metadata=excluded.metadata,updated_at=datetime('now')",
            (platform, username, kw.get("status","active"), kw.get("cookies",""), json.dumps(kw.get("metadata",{}))))
        self.conn.commit()

    def get_account(self, platform, username=None):
        if username:
            row = self.conn.execute("SELECT * FROM accounts WHERE platform=? AND username=?", (platform,username)).fetchone()
        else:
            row = self.conn.execute("SELECT * FROM accounts WHERE platform=? AND status='active' ORDER BY updated_at DESC LIMIT 1", (platform,)).fetchone()
        return dict(row) if row else None

    def get_accounts(self, platform=None):
        rows = self.conn.execute("SELECT * FROM accounts" + (" WHERE platform=?" if platform else ""), (platform,) if platform else ()).fetchall()
        return [dict(r) for r in rows]

    # -- Content -------------------------------------------------------
    def log_content(self, content_type, body, metadata=None):
        cur = self.conn.execute("INSERT INTO content (content_type,body,metadata) VALUES (?,?,?)",
            (content_type, body, json.dumps(metadata or {})))
        self.conn.commit()
        return cur.lastrowid

    def get_unused_content(self, content_type=None, limit=10):
        if content_type:
            rows = self.conn.execute("SELECT * FROM content WHERE used=0 AND content_type=? ORDER BY created_at DESC LIMIT ?", (content_type,limit)).fetchall()
        else:
            rows = self.conn.execute("SELECT * FROM content WHERE used=0 ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()
        return [dict(r) for r in rows]

    def mark_content_used(self, content_id):
        self.conn.execute("UPDATE content SET used=1 WHERE id=?", (content_id,))
        self.conn.commit()

    # -- Posts ---------------------------------------------------------
    def log_post(self, platform, target, post_type="image", url=None, content_id=None, metadata=None):
        cur = self.conn.execute("INSERT INTO posts (platform,target,post_type,url,content_id,metadata) VALUES (?,?,?,?,?,?)",
            (platform, target, post_type, url, content_id, json.dumps(metadata or {})))
        self.conn.commit()
        return cur.lastrowid

    def update_post_metrics(self, post_id, upvotes=0, comments=0, clicks=0):
        self.conn.execute("UPDATE posts SET upvotes=?,comments=?,clicks=?,checked_at=datetime('now') WHERE id=?",
            (upvotes, comments, clicks, post_id))
        self.conn.commit()

    def get_posts(self, platform=None, limit=50, days=None):
        q, p = "SELECT * FROM posts WHERE 1=1", []
        if platform: q += " AND platform=?"; p.append(platform)
        if days: q += " AND posted_at >= datetime('now', ?)"; p.append(f"-{days} days")
        q += " ORDER BY posted_at DESC LIMIT ?"; p.append(limit)
        return [dict(r) for r in self.conn.execute(q, p).fetchall()]

    def get_post_stats(self, platform=None, days=7):
        q = "SELECT COUNT(*) as total_posts, COALESCE(SUM(upvotes),0) as total_upvotes, COALESCE(SUM(comments),0) as total_comments, COALESCE(SUM(clicks),0) as total_clicks, COALESCE(AVG(upvotes),0) as avg_upvotes, COUNT(DISTINCT target) as unique_targets FROM posts WHERE posted_at >= datetime('now', ?)"
        p = [f"-{days} days"]
        if platform: q += " AND platform=?"; p.append(platform)
        return dict(self.conn.execute(q, p).fetchone())

    def get_best_targets(self, platform, limit=10):
        rows = self.conn.execute("SELECT target, COUNT(*) as posts, AVG(upvotes) as avg_upvotes, SUM(clicks) as total_clicks FROM posts WHERE platform=? GROUP BY target ORDER BY avg_upvotes DESC LIMIT ?", (platform, limit)).fetchall()
        return [dict(r) for r in rows]

    # -- Schedule ------------------------------------------------------
    def add_scheduled(self, action, target, scheduled_for, payload=None):
        cur = self.conn.execute("INSERT INTO schedule (action,target,scheduled_for,payload) VALUES (?,?,?,?)",
            (action, target, scheduled_for, json.dumps(payload or {})))
        self.conn.commit()
        return cur.lastrowid

    def get_due_actions(self):
        return [dict(r) for r in self.conn.execute("SELECT * FROM schedule WHERE status='pending' AND scheduled_for <= datetime('now') ORDER BY scheduled_for ASC").fetchall()]

    def mark_executed(self, schedule_id, status="completed"):
        self.conn.execute("UPDATE schedule SET status=?,executed_at=datetime('now') WHERE id=?", (status, schedule_id))
        self.conn.commit()

    # -- Metrics -------------------------------------------------------
    def log_metric(self, platform, metric_type, value, date=None, metadata=None):
        date = date or datetime.now(timezone.utc).strftime("%Y-%m-%d")
        self.conn.execute("INSERT INTO metrics (date,platform,metric_type,value,metadata) VALUES (?,?,?,?,?) ON CONFLICT(date,platform,metric_type) DO UPDATE SET value=excluded.value,metadata=excluded.metadata",
            (date, platform, metric_type, value, json.dumps(metadata or {})))
        self.conn.commit()

    def get_metrics(self, platform=None, metric_type=None, days=30):
        q, p = "SELECT * FROM metrics WHERE date >= date('now', ?)", [f"-{days} days"]
        if platform: q += " AND platform=?"; p.append(platform)
        if metric_type: q += " AND metric_type=?"; p.append(metric_type)
        q += " ORDER BY date DESC"
        return [dict(r) for r in self.conn.execute(q, p).fetchall()]

    # -- Memory (agent learnings) --------------------------------------
    def add_memory(self, content, category="general", source=None, confidence=1.0, expires_days=None):
        expires = f"+{expires_days} days" if expires_days else None
        cur = self.conn.execute(
            "INSERT INTO memory (category,content,source,confidence,expires_at) VALUES (?,?,?,?,CASE WHEN ? IS NOT NULL THEN datetime('now',?) ELSE NULL END)",
            (category, content, source, confidence, expires, expires))
        self.conn.commit()
        return cur.lastrowid

    def search_memory(self, query=None, category=None, limit=20):
        q, p = "SELECT * FROM memory WHERE (expires_at IS NULL OR expires_at > datetime('now'))", []
        if category: q += " AND category=?"; p.append(category)
        if query: q += " AND content LIKE ?"; p.append(f"%{query}%")
        q += " ORDER BY created_at DESC LIMIT ?"; p.append(limit)
        return [dict(r) for r in self.conn.execute(q, p).fetchall()]

    def forget(self, memory_id=None, category=None, older_than_days=None):
        if memory_id: self.conn.execute("DELETE FROM memory WHERE id=?", (memory_id,))
        elif category and older_than_days: self.conn.execute("DELETE FROM memory WHERE category=? AND created_at < datetime('now', ?)", (category, f"-{older_than_days} days"))
        elif category: self.conn.execute("DELETE FROM memory WHERE category=?", (category,))
        self.conn.commit()

    # -- Export / Import / GitHub Backup --------------------------------
    def export_json(self, filepath=None):
        tables = ["config","accounts","content","posts","schedule","metrics","memory"]
        data = {"_meta": {"exported_at": datetime.now(timezone.utc).isoformat(), "db_path": self.db_path, "version": "1.0"}}
        for t in tables:
            data[t] = [dict(r) for r in self.conn.execute(f"SELECT * FROM {t}").fetchall()]
        if filepath:
            Path(filepath).parent.mkdir(parents=True, exist_ok=True)
            with open(filepath, "w") as f: json.dump(data, f, indent=2, default=str)
        return data

    def import_json(self, filepath=None, data=None):
        if filepath:
            with open(filepath) as f: data = json.load(f)
        if not data: return
        for row in data.get("config", []):
            self.conn.execute("INSERT INTO config (key,value,encrypted,updated_at) VALUES (?,?,?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value,encrypted=excluded.encrypted,updated_at=excluded.updated_at",
                (row["key"], row["value"], row.get("encrypted",0), row.get("updated_at")))
        for row in data.get("accounts", []):
            self.upsert_account(row["platform"], row["username"], status=row.get("status","active"), cookies=row.get("cookies",""), metadata=json.loads(row.get("metadata","{}")))
        for row in data.get("memory", []):
            existing = self.conn.execute("SELECT id FROM memory WHERE content=? AND category=?", (row["content"], row.get("category","general"))).fetchone()
            if not existing:
                self.conn.execute("INSERT INTO memory (category,content,source,confidence,created_at,expires_at) VALUES (?,?,?,?,?,?)",
                    (row.get("category","general"), row["content"], row.get("source"), row.get("confidence",1.0), row.get("created_at"), row.get("expires_at")))
        self.conn.commit()

    def push_to_github(self, token=None, repo=None, path=None):
        if not httpx: return {"error": "httpx not installed"}
        token = token or os.environ.get("GITHUB_TOKEN","")
        repo = repo or os.environ.get("GITHUB_REPO", GITHUB_REPO)
        path = path or GITHUB_BACKUP_PATH
        if not token: return {"error": "No GITHUB_TOKEN set"}
        data = self.export_json()
        content_b64 = base64.b64encode(json.dumps(data, indent=2, default=str).encode()).decode()
        api_url = f"https://api.github.com/repos/{repo}/contents/{path}"
        headers = {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
        resp = httpx.get(api_url, headers=headers)
        sha = resp.json().get("sha") if resp.status_code == 200 else None
        payload = {"message": f"Memory backup {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}", "content": content_b64}
        if sha: payload["sha"] = sha
        resp = httpx.put(api_url, headers=headers, json=payload)
        if resp.status_code in (200,201): return {"success": True, "url": resp.json().get("content",{}).get("html_url")}
        return {"error": f"GitHub API {resp.status_code}: {resp.text[:500]}"}

    def restore_from_github(self, token=None, repo=None, path=None):
        if not httpx: return {"error": "httpx not installed"}
        token = token or os.environ.get("GITHUB_TOKEN","")
        repo = repo or os.environ.get("GITHUB_REPO", GITHUB_REPO)
        path = path or GITHUB_BACKUP_PATH
        if not token: return {"error": "No GITHUB_TOKEN set"}
        api_url = f"https://api.github.com/repos/{repo}/contents/{path}"
        headers = {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"}
        resp = httpx.get(api_url, headers=headers)
        if resp.status_code != 200: return {"error": f"API error {resp.status_code}"}
        data = json.loads(base64.b64decode(resp.json().get("content","")).decode())
        self.import_json(data=data)
        return {"success": True, "records_imported": sum(len(data.get(t,[])) for t in ["config","accounts","memory"])}

    def stats(self):
        counts = {}
        for t in ["config","accounts","content","posts","schedule","metrics","memory"]:
            counts[t] = self.conn.execute(f"SELECT COUNT(*) as c FROM {t}").fetchone()["c"]
        counts["db_size_kb"] = round(os.path.getsize(self.db_path)/1024, 1) if os.path.exists(self.db_path) else 0
        return counts

    def close(self):
        self.conn.close()
    def __enter__(self): return self
    def __exit__(self, *a): self.close()
    def __repr__(self):
        s = self.stats()
        return f"<MemoryStore {s['memory']} memories, {s['posts']} posts, {s['content']} content, {s['accounts']} accounts>"


if __name__ == "__main__":
    import sys
    mem = MemoryStore()
    if len(sys.argv) < 2:
        print(f"Pipeline Memory Store\n  DB: {mem.db_path}\n  Stats: {json.dumps(mem.stats(), indent=2)}")
        print("Commands: stats | export [file] | import <file> | push | pull | config | memory")
        sys.exit(0)
    cmd = sys.argv[1]
    if cmd == "stats": print(json.dumps(mem.stats(), indent=2))
    elif cmd == "export":
        out = sys.argv[2] if len(sys.argv) > 2 else BACKUP_FILENAME
        mem.export_json(out); print(f"Exported to {out}")
    elif cmd == "import":
        mem.import_json(sys.argv[2]); print(f"Imported from {sys.argv[2]}")
    elif cmd == "push": print(json.dumps(mem.push_to_github(), indent=2))
    elif cmd == "pull": print(json.dumps(mem.restore_from_github(), indent=2))
    elif cmd == "config":
        if len(sys.argv) >= 4: mem.set_config(sys.argv[2], sys.argv[3]); print(f"Set {sys.argv[2]}")
        elif len(sys.argv) == 3: print(f"{sys.argv[2]} = {mem.get_config(sys.argv[2])}")
        else:
            for k,v in mem.get_all_config().items(): print(f"  {k} = {v}")
    elif cmd == "memory":
        if len(sys.argv) >= 3 and sys.argv[2] == "add": mid = mem.add_memory(" ".join(sys.argv[3:])); print(f"Added #{mid}")
        elif len(sys.argv) >= 3 and sys.argv[2] == "search":
            for r in mem.search_memory(" ".join(sys.argv[3:])): print(f"  [{r['id']}] ({r['category']}) {r['content']}")
        else:
            for r in mem.search_memory(): print(f"  [{r['id']}] ({r['category']}) {r['content']}")
    mem.close()
