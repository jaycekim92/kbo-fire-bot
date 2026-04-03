import sqlite3
import json
from pathlib import Path

DB_PATH = Path(__file__).parent / "kbo_firebot.db"
SCHEMA_PATH = Path(__file__).parent / "schema.sql"


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


# --- Games ---
def insert_game(game_date, home_team, away_team, home_score, away_score, stadium, raw_data=None):
    conn = get_conn()
    cur = conn.execute(
        "INSERT INTO games (game_date, home_team, away_team, home_score, away_score, stadium, raw_data) VALUES (?,?,?,?,?,?,?)",
        (game_date, home_team, away_team, home_score, away_score, stadium, json.dumps(raw_data, ensure_ascii=False) if raw_data else None),
    )
    conn.commit()
    game_id = cur.lastrowid
    conn.close()
    return game_id


def get_games_by_date(game_date):
    conn = get_conn()
    rows = conn.execute("SELECT * FROM games WHERE game_date = ? ORDER BY id", (game_date,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_all_game_dates():
    conn = get_conn()
    rows = conn.execute("SELECT DISTINCT game_date FROM games ORDER BY game_date DESC").fetchall()
    conn.close()
    return [r["game_date"] for r in rows]


# --- Posts ---
def insert_post(game_id, author, content, post_type="summary"):
    conn = get_conn()
    cur = conn.execute(
        "INSERT INTO posts (game_id, author, content, post_type) VALUES (?,?,?,?)",
        (game_id, author, content, post_type),
    )
    conn.commit()
    post_id = cur.lastrowid
    conn.close()
    return post_id


def get_posts(limit=50):
    conn = get_conn()
    rows = conn.execute(
        """SELECT p.*, g.home_team, g.away_team, g.home_score, g.away_score, g.game_date,
                  (SELECT COUNT(*) FROM replies r WHERE r.post_id = p.id) as reply_count
           FROM posts p LEFT JOIN games g ON p.game_id = g.id
           ORDER BY p.created_at DESC LIMIT ?""",
        (limit,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_post(post_id):
    conn = get_conn()
    row = conn.execute(
        """SELECT p.*, g.home_team, g.away_team, g.home_score, g.away_score, g.game_date
           FROM posts p LEFT JOIN games g ON p.game_id = g.id WHERE p.id = ?""",
        (post_id,),
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def like_post(post_id):
    conn = get_conn()
    conn.execute("UPDATE posts SET likes = likes + 1 WHERE id = ?", (post_id,))
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
    reply_id = cur.lastrowid
    conn.close()
    return reply_id


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


# --- Users ---
def get_or_create_user(nickname):
    conn = get_conn()
    row = conn.execute("SELECT * FROM users WHERE nickname = ?", (nickname,)).fetchone()
    if not row:
        conn.execute("INSERT INTO users (nickname) VALUES (?)", (nickname,))
        conn.commit()
        row = conn.execute("SELECT * FROM users WHERE nickname = ?", (nickname,)).fetchone()
    conn.close()
    return dict(row)


# --- News ---
def get_news_by_game(game_id):
    conn = get_conn()
    rows = conn.execute("SELECT title FROM news WHERE game_id = ?", (game_id,)).fetchall()
    conn.close()
    return [r["title"] for r in rows]


# Initialize on import
init_db()
