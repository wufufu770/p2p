#!/usr/bin/env python3
"""graphd - Kuzu 单写者 sidecar。三环+插件全部经 HTTP 读写图,规避多进程锁。
stdlib only (kuzu 除外). GET /health POST /query POST /reset
"""
import json
import os
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

DB_PATH = os.environ.get("P2P_GRAPH", "/home/wff/p2p/graphd/kuzu_db")
PORT = int(os.environ.get("P2P_GRAPH_PORT", "8765"))

import kuzu

_lock = threading.Lock()
_db = None


def db():
    global _db
    if _db is None:
        parent = os.path.dirname(DB_PATH)
        if parent:
            os.makedirs(parent, exist_ok=True)
        _db = kuzu.Database(DB_PATH)
        conn = kuzu.Connection(_db)
        init_schema(conn)
    return _db


SCHEMA = [
    "CREATE NODE TABLE IF NOT EXISTS Engagement(name STRING, target STRING, scope STRING, auth STRING, status STRING, created_at STRING, PRIMARY KEY(name))",
    "CREATE NODE TABLE IF NOT EXISTS Endpoint(id STRING, url STRING, param STRING, method STRING, tech STRING, business_chain STRING, coverage_votes INT64 DEFAULT 0, exhausted BOOL DEFAULT false, PRIMARY KEY(id))",
    "CREATE NODE TABLE IF NOT EXISTS Signal_(id STRING, type STRING, weight DOUBLE DEFAULT 1.0, status STRING DEFAULT 'open', evidence STRING, ts STRING, ring STRING, PRIMARY KEY(id))",
    "CREATE NODE TABLE IF NOT EXISTS Hypothesis(id STRING, text STRING, strategy STRING, status STRING DEFAULT 'open', ts STRING, PRIMARY KEY(id))",
    "CREATE NODE TABLE IF NOT EXISTS Finding(id STRING, title STRING, severity STRING, cvss DOUBLE DEFAULT 0.0, evidence_dir STRING, repro STRING, category STRING DEFAULT 'vuln', gate_status STRING DEFAULT 'candidate', ts STRING, PRIMARY KEY(id))",
    "CREATE NODE TABLE IF NOT EXISTS ExperienceWeight(id STRING, pattern STRING, stack STRING, prior DOUBLE DEFAULT 1.0, hits INT64 DEFAULT 0, wins INT64 DEFAULT 0, target_type STRING DEFAULT 'web', PRIMARY KEY(id))",
    "CREATE NODE TABLE IF NOT EXISTS AgentIdentity(worker_id STRING, ring STRING, chain STRING, status STRING, checkpoint STRING, todo STRING, updated_at STRING, PRIMARY KEY(worker_id))",
    "CREATE REL TABLE IF NOT EXISTS AT(FROM Signal_ TO Endpoint)",
    "CREATE REL TABLE IF NOT EXISTS CONFIRMS(FROM Finding TO Signal_)",
    "CREATE REL TABLE IF NOT EXISTS SUGGESTS(FROM Hypothesis TO Endpoint)",
    "CREATE REL TABLE IF NOT EXISTS DERIVED_FROM(FROM Signal_ TO Signal_)",
    "CREATE REL TABLE IF NOT EXISTS PRIOR_FOR(FROM ExperienceWeight TO Signal_)",
]


def init_schema(conn):
    for q in SCHEMA:
        try:
            conn.execute(q)
        except Exception as e:
            if "already exists" not in str(e):
                raise


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _send(self, code, obj):
        body = json.dumps(obj, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/health":
            self._send(200, {"ok": True, "db": DB_PATH})
        else:
            self._send(404, {"error": "unknown"})

    def do_POST(self):
        n = int(self.headers.get("Content-Length", 0))
        req = json.loads(self.rfile.read(n) or b"{}")
        if self.path == "/query":
            cypher = req.get("cypher", "").strip()
            params = req.get("params") or {}
            if not cypher:
                return self._send(400, {"error": "empty cypher"})
            with _lock:
                try:
                    conn = kuzu.Connection(db())
                    res = conn.execute(cypher, params)
                    rows = []
                    while res.has_next():
                        rows.append(res.get_next())
                    cols = res.get_column_names()
                    data = []
                    for r in rows:
                        data.append({cols[i]: _jsonify(r[i]) for i in range(len(cols))})
                    return self._send(200, {"ok": True, "rows": data})
                except Exception as e:
                    return self._send(400, {"ok": False, "error": str(e)})
        elif self.path == "/reset":
            global _db
            with _lock:
                _db = None
                import shutil
                shutil.rmtree(DB_PATH, ignore_errors=True)
            return self._send(200, {"ok": True})
        else:
            self._send(404, {"error": "unknown"})


def _jsonify(v):
    if isinstance(v, (int, float, str, bool)) or v is None:
        return v
    return str(v)


if __name__ == "__main__":
    db()  # 初始化 schema
    srv = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    print(f"[graphd] listening :{PORT} db={DB_PATH}", flush=True)
    srv.serve_forever()
