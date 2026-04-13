"""
피드 에이전트 — 유저에게 피드 제공, 답글/좋아요 관리
Streamlit UI를 담당한다.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from shared import db


def get_feed(category=None, limit=50):
    """카테고리별 또는 전체 피드 조회"""
    return db.get_posts(category=category, limit=limit)


def get_post_detail(post_id):
    """글 상세 + 답글"""
    post = db.get_post(post_id)
    replies = db.get_replies(post_id) if post else []
    return post, replies


def add_reply(post_id, author, content):
    """답글 추가"""
    return db.insert_reply(post_id, author, content)


def like_post(post_id):
    """글 좋아요"""
    db.like_post(post_id)


def like_reply(reply_id):
    """답글 좋아요"""
    db.like_reply(reply_id)


def clear_posts(category=None):
    """발화글 삭제"""
    db.delete_posts(category)
