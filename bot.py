from groq import Groq
import os
import streamlit as st
import db
import crawler

GROQ_API_KEY = st.secrets.get("GROQ_API_KEY", os.environ.get("GROQ_API_KEY", ""))


def generate_fire_post(game, news):
    """경기결과 + 뉴스 기반 발화글 생성 (Gemini)"""
    winner = game["home_team"] if game["home_score"] > game["away_score"] else game["away_team"]
    loser = game["away_team"] if game["home_score"] > game["away_score"] else game["home_team"]
    is_tie = game["home_score"] == game["away_score"]

    game_summary = (
        f"날짜: {game['game_date']}\n"
        f"구장: {game['stadium']}\n"
        f"원정: {game['away_team']} {game['away_score']} vs 홈: {game['home_team']} {game['home_score']}\n"
        f"{'무승부' if is_tie else f'승리: {winner}, 패배: {loser}'}"
    )

    news_text = "\n".join(f"- {n}" for n in news) if news else "(관련 뉴스 없음)"

    prompt = f"""너는 야구 커뮤니티에서 경기 끝나고 글 올리는 사람이야.
특정 팀 팬은 아니고, 중립적으로 경기를 본 사람 시점이야.
반드시 한국어로만 작성해. 일본어, 영어 등 외국어는 절대 쓰지 마.

아래 경기 결과랑 뉴스 참고해서 글 하나 써줘.

[경기 결과]
{game_summary}

[참고할 뉴스 (절대 제목 그대로 쓰지 마)]
{news_text}

반드시 지킬 것:
- 첫 줄은 반드시 "{game['away_team']} {game['away_score']} : {game['home_score']} {game['home_team']}" 이것만 써
- 팀명(KIA, KT, LG, NC, SSG 등)은 반드시 영문 약어 그대로 써. 나머지는 한국어만
- 150자 이내로 짧게
- 초성체(ㅋㅋ, ㄷㄷ, ㄹㅇ 등) 쓰지 마
- 뉴스 요약하지 말고, 하나의 포인트만 잡아서 네 의견처럼 써
- 담백하게 쓰되, 마지막에 다른 팬들이 한마디 하고 싶어지는 질문이나 화두를 던져
- 반드시 반말로 써. "~합니다", "~인가요?", "~일까요?" 같은 존댓말 절대 금지. "~인가?", "~아닌가?", "~인 듯", "~같은데" 이런 식으로

중요: 팀명은 반드시 KIA, KT, LG, NC, SSG 이렇게 영문으로 써야 한다. "엘지", "기아", "엔씨" 이렇게 한글로 쓰지 마.

좋은 예시:
"웰스 6이닝 1실점인데 시범경기 폼은 진짜 몸풀기였나. 올해 LG 선발진 리그 탑이라고 봐도 되나?"
"NC 타선 진짜 무섭다. 롯데 불펜이 이걸 어떻게 막나?"

나쁜 예시 (이렇게 쓰지 마):
"엘지가 오늘 좋은 경기를 했습니다."
"의 공격력이 좋았는데" (팀명 빠짐)
"""

    try:
        client = Groq(api_key=GROQ_API_KEY)
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=500,
        )
        text = response.choices[0].message.content
        import re
        # 힌디어, 러시아어, 한자, 일본어, 태국어 등 비한글/비영문 외국어만 제거
        text = re.sub(r'[\u0900-\u097F\u0400-\u04FF\u4E00-\u9FFF\u3040-\u309F\u30A0-\u30FF\u0E00-\u0E7F\u0600-\u06FF\u3000-\u303F]+', '', text)
        text = re.sub(r' {2,}', ' ', text).strip()
        return text
    except Exception as e:
        print(f"Groq API 호출 실패: {e}")
        return _fallback_post(game, news)


def _fallback_post(game, news):
    """API 실패 시 기본 발화글"""
    headline = news[0][:80] + "..." if news and len(news[0]) > 80 else (news[0] if news else "")
    score = f"{game['away_team']} {game['away_score']} : {game['home_score']} {game['home_team']}"
    return f"[경기결과] {score}\n{headline}\n\n이 경기 본 사람? 어땠음?"


def create_posts_for_date(game_date):
    """DB에 저장된 경기결과 조회 → 뉴스 크롤링 → 발화글 생성"""
    games = db.get_games_by_date(game_date)
    if not games:
        return []

    results = []
    for game in games:
        news = db.get_news_by_game(game["id"])
        if not news:
            news = crawler.fetch_kbo_news(game["home_team"], game["away_team"])
        content = generate_fire_post(game, news)
        post_id = db.insert_post(
            game_id=game["id"],
            author="fire_bot",
            content=content,
            post_type="summary",
        )
        results.append({"id": post_id, "content": content, "game": game, "news": news})

    return results
