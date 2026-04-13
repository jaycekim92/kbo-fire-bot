"""주식 크롤러 — 대형주 + 오늘의 이슈"""
import sys
from pathlib import Path
from bs4 import BeautifulSoup
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from shared import db
from agents.crawlers.common import HAS_PLAYWRIGHT, crawl_news

if HAS_PLAYWRIGHT:
    from playwright.sync_api import sync_playwright


def _crawl_page(url):
    """Playwright로 페이지 크롤링 → BeautifulSoup 반환"""
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(url)
        page.wait_for_timeout(3000)
        html = page.content()
        browser.close()
    return BeautifulSoup(html, "html.parser")


def _parse_stock_table(soup, table_idx=1, limit=10):
    """테이블에서 종목 파싱"""
    tables = soup.find_all("table")
    if len(tables) <= table_idx:
        return []

    stocks = []
    for row in tables[table_idx].find_all("tr")[1:limit+1]:
        cells = row.find_all("td")
        if len(cells) < 5:
            continue
        name = cells[1].get_text(strip=True)
        price = cells[2].get_text(strip=True)
        change = cells[3].get_text(strip=True)
        pct = cells[4].get_text(strip=True)
        volume = cells[5].get_text(strip=True) if len(cells) > 5 else ""
        if name:
            stocks.append({"name": name, "price": price, "change": change, "pct": pct, "volume": volume})
    return stocks


def crawl_events(event_date):
    """대형주 + 이슈주 크롤링 → events 저장"""
    if not HAS_PLAYWRIGHT:
        print("[주식 크롤러] Playwright 미설치")
        return []

    existing = db.get_events("stock", event_date)
    if existing:
        return []

    saved = []

    # 1. 시총 상위 10 (대형주)
    soup = _crawl_page("https://finance.daum.net/domestic/market_cap")
    top10 = _parse_stock_table(soup, table_idx=1, limit=10)
    top10_names = {s["name"] for s in top10}

    # 등락률 절대값 큰 순으로 정렬 → 상위 2개
    for s in top10:
        try:
            s["pct_abs"] = abs(float(s["pct"].replace("%", "").replace("+", "").replace(",", "")))
        except ValueError:
            s["pct_abs"] = 0
    top10.sort(key=lambda x: x["pct_abs"], reverse=True)

    for s in top10[:2]:
        data = {"stock_name": s["name"], "price": s["price"], "change": s["change"],
                "change_pct": s["pct"], "volume": s["volume"], "theme": "대형주"}
        title = f"[대형주] {s['name']} {s['pct']}"
        event_id = db.insert_event("stock", event_date, title, data)
        data["id"] = event_id
        saved.append(data)

    # 2. 거래량 상위 (이슈주) — 시총 상위와 안 겹치는 것
    soup2 = _crawl_page("https://finance.daum.net/domestic/rise_stocks")
    risers = _parse_stock_table(soup2, table_idx=1, limit=20)

    issue_count = 0
    for s in risers:
        if s["name"] in top10_names:
            continue
        if "ETN" in s["name"] or "ETF" in s["name"] or "인버스" in s["name"] or "레버리지" in s["name"] or "우" == s["name"][-1:]:
            continue

        data = {"stock_name": s["name"], "price": s["price"], "change": s["change"],
                "change_pct": s["pct"], "volume": s["volume"], "theme": "이슈주"}
        title = f"[이슈주] {s['name']} {s['pct']}"
        event_id = db.insert_event("stock", event_date, title, data)
        data["id"] = event_id
        saved.append(data)

        issue_count += 1
        if issue_count >= 2:
            break

    return saved


def crawl_contexts(event_date):
    """각 종목별 뉴스 크롤링 → contexts 저장"""
    import json
    events = db.get_events("stock", event_date)
    for e in events:
        if db.get_contexts(e["id"]):
            continue
        data = json.loads(e["data"]) if isinstance(e["data"], str) else e["data"]
        news = crawl_news(data["stock_name"], event_date, max_count=3)
        for title in news:
            db.insert_context(e["id"], title)
        print(f"  {e['title']}: 뉴스 {len(news)}건")


def run(event_date):
    events = crawl_events(event_date)
    print(f"[주식 크롤러] {event_date} {len(events)}종목 수집")
    crawl_contexts(event_date)
    return db.get_events("stock", event_date)


if __name__ == "__main__":
    date = sys.argv[1] if len(sys.argv) > 1 else datetime.now().strftime("%Y-%m-%d")
    run(date)
