"""공통 크롤링 유틸"""
import requests
from bs4 import BeautifulSoup

try:
    from playwright.sync_api import sync_playwright
    HAS_PLAYWRIGHT = True
except ImportError:
    HAS_PLAYWRIGHT = False

HEADERS = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}


def fetch_article_lead(url, max_chars=300):
    """다음 뉴스 기사 본문에서 리드문 추출"""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=5)
        soup = BeautifulSoup(resp.text, "html.parser")
        paragraphs = soup.find_all(attrs={"dmcf-ptype": "general"})
        if not paragraphs:
            article = soup.find(class_="article_view")
            if article:
                paragraphs = article.find_all("p")
        lead = ""
        for p in paragraphs:
            text = p.get_text(strip=True)
            if text and len(text) > 20:
                lead += text + " "
                if len(lead) >= max_chars:
                    break
        return lead[:max_chars].strip()
    except Exception:
        return ""


def fetch_article_image(url):
    """다음 뉴스 기사에서 대표 이미지(og:image) 추출"""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=5)
        soup = BeautifulSoup(resp.text, "html.parser")
        og = soup.find("meta", property="og:image")
        if og and og.get("content"):
            return og["content"]
    except Exception:
        pass
    return ""


def crawl_news(query, event_date=None, max_count=3, fetch_images=False):
    """Daum 뉴스 검색 → 제목 + 리드문 반환. fetch_images=True면 이미지도."""
    date_compact = event_date.replace("-", "") if event_date else ""
    url = f"https://search.daum.net/search?w=news&q={query}&sort=recency"
    if date_compact:
        url += f"&sd={date_compact}000000&ed={date_compact}235959&period=u"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=5)
        soup = BeautifulSoup(resp.text, "html.parser")
        articles = []
        images = []
        seen_urls = set()
        for a in soup.find_all("a", href=True):
            if "v.daum.net/v/" in a["href"]:
                article_url = a["href"]
                if not article_url.startswith("http"):
                    article_url = "https:" + article_url
                url_id = article_url.split("/v/")[-1][:14]
                if url_id in seen_urls:
                    continue
                title = a.get_text(strip=True)
                if title and len(title) > 10:
                    seen_urls.add(url_id)
                    lead = fetch_article_lead(article_url)
                    if lead:
                        articles.append(f"{title} | {lead}")
                    else:
                        articles.append(title)

                    if fetch_images and not images:
                        img = fetch_article_image(article_url)
                        if img:
                            images.append(img)

                    if len(articles) >= max_count:
                        break

        if fetch_images:
            return articles, images
        return articles
    except Exception:
        if fetch_images:
            return [], []
        return []
