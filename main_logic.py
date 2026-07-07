import logging
import re
import sqlite3
from datetime import datetime

import ollama
import requests
import yfinance as yf
from bs4 import BeautifulSoup

import config
from ai_brain import ai_discover_new_stocks, get_ai_investment_decision
from db_manager import get_statistics
from kis_api import get_access_token, get_mock_cash_balance

# 404 방지용 정제 리스트
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
    """[수정] kd_change 변수명 불일치 해결 완료"""
    try:
        kospi = yf.Ticker("^KS11").history(period="1d", timeout=config.TIMEOUT)
        kosdaq = yf.Ticker("^KQ11").history(period="1d", timeout=config.TIMEOUT)
        kp = kospi["Close"].iloc[-1]
        kp_change = ((kp - kospi["Open"].iloc[0]) / kospi["Open"].iloc[0]) * 100
        kd = kosdaq["Close"].iloc[-1]
        kd_change = ((kd - kosdaq["Open"].iloc[0]) / kosdaq["Open"].iloc[0]) * 100
        return f"KOSPI: {kp_change:+.2f}% | KOSDAQ: {kd_change:+.2f}%"
    except:
        return "지수 업데이트 중..."


def get_kr_realtime_news(ticker_name, ticker_code):
    """네이버 금융 뉴스 수집 (URL 콘솔 출력 포함)"""
    try:
        pure_code = re.sub(r"[^0-9]", "", ticker_code)
        url = f"https://search.naver.com/search.naver?where=news&query={ticker_name}+{pure_code}&sort=1&pd=4"
        print(f"📡 [DEBUG NEWS URL]: {url}")  # 파트너님 요청 사항

        headers = {"User-Agent": "Mozilla/5.0"}
        res = requests.get(url, headers=headers, timeout=config.TIMEOUT)
        soup = BeautifulSoup(res.text, "html.parser")
        titles = [a.text for a in soup.select(".news_tit")[:3]]
        for i, t in enumerate(titles):
            print(f"   ㄴ [뉴스{i+1}]: {t}")  # 콘솔 생중계
        return titles
    except Exception as e:
        logging.error(f"뉴스 수집 실패: {e}")
        return []


def refresh_stock_pool_by_capital():
    conn = sqlite3.connect("virtual_trade.db")
    cursor = conn.cursor()
    cash = cursor.execute("SELECT cash FROM account").fetchone()[0]
    conn.close()
    ai_raw = ai_discover_new_stocks(cash, ",".join(CLEAN_POOL))
    ticker_codes = re.findall(r"(\d{6}\.K[SQ])", ai_raw)
    discovered = []
    conn = sqlite3.connect("virtual_trade.db")
    cursor = conn.cursor()
    cursor.execute("DELETE FROM stock_master")
    for ticker in list(set(ticker_codes)):
        try:
            stock = yf.Ticker(ticker)
            hist = stock.history(period="1d", timeout=config.TIMEOUT)
            if not hist.empty:
                price = int(hist["Close"].iloc[-1])
                if price <= cash:
                    name = stock.info.get("shortName", ticker)
                    cursor.execute(
                        "INSERT OR REPLACE INTO stock_master VALUES (?, ?, ?)",
                        (ticker, name, price),
                    )
                    discovered.append(f"{name} ({ticker})")
        except:
            continue
    conn.commit()
    conn.close()
    return discovered if discovered else ["대한해운 (005880.KS)"]


def predict_market_view():
    """상단 시장 예측 리포트 (한글 고정)"""
    conn = sqlite3.connect("virtual_trade.db")
    stocks = conn.execute(
        "SELECT name, ticker FROM stock_master WHERE price > 0 LIMIT 3"
    ).fetchall()
    conn.close()
    summary = "\n".join([f"- {s[0]}({s[1]})" for s in stocks])
    indices = get_market_indices()
    prompt = f"너의 모국어는 {config.SYSTEM_LANGUAGE}이다. 현재 지수 {indices}와 종목군 {summary}를 분석하여 전략 보고하라. 영어 금지."
    try:
        res = ollama.chat(
            model=config.AI_MODEL,
            messages=[{"role": "user", "content": prompt}],
            options={"temperature": 0.1},
        )
        reply = res["message"]["content"].strip()
        if re.search("[a-zA-Z]{20,}", reply):
            return "현재 시장의 변동성이 높습니다. 기술적 분석을 통한 단기 매매 관점을 유지하십시오."
        return reply
    except:
        return "예측 엔진 일시 지연"


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
            cp = int(
                yf.Ticker(t)
                .history(period="1d", timeout=config.TIMEOUT)["Close"]
                .iloc[-1]
            )
            profit = (cp - a) * q
            rate = (profit / (a * q)) * 100 if a > 0 else 0
            res.append((name, t, q, a, cp, profit, rate))
        except:
            res.append((n if n else t, t, q, a, 0, 0, 0))
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
            return {"status": "WAITING", "msg": "데이터 동기화 대기 중..."}

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

        news = get_kr_realtime_news(
            re.sub(r"\(.*\)", "", target_ticker).strip(), target_ticker
        )
        indices = get_market_indices()
        ai_res = get_ai_investment_decision(
            target_ticker, price, "분석완료", [], news, indices
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
            "news": "\n".join(news) if news else "수집된 뉴스 없음",
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
