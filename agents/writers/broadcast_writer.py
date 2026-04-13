"""방송 발화글 생성"""
import json
import yaml
import sys
from pathlib import Path
from datetime import datetime, timedelta

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from shared import db
from agents.writers.common import generate

CONFIGS_DIR = Path(__file__).parent.parent.parent / "configs"


def load_config(program_name):
    config_path = CONFIGS_DIR / f"broadcast_{program_name}.yaml"
    if not config_path.exists():
        config_path = CONFIGS_DIR / "broadcast_무명전설.yaml"
    with open(config_path, "r") as f:
        return yaml.safe_load(f)


def build_prompt(config, event, contexts):
    news_text = "\n".join(f"- {c}" for c in contexts) if contexts else "(관련 뉴스 없음)"

    return f"""{config['prompt']['system']}

[캐릭터]
{config['prompt'].get('character', '')}

[이벤트]
프로그램: {event['title']}
날짜: {event['event_date']}

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

발화글만 출력해. 설명이나 메타 코멘트 없이 발화글 본문만."""


def run(event_date, program_name="무명전설"):
    config = load_config(program_name)
    events = db.get_events("broadcast", event_date)
    events = [e for e in events if program_name in e.get("title", "")]

    if not events:
        print(f"[방송 작성] {event_date} {program_name} 이벤트 없음")
        return []

    results = []
    for event in events:
        contexts = db.get_contexts(event["id"])
        prompt = build_prompt(config, event, contexts)
        content = generate(prompt) or f"{event['title']}\n\n이거 어떻게 봄?"
        post_id = db.insert_post("broadcast", event["id"], "fire_bot", content)
        results.append({"id": post_id, "content": content})
        print(f"[방송 작성] {event['title']} → 발화글 생성")

    return results


if __name__ == "__main__":
    program = sys.argv[1] if len(sys.argv) > 1 else "무명전설"
    date = sys.argv[2] if len(sys.argv) > 2 else (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    run(date, program)
