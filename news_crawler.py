# news_crawler.py
import re
import urllib.parse

import requests
from bs4 import BeautifulSoup


def get_naver_stock_news(ticker_name, ticker_code):
    """
    네이버 뉴스에서 특정 종목의 최신 속보를 수집하는 독립 모듈
    """
    news_list = []
    try:
        # 종목코드 숫자만 추출
        pure_code = re.sub(r"[^0-9]", "", str(ticker_code))

        # 검색 쿼리 최적화: 종목명 위주로 검색
        query_str = f"{ticker_name}"
        query = urllib.parse.quote(query_str)

        # sort=1 (최신순), pd=4 (1일 이내)
        url = f"https://search.naver.com/search.naver?where=news&query={query}&sort=1&pd=4"

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        }

        res = requests.get(url, headers=headers, timeout=5)
        if res.status_code != 200:
            return [f"네이버 연결 실패 (상태코드: {res.status_code})"]

        soup = BeautifulSoup(res.text, "html.parser")

        # [네이버 뉴스 신규 구조 대응]
        titles = soup.select(".news_tit, .sds-comps-text-type-headline1, .tit_main")

        for t in titles[:3]:  # 최신 3개만 수집
            news_list.append(t.text.strip())

        # [결과 부족 시 기간 제한 해제 재검색]
        if not news_list:
            url_no_limit = (
                f"https://search.naver.com/search.naver?where=news&query={query}&sort=1"
            )
            res = requests.get(url_no_limit, headers=headers, timeout=5)
            soup = BeautifulSoup(res.text, "html.parser")
            titles = soup.select(".news_tit, .sds-comps-text-type-headline1, .tit_main")
            for t in titles[:3]:
                news_list.append(t.text.strip() + " (최근 뉴스 없음 - 전체 기간)")

    except Exception as e:
        return [f"뉴스 수집 중 오류 발생: {str(e)}"]

    return news_list


if __name__ == "__main__":
    test_name = "대창"
    test_code = "012800"
    print(f"🚀 [{test_name}] 뉴스 수집 테스트 시작...")
    results = get_naver_stock_news(test_name, test_code)
    for i, news in enumerate(results):
        print(f"{i+1}. {news}")
