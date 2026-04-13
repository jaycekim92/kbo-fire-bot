"""KBO 크롤러"""
import re
import sys
from pathlib import Path
from bs4 import BeautifulSoup
from datetime import datetime, timedelta

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from shared import db
from agents.crawlers.common import HAS_PLAYWRIGHT, crawl_news

if HAS_PLAYWRIGHT:
    from playwright.sync_api import sync_playwright

KBO_TEAMS = ["KIA", "KT", "LG", "NC", "SSG", "두산", "롯데", "삼성", "키움", "한화"]
TEAM_PATTERN = "|".join(KBO_TEAMS)
SCORE_RE = re.compile(rf"종료({TEAM_PATTERN})(\d+)({TEAM_PATTERN})(\d+)")


def crawl_events(event_date):
    """경기결과 크롤링 → events 저장"""
    if not HAS_PLAYWRIGHT:
        print("[KBO 크롤러] Playwright 미설치")
        return []

    date_str = event_date.replace("-", "")
    url = f"https://sports.daum.net/schedule/kbo?date={date_str}"

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(url)
        page.wait_for_timeout(3000)
        html = page.content()
        browser.close()

    soup = BeautifulSoup(html, "html.parser")
    tables = soup.find_all("table")
    if len(tables) < 2:
        return []

    target_date = f"{event_date[5:7]}.{event_date[8:10]}"
    saved = []
    current_date = ""
    current_stadium = ""

    existing = db.get_events("kbo", event_date)
    existing_titles = {e["title"] for e in existing}

    for row in tables[1].find_all("tr")[1:]:
        cells = row.find_all("td")
        text = row.get_text(strip=True)

        date_match = re.search(r"(\d{2}\.\d{2})", text)
        if date_match:
            current_date = date_match.group(1)
        if current_date != target_date:
            continue

        m = SCORE_RE.search(text)
        if m:
            away, away_s, home, home_s = m.group(1), int(m.group(2)), m.group(3), int(m.group(4))
            for cell in cells:
                ct = cell.get_text(strip=True)
                if "야구장" in ct or "파크" in ct or "돔" in ct or "볼파크" in ct:
                    current_stadium = ct
                    break

            title = f"{away} vs {home}"
            if title not in existing_titles:
                data = {"away_team": away, "home_team": home, "away_score": away_s, "home_score": home_s, "stadium": current_stadium}
                event_id = db.insert_event("kbo", event_date, title, data)
                data["id"] = event_id
                saved.append(data)

    return saved


def crawl_contexts(event_date):
    """각 경기별 뉴스 + 이미지 크롤링 → contexts 저장"""
    events = db.get_events("kbo", event_date)
    import json
    for e in events:
        if db.get_contexts(e["id"]):
            continue
        data = json.loads(e["data"]) if isinstance(e["data"], str) else e["data"]
        news, images = crawl_news(f"{data['home_team']} {data['away_team']} 경기", event_date, fetch_images=True)
        for title in news:
            db.insert_context(e["id"], title)
        # 이미지 저장
        if images and not e.get("image_url"):
            conn = db.get_conn()
            conn.execute("UPDATE events SET image_url = ? WHERE id = ?", (images[0], e["id"]))
            conn.commit()
            conn.close()
        print(f"  {e['title']}: 뉴스 {len(news)}건, 이미지 {'O' if images else 'X'}")


def run(event_date):
    events = crawl_events(event_date)
    print(f"[KBO 크롤러] {event_date} {len(events)}경기 신규 수집")
    crawl_contexts(event_date)
    return db.get_events("kbo", event_date)


if __name__ == "__main__":
    date = sys.argv[1] if len(sys.argv) > 1 else (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    run(date)
