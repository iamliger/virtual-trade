# news_crawler.py
import re
import urllib.parse

import requests
from bs4 import BeautifulSoup


def get_naver_stock_news(ticker_name, ticker_code):
    """
    네이버 증권 종목 뉴스 섹션 직접 크롤링 (User-Agent 및 Referer 보강)
    """
    news_list = []
    try:
        pure_code = re.sub(r"[^0-9]", "", str(ticker_code))
        # 네이버 증권 전용 뉴스 URL (통합검색보다 차단이 적음)
        url = f"https://finance.naver.com/item/news_news.naver?code={pure_code}"

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
            "Referer": f"https://finance.naver.com/item/main.naver?code={pure_code}",
            "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
        }

        print(f"🔍 [DEBUG NEWS URL]: {url}")
        res = requests.get(url, headers=headers, timeout=7)
        res.encoding = "euc-kr"  # 네이버 금융은 EUC-KR 사용

        soup = BeautifulSoup(res.text, "html.parser")
        # 제목 선택자 정밀 타겟팅
        titles = soup.select(".tit")

        for t in titles[:5]:
            headline = t.text.strip()
            if headline:
                news_list.append(headline)
                print(f"   ㄴ [SUCCESS]: {headline[:30]}...")

        # 만약 증권 섹터 뉴스가 없으면 통합 검색으로 Fallback
        if not news_list:
            print("   ⚠️ [WARNING]: 증권 섹터 뉴스 부재, 통합 검색 시도...")
            query = urllib.parse.quote(ticker_name)
            fallback_url = (
                f"https://search.naver.com/search.naver?where=news&query={query}&sort=1"
            )
            res = requests.get(fallback_url, headers=headers, timeout=5)
            soup = BeautifulSoup(res.text, "html.parser")
            for t in soup.select(".news_tit")[:3]:
                news_list.append(t.text.strip())

    except Exception as e:
        print(f"   ❌ [ERROR]: 뉴스 크롤링 중 치명적 오류 - {e}")
        return [f"뉴스 수집 일시 중단: {str(e)}"]

    return news_list
