# main_logic.py
import re
import sqlite3
import urllib.parse
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
        kp = kospi["Close"].iloc[-1]
        kp_c = ((kp - kospi["Open"].iloc[0]) / kospi["Open"].iloc[0]) * 100
        nq = yf.Ticker("NQ=F").history(period="1d")
        nq_c = ((nq["Close"].iloc[-1] - nq["Open"].iloc[0]) / nq["Open"].iloc[0]) * 100
        es = yf.Ticker("ES=F").history(period="1d")
        es_c = ((es["Close"].iloc[-1] - es["Open"].iloc[0]) / es["Open"].iloc[0]) * 100
        return f"KOSPI: {kp_c:+.2f}% | NQ(나스닥선물): {nq_c:+.2f}% | ES(S&P선물): {es_c:+.2f}%"
    except:
        return "지수 정보 업데이트 중..."


def get_kr_realtime_news(ticker_name):
    try:
        url = (
            f"https://search.naver.com/search.naver?where=news&query={ticker_name}+주가"
        )
        print(f"🇰🇷 [NAVER NEWS URL]: {url}")
        headers = {"User-Agent": "Mozilla/5.0"}
        res = requests.get(url, headers=headers, timeout=5)
        soup = BeautifulSoup(res.text, "html.parser")
        return [a.text for a in soup.select(".news_tit")[:3]]
    except Exception as e:
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
    """상단 시장 예측 리포트 - 영어 노출 물리적 차단 및 한글 고정"""
    conn = sqlite3.connect("virtual_trade.db")
    stocks = conn.execute(
        "SELECT name, ticker FROM stock_master WHERE price > 0 LIMIT 3"
    ).fetchall()
    conn.close()
    summary = "\n".join([f"- {s[0]}({s[1]})" for s in stocks])
    indices = get_market_indices()

    # 💡 [핵심] 시작 단어를 고정하고 영어 금지를 극단적으로 강조
    prompt = f"너는 한국 최고의 수석 전략가이다. 한국어로만 대답하라. 시작은 반드시 '현재 시장 상황은'으로 하라.\n지수: {indices}\n대상종목: {summary}"
    try:
        res = ollama.chat(
            model="llama3",
            messages=[{"role": "user", "content": prompt}],
            options={"temperature": 0.05},
        )
        reply = res["message"]["content"].strip()

        # 💡 [사후 필터링] 영어가 30자 이상 발견되면 미리 준비된 한글 리포트로 대체
        if re.search("[a-zA-Z]{30,}", reply):
            stock_names = [s[0] for s in stocks]
            return (
                f"현재 시장 지수({indices})가 변동성을 보이고 있습니다. "
                f"분석 중인 {', '.join(stock_names)} 등 저가주 섹터를 중심으로 "
                "실시간 수급 상황을 모니터링하며 기술적 반등 지점을 공략하는 전략을 추천합니다."
            )
        return reply
    except:
        return "예측 엔진 일시적 지연 중"


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

        # [DEBUG] 야후 뉴스 URL 출력 유지
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

        ticker_only_name = re.sub(r"\(.*\)", "", target_ticker).strip()
        n_news = get_kr_realtime_news(ticker_only_name)
        indices = get_market_indices()

        # AI 판단 시 한글 속보 전달
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
            "[네이버 금융 실시간 속보]\n" + "\n".join([f"• {h}" for h in n_news])
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
