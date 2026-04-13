import streamlit as st
import random
import sys
from pathlib import Path
from datetime import datetime, date

sys.path.insert(0, str(Path(__file__).parent))
from shared import db
from agents import feed_agent

st.set_page_config(page_title="발화봇", page_icon="baseball", layout="centered")

st.markdown("""
<style>
    .post-card { background: #1a1a2e; border-radius: 12px; padding: 16px; margin-bottom: 12px; border: 1px solid #16213e; }
    .bot-badge { background: #e94560; color: white; padding: 2px 8px; border-radius: 12px; font-size: 0.75em; font-weight: bold; }
    .reply-card { background: #16213e; border-radius: 8px; padding: 12px; margin: 8px 0 8px 20px; border-left: 3px solid #e94560; }
    .like-count { color: #e94560; }
    div[data-testid="stSidebar"] { background: #0f3460; }
</style>
""", unsafe_allow_html=True)

RANDOM_NAMES = [
    "잠실야경꾼", "직관러", "치맥은필수", "9회말역전", "만루홈런",
    "삼진아웃", "파울볼수집가", "더블헤더", "지명타자", "스퀴즈번트",
    "견제구달인", "폭투마니아", "대타전문", "응원단장", "불펜에이스",
    "타석의신", "외야석주민", "내야안타", "볼넷산책", "끝내기안타",
]

CATEGORIES = {
    "kbo": {"name": "KBO 야구", "db_key": "kbo"},
    "stock": {"name": "주식", "db_key": "stock"},
    "broadcast_무명전설": {"name": "무명전설", "db_key": "broadcast", "program": "무명전설"},
    "broadcast_대군부인": {"name": "21세기 대군부인", "db_key": "broadcast", "program": "대군부인"},
}

if "nickname" not in st.session_state:
    st.session_state.nickname = random.choice(RANDOM_NAMES) + str(random.randint(1, 999))
if "current_post" not in st.session_state:
    st.session_state.current_post = None
if "category" not in st.session_state:
    st.session_state.category = "kbo"


def get_db_key(cat):
    return CATEGORIES[cat]["db_key"]


def get_program(cat):
    return CATEGORIES[cat].get("program")


def run_crawler(cat, event_date):
    """카테고리별 크롤러 실행"""
    if cat == "kbo":
        from agents.crawlers.kbo_crawler import run
        return run(event_date)
    elif cat == "stock":
        from agents.crawlers.stock_crawler import run
        return run(event_date)
    elif cat.startswith("broadcast"):
        from agents.crawlers.broadcast_crawler import run
        return run(event_date, get_program(cat))


def _do_crawl(cat, start_date, end_date):
    """기간 크롤링 실행"""
    from datetime import timedelta
    current = start_date
    total = 0
    with st.spinner("크롤링 중..."):
        while current <= end_date:
            date_str = current.strftime("%Y-%m-%d")
            run_crawler(cat, date_str)
            total += 1
            current += timedelta(days=1)
    st.success(f"{total}일치 크롤링 완료!")
    st.rerun()


def run_writer(cat, event_date):
    """카테고리별 작성 에이전트 실행"""
    if cat == "kbo":
        from agents.writers.kbo_writer import run
        return run(event_date)
    elif cat == "stock":
        from agents.writers.stock_writer import run
        return run(event_date)
    elif cat.startswith("broadcast"):
        from agents.writers.broadcast_writer import run
        return run(event_date, get_program(cat))


def feed_page():
    cat = st.session_state.category
    db_key = get_db_key(cat)
    program = get_program(cat)

    with st.sidebar:
        st.markdown(f"**{st.session_state.nickname}** 님 환영!")
        st.divider()

        # 카테고리 선택
        cat = st.selectbox("카테고리", list(CATEGORIES.keys()), format_func=lambda x: CATEGORIES[x]["name"])
        st.session_state.category = cat
        db_key = get_db_key(cat)
        program = get_program(cat)

        st.divider()

        # 로컬 환경 감지 (Streamlit Cloud에는 /mount/src/ 경로)
        import os
        is_local = not os.path.exists("/mount/src")

        # 수집된 날짜 현황 (항상 표시)
        if program:
            existing_dates = [d for d in db.get_all_event_dates(db_key)
                            if any(program in e.get("title", "") for e in db.get_events(db_key, d))]
        else:
            existing_dates = db.get_all_event_dates(db_key)

        if existing_dates:
            dates_str = ", ".join(existing_dates[:5])
            if len(existing_dates) > 5:
                dates_str += f" 외 {len(existing_dates) - 5}일"
            st.info(f"수집된 날짜: {dates_str}")

        if is_local:
            # --- 로컬 전용: 크롤링 + 발화글 생성 ---
            st.markdown("### 데이터 수집")
            from datetime import timedelta
            with st.form("crawl"):
                col_s, col_e = st.columns(2)
                with col_s:
                    start_date = st.date_input("시작일", value=datetime.now() - timedelta(days=7))
                with col_e:
                    end_date = st.date_input("종료일", value=datetime.now())
                crawl_submitted = st.form_submit_button("크롤링 실행", use_container_width=True)

            if crawl_submitted:
                overlap = [d for d in existing_dates if start_date.strftime("%Y-%m-%d") <= d <= end_date.strftime("%Y-%m-%d")]
                if overlap:
                    st.warning(f"⚠️ {overlap[-1]} ~ {overlap[0]} ({len(overlap)}일) 데이터가 이미 있습니다.")
                    col_y, col_n = st.columns(2)
                    with col_y:
                        if st.button("덮어쓰기 (재수집)", use_container_width=True):
                            _do_crawl(cat, start_date, end_date)
                    with col_n:
                        if st.button("취소", use_container_width=True):
                            st.rerun()
                else:
                    _do_crawl(cat, start_date, end_date)

            st.markdown("### 발화글 생성")
            with st.form("write"):
                event_date = st.selectbox("날짜", existing_dates) if existing_dates else None
                write_submitted = st.form_submit_button("발화글 생성", use_container_width=True)
                if write_submitted and event_date:
                    with st.spinner("발화글 생성 중..."):
                        results = run_writer(cat, event_date)
                    if results:
                        st.success(f"{len(results)}건 생성 완료!")
                        st.rerun()
                    else:
                        st.warning("이벤트가 없습니다.")

            st.divider()
            if st.button("발화글 전체 삭제", use_container_width=True):
                feed_agent.clear_posts(db_key)
                st.success("삭제 완료!")
                st.rerun()

        st.caption(f"닉네임: {st.session_state.nickname}")

    # Main Content
    if st.session_state.current_post:
        post_detail_page(st.session_state.current_post)
    else:
        feed_list_page(cat)


def feed_list_page(category):
    db_key = get_db_key(category)
    program = get_program(category)

    st.title(CATEGORIES[category]["name"])
    st.caption("한마디 던져봐!")

    posts = feed_agent.get_feed(category=db_key, limit=50)
    # 방송은 프로그램별 필터
    if program:
        posts = [p for p in posts if program in (p.get("event_title") or "")]

    if not posts:
        st.info("아직 글이 없습니다. 사이드바에서 크롤링 → 발화글 생성을 해보세요!")
        return

    for post in posts:
        with st.container():
            col1, col2, col3 = st.columns([1, 6, 2])
            with col1:
                st.markdown("🤖" if post["author"] == "fire_bot" else "👤")
            with col2:
                author_display = "**발화봇**" if post["author"] == "fire_bot" else f"**{post['author']}**"
                st.markdown(author_display)
            with col3:
                st.caption(post["created_at"][:16] if post["created_at"] else "")

            # 이미지
            if post.get("image_url"):
                st.image(post["image_url"], use_container_width=True)

            lines = post["content"].strip().split("\n", 1)
            st.markdown(f"**{lines[0].strip()}**")
            if len(lines) > 1:
                st.markdown(lines[1].strip())

            col_like, col_reply, col_open = st.columns([1, 1, 2])
            with col_like:
                if st.button(f"❤️ {post['likes']}", key=f"like_{post['id']}"):
                    feed_agent.like_post(post["id"])
                    st.rerun()
            with col_reply:
                st.markdown(f"💬 {post.get('reply_count', 0)}")
            with col_open:
                if st.button("답글 보기 →", key=f"open_{post['id']}"):
                    st.session_state.current_post = post["id"]
                    st.rerun()

            st.divider()


def post_detail_page(post_id):
    post, replies = feed_agent.get_post_detail(post_id)
    if not post:
        st.error("글을 찾을 수 없습니다.")
        return

    def go_back():
        st.session_state.current_post = None

    st.button("← 피드로 돌아가기", on_click=go_back)
    st.divider()

    author_display = "🤖 **발화봇**" if post["author"] == "fire_bot" else f"👤 **{post['author']}**"
    st.markdown(author_display)
    lines = post["content"].strip().split("\n", 1)
    st.markdown(f"## {lines[0].strip()}")
    if len(lines) > 1:
        st.markdown(f"### {lines[1].strip()}")

    col_like, _ = st.columns([1, 4])
    with col_like:
        if st.button(f"❤️ {post['likes']}", key="detail_like"):
            feed_agent.like_post(post_id)
            st.rerun()

    st.divider()
    st.markdown(f"**답글 {len(replies)}개**")

    for reply in replies:
        with st.container():
            col1, col2 = st.columns([5, 1])
            with col1:
                st.markdown(f"**{reply['author']}**: {reply['content']}")
            with col2:
                if st.button(f"❤️ {reply['likes']}", key=f"rlike_{reply['id']}"):
                    feed_agent.like_reply(reply["id"])
                    st.rerun()

    st.divider()
    reply_text = st.text_area("답글 작성", placeholder="한마디 던져봐!", max_chars=500, key="reply_input")
    if st.button("답글 달기", type="primary", use_container_width=True):
        if reply_text.strip():
            feed_agent.add_reply(post_id, st.session_state.nickname, reply_text.strip())
            st.rerun()
        else:
            st.warning("답글을 입력해주세요!")


# --- Main ---
feed_page()
