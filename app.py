import streamlit as st
import db
import bot
import crawler
from datetime import datetime

st.set_page_config(page_title="KBO 발화봇", page_icon="baseball", layout="centered")

# --- Custom CSS ---
st.markdown("""
<style>
    .post-card {
        background: #1a1a2e;
        border-radius: 12px;
        padding: 16px;
        margin-bottom: 12px;
        border: 1px solid #16213e;
    }
    .bot-badge {
        background: #e94560;
        color: white;
        padding: 2px 8px;
        border-radius: 12px;
        font-size: 0.75em;
        font-weight: bold;
    }
    .reply-card {
        background: #16213e;
        border-radius: 8px;
        padding: 12px;
        margin: 8px 0 8px 20px;
        border-left: 3px solid #e94560;
    }
    .score-badge {
        font-size: 1.2em;
        font-weight: bold;
    }
    .like-count {
        color: #e94560;
    }
    div[data-testid="stSidebar"] {
        background: #0f3460;
    }
</style>
""", unsafe_allow_html=True)

# --- Session State ---
import random

RANDOM_NAMES = [
    "잠실야경꾼", "직관러", "치맥은필수", "9회말역전", "만루홈런",
    "삼진아웃", "파울볼수집가", "더블헤더", "지명타자", "스퀴즈번트",
    "견제구달인", "폭투마니아", "대타전문", "응원단장", "불펜에이스",
    "타석의신", "외야석주민", "내야안타", "볼넷산책", "끝내기안타",
]

if "nickname" not in st.session_state:
    st.session_state.nickname = random.choice(RANDOM_NAMES) + str(random.randint(1, 999))
if "current_post" not in st.session_state:
    st.session_state.current_post = None


def feed_page():
    # --- Sidebar ---
    with st.sidebar:
        st.markdown(f"**{st.session_state.nickname}** 님 환영!")
        st.divider()

        st.markdown("### 발화글 생성")
        available_dates = db.get_all_game_dates()
        with st.form("add_post"):
            game_date = st.selectbox("경기 날짜", available_dates) if available_dates else None
            submitted = st.form_submit_button("발화글 생성", use_container_width=True)
            if submitted and game_date:
                date_str = game_date
                with st.spinner("발화글 생성 중..."):
                    results = bot.create_posts_for_date(date_str)
                if results:
                    st.success(f"{len(results)}경기 발화글 생성 완료!")
                    st.rerun()
                else:
                    st.warning("해당 날짜에 종료된 경기가 없습니다.")

        st.divider()
        st.caption(f"닉네임: {st.session_state.nickname}")

    # --- Main Content ---
    if st.session_state.current_post:
        post_detail_page(st.session_state.current_post)
    else:
        feed_list_page()


def feed_list_page():
    st.title("KBO 발화봇")
    st.caption("오늘 경기 어땠어? 한마디 던져봐!")

    posts = db.get_posts(limit=50)

    if not posts:
        st.info("아직 글이 없습니다. 사이드바에서 '샘플 경기 불러오기'를 눌러보세요!")
        return

    for post in posts:
        with st.container():
            # Header
            col1, col2, col3 = st.columns([1, 6, 2])
            with col1:
                if post["author"] == "fire_bot":
                    st.markdown("🤖")
                else:
                    st.markdown("👤")
            with col2:
                author_display = "**발화봇**" if post["author"] == "fire_bot" else f"**{post['author']}**"
                st.markdown(author_display)
            with col3:
                st.caption(post["created_at"][:16] if post["created_at"] else "")

            # Content — 첫 줄(경기결과)과 본문 분리
            lines = post["content"].strip().split("\n", 1)
            score_line = lines[0].strip()
            body = lines[1].strip() if len(lines) > 1 else ""
            st.markdown(f"**{score_line}**")
            if body:
                st.markdown(body)

            # Actions
            col_like, col_reply, col_open = st.columns([1, 1, 2])
            with col_like:
                if st.button(f"❤️ {post['likes']}", key=f"like_{post['id']}"):
                    db.like_post(post["id"])
                    st.rerun()
            with col_reply:
                st.markdown(f"💬 {post.get('reply_count', 0)}")
            with col_open:
                if st.button("답글 보기 →", key=f"open_{post['id']}"):
                    st.session_state.current_post = post["id"]
                    st.rerun()

            st.divider()


def post_detail_page(post_id):
    post = db.get_post(post_id)
    if not post:
        st.error("글을 찾을 수 없습니다.")
        return

    def go_back():
        st.session_state.current_post = None

    st.button("← 피드로 돌아가기", on_click=go_back)

    st.divider()

    # Post
    author_display = "🤖 **발화봇**" if post["author"] == "fire_bot" else f"👤 **{post['author']}**"
    st.markdown(author_display)
    lines = post["content"].strip().split("\n", 1)
    score_line = lines[0].strip()
    body = lines[1].strip() if len(lines) > 1 else ""
    st.markdown(f"## {score_line}")
    if body:
        st.markdown(f"### {body}")

    col_like, _ = st.columns([1, 4])
    with col_like:
        if st.button(f"❤️ {post['likes']}", key="detail_like"):
            db.like_post(post_id)
            st.rerun()

    st.divider()

    # Replies
    replies = db.get_replies(post_id)
    st.markdown(f"**답글 {len(replies)}개**")

    for reply in replies:
        with st.container():
            col1, col2 = st.columns([5, 1])
            with col1:
                st.markdown(f"**{reply['author']}**: {reply['content']}")
            with col2:
                if st.button(f"❤️ {reply['likes']}", key=f"rlike_{reply['id']}"):
                    db.like_reply(reply["id"])
                    st.rerun()

    # Reply input
    st.divider()
    reply_text = st.text_area("답글 작성", placeholder="한마디 던져봐!", max_chars=500, key="reply_input")
    if st.button("답글 달기", type="primary", use_container_width=True):
        if reply_text.strip():
            db.insert_reply(post_id, st.session_state.nickname, reply_text.strip())
            st.rerun()
        else:
            st.warning("답글을 입력해주세요!")


# --- Main ---
feed_page()
