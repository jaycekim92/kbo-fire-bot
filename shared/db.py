import sqlite3
import json
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "firebot.db"
SCHEMA_PATH = Path(__file__).parent.parent / "shared" / "schema.sql"


def get_conn():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    conn = get_conn()
    conn.executescript(SCHEMA_PATH.read_text())
    conn.commit()
    conn.close()


# --- Events (이벤트: 경기결과, 종목시세 등) ---
def insert_event(category, event_date, title, data, image_url=None):
    conn = get_conn()
    cur = conn.execute(
        "INSERT INTO events (category, event_date, title, data, image_url) VALUES (?,?,?,?,?)",
        (category, event_date, title, json.dumps(data, ensure_ascii=False), image_url),
    )
    conn.commit()
    event_id = cur.lastrowid
    conn.close()
    return event_id


def get_events(category, event_date):
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM events WHERE category = ? AND event_date = ? ORDER BY id",
        (category, event_date),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_all_event_dates(category):
    conn = get_conn()
    rows = conn.execute(
        "SELECT DISTINCT event_date FROM events WHERE category = ? ORDER BY event_date DESC",
        (category,),
    ).fetchall()
    conn.close()
    return [r["event_date"] for r in rows]


# --- Context (컨텍스트: 뉴스 등) ---
def insert_context(event_id, content):
    conn = get_conn()
    conn.execute(
        "INSERT INTO contexts (event_id, content) VALUES (?,?)",
        (event_id, content),
    )
    conn.commit()
    conn.close()


def get_contexts(event_id):
    conn = get_conn()
    rows = conn.execute(
        "SELECT content FROM contexts WHERE event_id = ?", (event_id,)
    ).fetchall()
    conn.close()
    return [r["content"] for r in rows]


# --- Posts (발화글) ---
def insert_post(category, event_id, author, content):
    conn = get_conn()
    cur = conn.execute(
        "INSERT INTO posts (category, event_id, author, content) VALUES (?,?,?,?)",
        (category, event_id, author, content),
    )
    conn.commit()
    post_id = cur.lastrowid
    conn.close()
    return post_id


def get_posts(category=None, limit=50):
    conn = get_conn()
    if category:
        rows = conn.execute(
            """SELECT p.*, e.title as event_title, e.event_date, e.data as event_data, e.image_url,
                      (SELECT COUNT(*) FROM replies r WHERE r.post_id = p.id) as reply_count
               FROM posts p LEFT JOIN events e ON p.event_id = e.id
               WHERE p.category = ?
               ORDER BY p.created_at DESC LIMIT ?""",
            (category, limit),
        ).fetchall()
    else:
        rows = conn.execute(
            """SELECT p.*, e.title as event_title, e.event_date, e.data as event_data, e.image_url,
                      (SELECT COUNT(*) FROM replies r WHERE r.post_id = p.id) as reply_count
               FROM posts p LEFT JOIN events e ON p.event_id = e.id
               ORDER BY p.created_at DESC LIMIT ?""",
            (limit,),
        ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_post(post_id):
    conn = get_conn()
    row = conn.execute(
        """SELECT p.*, e.title as event_title, e.event_date, e.data as event_data
           FROM posts p LEFT JOIN events e ON p.event_id = e.id WHERE p.id = ?""",
        (post_id,),
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def like_post(post_id):
    conn = get_conn()
    conn.execute("UPDATE posts SET likes = likes + 1 WHERE id = ?", (post_id,))
    conn.commit()
    conn.close()


def delete_posts(category=None):
    conn = get_conn()
    if category:
        conn.execute("DELETE FROM replies WHERE post_id IN (SELECT id FROM posts WHERE category = ?)", (category,))
        conn.execute("DELETE FROM posts WHERE category = ?", (category,))
    else:
        conn.execute("DELETE FROM replies")
        conn.execute("DELETE FROM posts")
    conn.commit()
    conn.close()


# --- Replies ---
def insert_reply(post_id, author, content):
    conn = get_conn()
    cur = conn.execute(
        "INSERT INTO replies (post_id, author, content) VALUES (?,?,?)",
        (post_id, author, content),
    )
    conn.commit()
    conn.close()
    return cur.lastrowid


def get_replies(post_id):
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM replies WHERE post_id = ? ORDER BY created_at ASC",
        (post_id,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def like_reply(reply_id):
    conn = get_conn()
    conn.execute("UPDATE replies SET likes = likes + 1 WHERE id = ?", (reply_id,))
    conn.commit()
    conn.close()


init_db()
