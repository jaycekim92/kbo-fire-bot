"""방송 크롤러"""
import sys
from pathlib import Path
from datetime import datetime, timedelta

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from shared import db
from agents.crawlers.common import crawl_news


def crawl_events(event_date, program_name):
    """방송 프로그램 뉴스 크롤링 → events + contexts 저장"""
    existing = db.get_events("broadcast", event_date)
    if any(program_name in e.get("title", "") for e in existing):
        return []

    news, images = crawl_news(program_name, event_date, max_count=5, fetch_images=True)
    if not news:
        print(f"[방송 크롤러] {event_date} {program_name} 뉴스 없음")
        return []

    data = {"program": program_name, "news_count": len(news)}
    image_url = images[0] if images else None
    event_id = db.insert_event("broadcast", event_date, program_name, data, image_url=image_url)

    for title in news:
        db.insert_context(event_id, title)

    return [{"id": event_id, "program": program_name, "news": news, "image": image_url}]


def run(event_date, program_name="무명전설"):
    events = crawl_events(event_date, program_name)
    print(f"[방송 크롤러] {event_date} {program_name} {len(events)}건 수집")

    all_events = db.get_events("broadcast", event_date)
    all_events = [e for e in all_events if program_name in e.get("title", "")]
    for e in all_events:
        contexts = db.get_contexts(e["id"])
        print(f"  {e['title']}: 뉴스 {len(contexts)}건")

    return all_events


if __name__ == "__main__":
    program = sys.argv[1] if len(sys.argv) > 1 else "무명전설"
    date = sys.argv[2] if len(sys.argv) > 2 else (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    run(date, program)
