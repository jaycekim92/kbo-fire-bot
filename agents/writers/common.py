"""공통 발화글 생성 유틸"""
import re
import os
import subprocess


def generate_claude(prompt):
    """Claude CLI로 발화글 생성"""
    try:
        result = subprocess.run(
            ["claude", "-p", prompt, "--output-format", "text"],
            capture_output=True, text=True, timeout=120,
        )
        if result.returncode == 0 and result.stdout.strip():
            return clean_text(result.stdout.strip())
    except Exception as e:
        print(f"[작성] Claude CLI 실패: {e}")
    return None


def generate_groq(prompt):
    """Groq API fallback"""
    try:
        from groq import Groq
        api_key = os.environ.get("GROQ_API_KEY", "")
        if not api_key:
            try:
                import streamlit as st
                api_key = st.secrets.get("GROQ_API_KEY", "")
            except Exception:
                pass
        if not api_key:
            return None

        client = Groq(api_key=api_key)
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=300,
        )
        return clean_text(response.choices[0].message.content)
    except Exception as e:
        print(f"[작성] Groq 실패: {e}")
        return None


def generate(prompt):
    """Claude CLI → Groq → None 순서로 시도"""
    return generate_claude(prompt) or generate_groq(prompt)


def clean_text(text):
    """후처리: think 태그 + 외국어 제거"""
    text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL).strip()
    text = re.sub(r'[\u0900-\u097F\u0400-\u04FF\u4E00-\u9FFF\u3040-\u309F\u30A0-\u30FF\u0E00-\u0E7F\u0600-\u06FF\u3000-\u303F]+', '', text)
    text = re.sub(r' {2,}', ' ', text).strip()
    return text
