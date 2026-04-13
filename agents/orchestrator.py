"""
오케스트레이터 — 컨트롤타워
각 에이전트를 독립적으로 호출. 직접 로직 없음.

사용법:
  python3 agents/orchestrator.py kbo 2026-04-01           # KBO 크롤링+발화
  python3 agents/orchestrator.py stock 2026-04-10          # 주식 크롤링+발화
  python3 agents/orchestrator.py broadcast 무명전설 2026-04-09    # 방송 크롤링+발화
  python3 agents/orchestrator.py broadcast 대군부인 2026-04-11
"""
import sys
from pathlib import Path
from datetime import datetime, timedelta

sys.path.insert(0, str(Path(__file__).parent.parent))


def run_kbo(event_date):
    from agents.crawlers.kbo_crawler import run as crawl
    from agents.writers.kbo_writer import run as write
    print(f"=== [KBO] {event_date} ===")
    crawl(event_date)
    write(event_date)


def run_stock(event_date):
    from agents.crawlers.stock_crawler import run as crawl
    from agents.writers.stock_writer import run as write
    print(f"=== [주식] {event_date} ===")
    crawl(event_date)
    write(event_date)


def run_broadcast(program_name, event_date):
    from agents.crawlers.broadcast_crawler import run as crawl
    from agents.writers.broadcast_writer import run as write
    print(f"=== [방송: {program_name}] {event_date} ===")
    crawl(event_date, program_name)
    write(event_date, program_name)


if __name__ == "__main__":
    category = sys.argv[1] if len(sys.argv) > 1 else "kbo"
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")

    if category == "kbo":
        date = sys.argv[2] if len(sys.argv) > 2 else yesterday
        run_kbo(date)
    elif category == "stock":
        date = sys.argv[2] if len(sys.argv) > 2 else yesterday
        run_stock(date)
    elif category == "broadcast":
        program = sys.argv[2] if len(sys.argv) > 2 else "무명전설"
        date = sys.argv[3] if len(sys.argv) > 3 else yesterday
        run_broadcast(program, date)
    else:
        print(f"미지원: {category}. 사용: kbo, stock, broadcast")
