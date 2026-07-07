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
from trade_manager import execute_scalping_buy, execute_scalping_sell

# [디버그 설정] True일 경우 콘솔에 상세 데이터를 출력합니다.
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


def get_kr_realtime_news(ticker_name):
    """네이버 금융 실시간 뉴스 수집"""
    try:
        url = f"https://search.naver.com/search.naver?where=news&query={ticker_name}"
        headers = {"User-Agent": "Mozilla/5.0"}
        res = requests.get(url, headers=headers)
        soup = BeautifulSoup(res.text, "html.parser")
        news_titles = [a.text for a in soup.select(".news_tit")[:3]]
        if DEBUG:
            print(f"🔍 [DEBUG] 네이버 실시간 뉴스 수집 완료: {len(news_titles)}건")
        return news_titles
    except Exception as e:
        if DEBUG:
            print(f"❌ [DEBUG] 네이버 뉴스 수집 실패: {e}")
        return []


def refresh_stock_pool_by_capital():
    conn = sqlite3.connect("virtual_trade.db")
    cursor = conn.cursor()
    cash = cursor.execute("SELECT cash FROM account").fetchone()[0]
    master_list = cursor.execute("SELECT ticker, name FROM stock_master").fetchall()

    if DEBUG:
        print(f"🛰️ [DEBUG] 자본금 {cash:,}원 기반 종목 필터링 시작...")

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
    prompt = f"너는 한국 수석 전략가이다. 한국어로 현재 지수 {indices}와 후보종목 {summary}를 분석하여 전략 보고하라."
    try:
        res = ollama.chat(
            model="llama3",
            messages=[{"role": "user", "content": prompt}],
            options={"temperature": 0.1},
        )
        return res["message"]["content"]
    except:
        return "예측 엔진 연결 지연"


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
    """실시간 매매 루프 (야후+네이버 뉴스 이원화 및 DEBUG 적용)"""
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
            return {"status": "WAITING", "msg": "실시간 데이터 동기화 중..."}

        price = int(df["Close"].iloc[-1])
        chart_data = df["Close"].tail(30).tolist()

        # 1. 야후 파이낸스 뉴스 (Global)
        y_news_data = stock.news
        y_headlines = []
        if y_news_data:
            for n in y_news_data[:3]:
                # 파트너님 제안: title 또는 headline 키 모두 확인
                title = n.get("title") or n.get("headline")
                if title:
                    y_headlines.append(title)
        if not y_headlines:
            y_headlines = ["글로벌 소식 지연 중"]

        # 2. 네이버 금융 뉴스 (Domestic)
        ticker_only_name = re.sub(r"\(.*\)", "", target_ticker).strip()
        n_headlines = get_kr_realtime_news(ticker_only_name)
        if not n_headlines:
            n_headlines = ["국내 속보 지연 중"]

        if DEBUG:
            print(f"📈 [DEBUG] 현재가 분석: {target_ticker} -> {price:,}원")
            print(f"📰 [DEBUG] 야후 뉴스 개수: {len(y_headlines)}")
            print(f"📰 [DEBUG] 네이버 뉴스 개수: {len(n_headlines)}")

        indices = get_market_indices()
        ai_res = get_ai_investment_decision(
            target_ticker, price, "추세분석완료", y_headlines, n_headlines, indices
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

        # 이원화된 뉴스 문자열 생성
        news_report = (
            "[글로벌(Yahoo)]\n" + "\n".join([f"• {h}" for h in y_headlines]) + "\n\n"
        )
        news_report += "[국내(Naver)]\n" + "\n".join([f"• {h}" for h in n_headlines])

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
        if DEBUG:
            print(f"🚨 [DEBUG] 루프 치명적 에러: {e}")
        return {"status": "ERROR", "msg": str(e)}
