"""
core/database.py — SQLite history + settings persistence
"""

import sqlite3
import json
from pathlib import Path
from datetime import datetime

APP_DIR = Path.home() / ".ytvault"
DB_PATH = APP_DIR / "vault.db"
THUMB_DIR = APP_DIR / "thumbnails"


def init():
    APP_DIR.mkdir(exist_ok=True)
    THUMB_DIR.mkdir(exist_ok=True)
    con = _con()
    con.executescript("""
        CREATE TABLE IF NOT EXISTS downloads (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            title       TEXT    NOT NULL,
            url         TEXT    NOT NULL,
            quality     TEXT,
            fmt         TEXT,
            duration    TEXT,
            filesize    TEXT,
            saved_path  TEXT,
            thumb_path  TEXT,
            channel     TEXT,
            downloaded_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS settings (
            key   TEXT PRIMARY KEY,
            value TEXT
        );
    """)
    con.commit()
    # Defaults
    defaults = {
        "download_dir": str(Path.home() / "Downloads"),
        "theme":        "dark",
        "accent":       "#e63946",
        "concurrent":   "1",
        "auto_thumb":   "1",
    }
    for k, v in defaults.items():
        con.execute("INSERT OR IGNORE INTO settings (key,value) VALUES (?,?)", (k, v))
    con.commit()


def _con():
    return sqlite3.connect(DB_PATH)


# ── Settings ──────────────────────────────────────────────────────────────────

def get_setting(key, fallback=None):
    row = _con().execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
    return row[0] if row else fallback


def set_setting(key, value):
    con = _con()
    con.execute("INSERT OR REPLACE INTO settings (key,value) VALUES (?,?)", (key, str(value)))
    con.commit()


def all_settings():
    rows = _con().execute("SELECT key,value FROM settings").fetchall()
    return dict(rows)


# ── Downloads history ─────────────────────────────────────────────────────────

def add_download(title, url, quality, fmt, duration, filesize, saved_path, thumb_path, channel):
    con = _con()
    con.execute("""
        INSERT INTO downloads
        (title,url,quality,fmt,duration,filesize,saved_path,thumb_path,channel)
        VALUES (?,?,?,?,?,?,?,?,?)
    """, (title, url, quality, fmt, duration, filesize, saved_path, thumb_path, channel))
    con.commit()


def get_history(limit=200):
    rows = _con().execute("""
        SELECT id,title,url,quality,fmt,duration,filesize,saved_path,thumb_path,channel,downloaded_at
        FROM downloads ORDER BY downloaded_at DESC LIMIT ?
    """, (limit,)).fetchall()
    keys = ["id","title","url","quality","fmt","duration","filesize","saved_path","thumb_path","channel","downloaded_at"]
    return [dict(zip(keys, r)) for r in rows]


def delete_download(row_id):
    _con().execute("DELETE FROM downloads WHERE id=?", (row_id,))
    _con().commit()


def clear_history():
    _con().execute("DELETE FROM downloads")
    _con().commit()


def search_history(q):
    rows = _con().execute("""
        SELECT id,title,url,quality,fmt,duration,filesize,saved_path,thumb_path,channel,downloaded_at
        FROM downloads WHERE title LIKE ? OR channel LIKE ?
        ORDER BY downloaded_at DESC LIMIT 100
    """, (f"%{q}%", f"%{q}%")).fetchall()
    keys = ["id","title","url","quality","fmt","duration","filesize","saved_path","thumb_path","channel","downloaded_at"]
    return [dict(zip(keys, r)) for r in rows]