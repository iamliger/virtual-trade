import re
import sqlite3
from datetime import datetime

import ollama
import requests
import yfinance as yf
from bs4 import BeautifulSoup

from ai_brain import ai_discover_new_stocks, get_ai_investment_decision
from db_manager import get_statistics
from kis_api import get_access_token, get_mock_cash_balance

DEBUG = True
CLEAN_POOL = [
    "HMM:011200.KS",
    "대한해운:005880.KS",
    "미래산업:025560.KS",
    "대원전선:006340.KS",
    "우리기술:032820.KQ",
    "팬오션:028670.KS",
    "삼성중공업:010140.KS",
    "이구산업:025820.KS",
    "모나리자:004700.KS",
    "대창:012800.KS",
    "케이옥션:102370.KQ",
]


def check_ollama_status():
    try:
        requests.get("http://localhost:11434/api/tags", timeout=2)
        return True
    except:
        return False


def get_market_indices():
    try:
        kospi = yf.Ticker("^KS11").history(period="1d")
        kosdaq = yf.Ticker("^KQ11").history(period="1d")
        kp = kospi["Close"].iloc[-1]
        kp_c = ((kp - kospi["Open"].iloc[0]) / kospi["Open"].iloc[0]) * 100
        kd = kosdaq["Close"].iloc[-1]
        kd_c = ((kd - kosdaq["Open"].iloc[0]) / kosdaq["Open"].iloc[0]) * 100
        return f"KOSPI: {kp:,.2f}({kp_c:+.2f}%), KOSDAQ: {kd:,.2f}({kd_c:+.2f}%)"
    except:
        return "지수 정보 업데이트 중..."


def get_kr_realtime_news(ticker_name, ticker_code):
    """
    [핵심 수정] 네이버 뉴스 쿼리 최적화 및 콘솔 정밀 출력
    주소 예시: https://search.naver.com/search.naver?where=news&query=HMM+011200
    """
    try:
        # 숫자 코드만 추출 (예: 011200.KS -> 011200)
        pure_code = re.sub(r"[^0-9]", "", ticker_code)
        url = f"https://search.naver.com/search.naver?where=news&query={ticker_name}+{pure_code}"

        # 1. 콘솔에 요청 URL 출력
        print(f"\n📡 [NEWS SCRAPING]: {url}")

        headers = {"User-Agent": "Mozilla/5.0"}
        res = requests.get(url, headers=headers, timeout=5)
        soup = BeautifulSoup(res.text, "html.parser")
        news_titles = [a.text for a in soup.select(".news_tit")[:3]]

        # 2. 콘솔에 수집된 뉴스 내용 생중계
        if news_titles:
            for i, title in enumerate(news_titles):
                print(f"   ㄴ [속보{i+1}]: {title}")
        else:
            print("   ㄴ ⚠️ 수집된 실시간 속보가 없습니다.")

        return news_titles
    except Exception as e:
        print(f"   ㄴ ❌ 뉴스 크롤링 에러: {e}")
        return []


def refresh_stock_pool_by_capital():
    conn = sqlite3.connect("virtual_trade.db")
    cursor = conn.cursor()
    cash = cursor.execute("SELECT cash FROM account").fetchone()[0]
    master_list = cursor.execute("SELECT ticker, name FROM stock_master").fetchall()
    discovered = []
    for ticker, name in master_list:
        try:
            stock = yf.Ticker(ticker)
            hist = stock.history(period="1d")
            if not hist.empty:
                price = int(hist["Close"].iloc[-1])
                if price <= cash:
                    cursor.execute(
                        "UPDATE stock_master SET price = ? WHERE ticker = ?",
                        (price, ticker),
                    )
                    discovered.append(f"{name} ({ticker})")
        except:
            continue
    conn.commit()
    conn.close()
    return discovered if discovered else ["대한해운 (005880.KS)"]


def predict_market_view():
    conn = sqlite3.connect("virtual_trade.db")
    stocks = conn.execute(
        "SELECT name, ticker FROM stock_master WHERE price > 0 LIMIT 3"
    ).fetchall()
    conn.close()
    summary = "\n".join([f"- {s[0]}({s[1]})" for s in stocks])
    indices = get_market_indices()
    prompt = f"너는 여의도 최고의 투자 전략가이다. 한국어로 현재 지수 {indices}와 종목군 {summary}를 분석하여 전략 보고하라. 시작은 반드시 '현재 시장 상황은'으로 하라."
    try:
        res = ollama.chat(
            model="llama3",
            messages=[{"role": "user", "content": prompt}],
            options={"temperature": 0.05},
        )
        reply = res["message"]["content"].strip()
        if re.search("[a-zA-Z]{30,}", reply):
            return f"현재 한국 시장 지수({indices})가 변동성을 보이고 있습니다. 분석 대상 종목을 중심으로 실시간 수급을 관찰하며 보수적인 단타 전략을 권장합니다."
        return reply
    except:
        return "예측 엔진 일시 연결 지연"


def get_db_history():
    conn = sqlite3.connect("virtual_trade.db")
    cursor = conn.cursor()
    cursor.execute(
        """SELECT t.trade_date, m.name, t.type, t.price, t.quantity, t.profit 
                      FROM trade_history t LEFT JOIN stock_master m ON t.ticker = m.ticker 
                      ORDER BY t.id DESC LIMIT 20"""
    )
    rows = cursor.fetchall()
    conn.close()
    return rows


def get_db_holdings_with_names():
    conn = sqlite3.connect("virtual_trade.db")
    cursor = conn.cursor()
    cursor.execute(
        "SELECT m.name, h.ticker, h.quantity, h.avg_price FROM holdings h LEFT JOIN stock_master m ON h.ticker = m.ticker"
    )
    rows = cursor.fetchall()
    conn.close()
    res = []
    for n, t, q, a in rows:
        try:
            name = n if n else t
            cp = int(yf.Ticker(t).history(period="1d")["Close"].iloc[-1])
            profit = (cp - a) * q
            rate = (profit / (a * q)) * 100 if a > 0 else 0
            res.append((name, t, q, a, cp, profit, rate))
        except:
            res.append(("데이터지연", t, q, a, 0, 0, 0))
    return res


def run_trading_cycle(token, target_ticker, daily_goal):
    try:
        today_p, week_p, month_p = get_statistics()
        conn = sqlite3.connect("virtual_trade.db")
        db_cash = conn.execute("SELECT cash FROM account").fetchone()[0]
        conn.close()
        if daily_goal > 0 and today_p >= daily_goal:
            return {
                "status": "GOAL_REACHED",
                "today_profit": today_p,
                "db_balance": db_cash,
            }

        stock = yf.Ticker(target_ticker)
        df = stock.history(period="1d", interval="1m")
        if df.empty:
            return {"status": "WAITING", "msg": "데이터 동기화 대기 중"}

        # [DEBUG] 야후 뉴스 URL
        print(
            f"🌍 [YAHOO NEWS URL]: https://finance.yahoo.com/quote/{target_ticker}/news"
        )

        price = int(df["Close"].iloc[-1])
        chart_data = df["Close"].tail(30).tolist()
        if price > db_cash:
            return {
                "status": "ACTIVE",
                "trade_status": "자산부족",
                "ticker": target_ticker,
                "price": price,
                "db_balance": db_cash,
                "today_profit": today_p,
                "weekly_profit": week_p,
                "monthly_profit": month_p,
                "decision": "HOLD",
                "reason": "가용 자산 부족",
                "news": "없음",
                "chart": chart_data,
            }

        # 💡 [핵심] 뉴스 수집 시 이름과 코드 모두 전달
        ticker_only_name = re.sub(r"\(.*\)", "", target_ticker).strip()
        n_news = get_kr_realtime_news(ticker_only_name, target_ticker)
        indices = get_market_indices()
        ai_res = get_ai_investment_decision(
            target_ticker, price, "차트분석완료", [], n_news, indices
        )
        decision = ai_res.get("decision", "HOLD")
        qty = db_cash // (price + (price * 0.0015))

        trade_msg = "관망"
        if decision == "BUY" and qty > 0:
            from trade_manager import execute_scalping_buy

            if execute_scalping_buy(target_ticker, price, qty):
                trade_msg = f"매수성공({qty}주)"
        elif decision == "SELL":
            conn = sqlite3.connect("virtual_trade.db")
            hold_qty = conn.execute(
                "SELECT quantity FROM holdings WHERE ticker = ?", (target_ticker,)
            ).fetchone()
            conn.close()
            if hold_qty and hold_qty[0] > 0:
                from trade_manager import execute_scalping_sell

                if execute_scalping_sell(target_ticker, price, hold_qty[0]):
                    trade_msg = f"매도성공({hold_qty[0]}주)"

        updated_today_p, _, _ = get_statistics()
        news_report = (
            "[국내 실시간 속보]\n" + "\n".join([f"• {h}" for h in n_news])
            if n_news
            else "[국내 속보 지연 중]"
        )
        return {
            "status": "ACTIVE",
            "ticker": target_ticker,
            "price": price,
            "decision": decision,
            "reason": ai_res.get("reason", "분석중"),
            "news": news_report,
            "db_balance": db_cash,
            "trade_status": trade_msg,
            "today_profit": updated_today_p,
            "weekly_profit": week_p,
            "monthly_profit": month_p,
            "chart": chart_data,
            "indices": indices,
        }
    except Exception as e:
        return {"status": "ERROR", "msg": str(e)}
