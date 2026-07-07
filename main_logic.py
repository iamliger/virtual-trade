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


def check_ollama_status():
    try:
        requests.get("http://localhost:11434/api/tags", timeout=2)
        return True
    except:
        return False


def get_market_indices():
    """KOSPI, KOSDAQ 지수 (kd_change 변수명 일치 확인 완료)"""
    try:
        kospi = yf.Ticker("^KS11").history(period="1d")
        kosdaq = yf.Ticker("^KQ11").history(period="1d")
        kp = kospi["Close"].iloc[-1]
        kp_change = ((kp - kospi["Open"].iloc[0]) / kospi["Open"].iloc[0]) * 100
        kd = kosdaq["Close"].iloc[-1]
        kd_change = ((kd - kosdaq["Open"].iloc[0]) / kosdaq["Open"].iloc[0]) * 100
        return (
            f"KOSPI: {kp:,.2f}({kp_change:+.2f}%), KOSDAQ: {kd:,.2f}({kd_change:+.2f}%)"
        )
    except:
        return "지수 정보 업데이트 중..."


def get_kr_realtime_news(ticker_name):
    try:
        url = f"https://search.naver.com/search.naver?where=news&query={ticker_name}"
        headers = {"User-Agent": "Mozilla/5.0"}
        res = requests.get(url, headers=headers)
        soup = BeautifulSoup(res.text, "html.parser")
        return [a.text for a in soup.select(".news_tit")[:3]]
    except:
        return []


def refresh_stock_pool_by_capital():
    """자본금 맞춤 종목 발굴"""
    conn = sqlite3.connect("virtual_trade.db")
    cash = conn.execute("SELECT cash FROM account").fetchone()[0]
    conn.close()

    # DB에 등록된 종목 리스트 로드
    conn = sqlite3.connect("virtual_trade.db")
    cursor = conn.cursor()
    cursor.execute("SELECT ticker, name FROM stock_master")
    master_list = cursor.fetchall()

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
    prompt = f"너는 한국 수석 전략가이다. 현재 지수 {indices}와 후보종목 {summary}를 분석해 한글로 단타 전략을 보고하라."
    try:
        res = ollama.chat(
            model="llama3",
            messages=[{"role": "user", "content": prompt}],
            options={"temperature": 0.1},
        )
        reply = res["message"]["content"]
        return (
            reply
            if not re.search("[a-zA-Z]{15,}", reply)
            else "시장 변동성에 대비하여 철저한 분할 매수 전략을 유지하십시오."
        )
    except:
        return "예측 엔진 연결 지연"


def get_db_history():
    """최근 매매 내역 조회"""
    conn = sqlite3.connect("virtual_trade.db")
    cursor = conn.cursor()
    cursor.execute(
        """SELECT t.trade_date, m.name, t.type, t.price, t.quantity, t.profit 
                      FROM trade_history t 
                      LEFT JOIN stock_master m ON t.ticker = m.ticker 
                      ORDER BY t.id DESC LIMIT 20"""
    )
    rows = cursor.fetchall()
    conn.close()
    return rows


def get_db_holdings_with_names():
    """보유 현황 조회"""
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
            return {"status": "WAITING", "msg": "실시간 데이터 수신 중..."}

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

        news = get_kr_realtime_news(target_ticker.split(".")[0])
        indices = get_market_indices()
        ai_res = get_ai_investment_decision(
            target_ticker, price, "추세분석완료", news, indices
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
        return {
            "status": "ACTIVE",
            "ticker": target_ticker,
            "price": price,
            "decision": decision,
            "reason": ai_res.get("reason", "분석중"),
            "news": "\n".join(news) if news else "뉴스 없음",
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
