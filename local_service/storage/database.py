import hashlib
import json
import sqlite3
import threading
import time
from pathlib import Path

PIPELINE = "novel-local-1"
# Provisional safety cap, to be calibrated with measured production workloads.
CACHE_BYTES = 128 * 1024 * 1024


def cache_key(text, model, device, glossary):
    payload = [PIPELINE, text, model.public(), device, glossary]
    return hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


class Database:
    def __init__(self, path: Path, cap=CACHE_BYTES):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.lock = threading.RLock()
        self.cap = cap
        self.db = sqlite3.connect(path, check_same_thread=False)
        self.db.execute("PRAGMA journal_mode=WAL")
        version = self.db.execute("PRAGMA user_version").fetchone()[0]
        if version > 1:
            raise RuntimeError("Dữ liệu thuộc phiên bản chương trình mới hơn.")
        self.db.executescript("""
            CREATE TABLE IF NOT EXISTS glossary(id TEXT PRIMARY KEY, body TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS cache(key TEXT PRIMARY KEY, body TEXT NOT NULL,
                bytes INTEGER NOT NULL, used REAL NOT NULL);
            CREATE INDEX IF NOT EXISTS cache_used ON cache(used);
            PRAGMA user_version=1;
        """)

    def glossaries(self):
        with self.lock:
            return [json.loads(row[0]) for row in self.db.execute("SELECT body FROM glossary ORDER BY id")]

    def save_glossary(self, body):
        with self.lock, self.db:
            self.db.execute("INSERT OR REPLACE INTO glossary VALUES (?,?)",
                            (body["id"], json.dumps(body, ensure_ascii=False)))

    def delete_glossary(self, id):
        with self.lock, self.db:
            self.db.execute("DELETE FROM glossary WHERE id=?", (id,))

    def get(self, key):
        with self.lock, self.db:
            row = self.db.execute("SELECT body FROM cache WHERE key=?", (key,)).fetchone()
            if row:
                self.db.execute("UPDATE cache SET used=? WHERE key=?", (time.time(), key))
                return json.loads(row[0])

    def put(self, key, value):
        body = json.dumps(value, ensure_ascii=False)
        with self.lock, self.db:
            self.db.execute("INSERT OR REPLACE INTO cache VALUES (?,?,?,?)",
                            (key, body, len(body.encode()) + len(key), time.time()))
            total = self.db.execute("SELECT COALESCE(SUM(bytes),0) FROM cache").fetchone()[0]
            while total > self.cap:
                row = self.db.execute("SELECT key,bytes FROM cache ORDER BY used LIMIT 1").fetchone()
                self.db.execute("DELETE FROM cache WHERE key=?", (row[0],))
                total -= row[1]

    def clear_cache(self):
        with self.lock, self.db:
            self.db.execute("DELETE FROM cache")
        # Reclaim disk pages, not just logical entries.
        with self.lock:
            self.db.execute("PRAGMA wal_checkpoint(TRUNCATE)")
            self.db.execute("VACUUM")

    def close(self):
        with self.lock:
            self.db.close()
