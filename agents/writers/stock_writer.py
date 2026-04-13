"""주식 발화글 생성 — 대형주 1건 + 이슈주 1건"""
import json
import yaml
import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from shared import db
from agents.writers.common import generate

CONFIG_PATH = Path(__file__).parent.parent.parent / "configs" / "stock.yaml"


def load_config():
    with open(CONFIG_PATH, "r") as f:
        return yaml.safe_load(f)


def build_prompt(config, theme, stocks, all_contexts):
    """테마별 종목들을 묶어서 프롬프트 생성"""
    stocks_summary = ""
    for s in stocks:
        stocks_summary += f"- {s['stock_name']} {s['change_pct']} (현재가 {s['price']}, 거래량 {s.get('volume','')})\n"

    news_text = "\n".join(f"- {c}" for c in all_contexts) if all_contexts else "(관련 뉴스 없음)"

    return f"""{config['prompt']['system']}

[캐릭터]
{config['prompt'].get('character', '')}

[테마: {theme}]
{stocks_summary}

[참고 뉴스 (절대 제목 그대로 쓰지 마)]
{news_text}

[작성 규칙]
{config['prompt']['rules']}

[팩트 선별 기준]
{config['prompt'].get('fact_selection', '')}

[포맷 (아래 중 하나 선택)]
{config['prompt'].get('format_rotation', '')}

좋은 예시:
{chr(10).join(e.strip() for e in config['prompt']['examples']['good'])}

나쁜 예시:
{chr(10).join(f'"{e}"' for e in config['prompt']['examples']['bad'])}

중요:
- 위 종목들을 묶어서 발화글 1개만 써
- 첫 줄에 종목명과 등락률 나열
- 시장 흐름과 엮어서 하나의 맥락으로
- 발화글만 출력. 설명 없이 본문만."""


def run(event_date):
    config = load_config()
    events = db.get_events("stock", event_date)
    if not events:
        print(f"[주식 작성] {event_date} 이벤트 없음")
        return []

    # 테마별로 묶기
    themes = {}
    for e in events:
        data = json.loads(e["data"]) if isinstance(e["data"], str) else e["data"]
        theme = data.get("theme", "종목")
        if theme not in themes:
            themes[theme] = {"stocks": [], "contexts": [], "event_ids": []}
        themes[theme]["stocks"].append(data)
        themes[theme]["contexts"].extend(db.get_contexts(e["id"]))
        themes[theme]["event_ids"].append(e["id"])

    results = []
    for theme, info in themes.items():
        prompt = build_prompt(config, theme, info["stocks"], info["contexts"])
        content = generate(prompt)
        if not content:
            names = ", ".join(s["stock_name"] for s in info["stocks"])
            content = f"{names}\n\n이거 어떻게 봄?"

        # 첫 번째 이벤트에 연결
        post_id = db.insert_post("stock", info["event_ids"][0], "fire_bot", content)
        results.append({"id": post_id, "content": content})
        print(f"[주식 작성] [{theme}] → 발화글 생성")

    return results


if __name__ == "__main__":
    date = sys.argv[1] if len(sys.argv) > 1 else datetime.now().strftime("%Y-%m-%d")
    run(date)
