import re
import requests
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

KBO_TEAMS = ["KIA", "KT", "LG", "NC", "SSG", "두산", "롯데", "삼성", "키움", "한화"]
TEAM_PATTERN = "|".join(KBO_TEAMS)
SCORE_RE = re.compile(rf"종료({TEAM_PATTERN})(\d+)({TEAM_PATTERN})(\d+)")


def fetch_kbo_scores(game_date):
    """Daum 스포츠에서 해당 날짜 KBO 경기결과 크롤링 (Playwright)"""
    date_str = game_date.replace("-", "")
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

    # 날짜 포맷: "04.02" 형태로 매칭
    target_date = f"{game_date[5:7]}.{game_date[8:10]}"
    games = []
    current_date = ""
    current_stadium = ""

    for row in tables[1].find_all("tr")[1:]:
        cells = row.find_all("td")
        text = row.get_text(strip=True)

        # 날짜 셀 감지
        date_match = re.search(r"(\d{2}\.\d{2})", text)
        if date_match:
            current_date = date_match.group(1)

        if current_date != target_date:
            continue

        # "종료팀명스코어팀명스코어" 패턴 찾기
        m = SCORE_RE.search(text)
        if m:
            away_team, away_score, home_team, home_score = m.group(1), int(m.group(2)), m.group(3), int(m.group(4))
            # 구장 찾기
            for cell in cells:
                cell_text = cell.get_text(strip=True)
                if "야구장" in cell_text or "파크" in cell_text or "돔" in cell_text or "볼파크" in cell_text:
                    current_stadium = cell_text
                    break

            games.append({
                "game_date": game_date,
                "away_team": away_team,
                "home_team": home_team,
                "away_score": away_score,
                "home_score": home_score,
                "stadium": current_stadium,
            })

    return games


def fetch_kbo_news(home_team, away_team, max_count=3):
    """Daum 뉴스에서 경기 관련 기사 크롤링"""
    query = f"KBO {home_team} {away_team}"
    url = f"https://search.daum.net/search?w=news&q={query}"
    headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}
    try:
        resp = requests.get(url, headers=headers, timeout=5)
        soup = BeautifulSoup(resp.text, "html.parser")
        articles = []
        for a in soup.find_all("a", href=True):
            if "v.daum.net/v/" in a["href"]:
                title = a.get_text(strip=True)
                if title and len(title) > 10:
                    articles.append(title)
                    if len(articles) >= max_count:
                        break
        return articles
    except Exception:
        return []
