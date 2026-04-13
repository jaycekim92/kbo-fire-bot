"""KBO 발화글 생성"""
import json
import yaml
import sys
from pathlib import Path
from datetime import datetime, timedelta

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from shared import db
from agents.writers.common import generate

CONFIG_PATH = Path(__file__).parent.parent.parent / "configs" / "kbo.yaml"


def load_config():
    with open(CONFIG_PATH, "r") as f:
        return yaml.safe_load(f)


def build_prompt(config, event, contexts):
    data = json.loads(event["data"]) if isinstance(event["data"], str) else event["data"]
    news_text = "\n".join(f"- {c}" for c in contexts) if contexts else "(관련 뉴스 없음)"

    prompt_vars = {**data, "event_date": event["event_date"]}
    winner = data["home_team"] if data["home_score"] > data["away_score"] else data["away_team"]
    loser = data["away_team"] if data["home_score"] > data["away_score"] else data["home_team"]
    is_tie = data["home_score"] == data["away_score"]

    event_summary = (
        f"날짜: {event['event_date']}\n"
        f"원정: {data['away_team']} {data['away_score']} vs 홈: {data['home_team']} {data['home_score']}\n"
        f"{'무승부' if is_tie else f'승리: {winner}, 패배: {loser}'}"
    )

    return f"""{config['prompt']['system']}

[캐릭터]
{config['prompt'].get('character', '')}

[이벤트]
{event_summary}

[참고 뉴스 (절대 제목 그대로 쓰지 마)]
{news_text}

[작성 규칙]
{config['prompt']['rules'].format(**prompt_vars)}

[팩트 선별 기준]
{config['prompt'].get('fact_selection', '')}

[포맷 (아래 중 하나 선택, 같은 형식 반복 금지)]
{config['prompt'].get('format_rotation', '')}

좋은 예시:
{chr(10).join(e.strip() for e in config['prompt']['examples']['good'])}

나쁜 예시:
{chr(10).join(f'"{e}"' for e in config['prompt']['examples']['bad'])}

발화글만 출력해. 설명이나 메타 코멘트 없이 발화글 본문만."""


def run(event_date):
    config = load_config()
    events = db.get_events("kbo", event_date)
    if not events:
        print(f"[KBO 작성] {event_date} 이벤트 없음")
        return []

    results = []
    for event in events:
        contexts = db.get_contexts(event["id"])
        prompt = build_prompt(config, event, contexts)
        content = generate(prompt) or f"{event['title']}\n\n이거 어떻게 봄?"
        post_id = db.insert_post("kbo", event["id"], "fire_bot", content)
        results.append({"id": post_id, "content": content})
        print(f"[KBO 작성] {event['title']} → 발화글 생성")

    return results


if __name__ == "__main__":
    date = sys.argv[1] if len(sys.argv) > 1 else (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    run(date)
