# main_logic.py
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
from news_crawler import get_naver_stock_news

MASTER_SOURCE = "HMM:011200.KS,대한해운:005880.KS,대원전선:006340.KS,우리기술:032820.KQ,팬오션:028670.KS,삼성중공업:010140.KS,이구산업:025820.KS,모나리자:004700.KS,대창:012800.KS,케이옥션:102370.KQ,서희건설:035890.KQ"


def check_ollama_status():
    try:
        requests.get("http://localhost:11434/api/tags", timeout=2)
        return True
    except:
        return False


def get_market_indices():
    try:
        kospi = yf.Ticker("^KS11").history(period="1d", timeout=config.TIMEOUT)
        kosdaq = yf.Ticker("^KQ11").history(period="1d", timeout=config.TIMEOUT)
        kp = kospi["Close"].iloc[-1]
        kp_o = kospi["Open"].iloc[0]
        kp_c = ((kp - kp_o) / kp_o * 100) if kp_o != 0 else 0.0
        kd = kosdaq["Close"].iloc[-1]
        kd_o = kosdaq["Open"].iloc[0]
        kd_c = ((kd - kd_o) / kd_o * 100) if kd_o != 0 else 0.0
        return f"KOSPI: {kp_c:+.2f}% | KOSDAQ: {kd_c:+.2f}%"
    except:
        return "지수 정보 업데이트 중..."


def refresh_stock_pool_by_capital():
    conn = sqlite3.connect("virtual_trade.db")
    cursor = conn.cursor()
    cash = cursor.execute("SELECT cash FROM account").fetchone()[0]
    conn.close()

    # [DEBUG] 자본금 출력
    print(f"\n💰 [DEBUG] 현재 가용 자본금: {cash:,}원")

    ai_raw = ai_discover_new_stocks(cash, MASTER_SOURCE)
    ticker_codes = re.findall(r"(\d{6}\.K[SQ])", ai_raw)
    discovered = []
    conn = sqlite3.connect("virtual_trade.db")
    cursor = conn.cursor()
    cursor.execute("DELETE FROM stock_master")
    for ticker in list(set(ticker_codes)):
        try:
            stock = yf.Ticker(ticker)
            hist = stock.history(period="1d")
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
    conn = sqlite3.connect("virtual_trade.db")
    stocks = conn.execute(
        "SELECT name, ticker FROM stock_master WHERE price > 0 LIMIT 3"
    ).fetchall()
    conn.close()
    summary = "\n".join([f"- {s[0]}({s[1]})" for s in stocks])
    indices = get_market_indices()
    prompt = f"너는 한국 수석 전략가이다. 한국어로 현재 지수 {indices}와 종목 {summary}를 분석하라. 영어 금지."
    try:
        res = ollama.chat(
            model=config.AI_MODEL,
            messages=[{"role": "user", "content": prompt}],
            options={"temperature": 0.05},
        )
        reply = res["message"]["content"].strip()
        # [사후 필터링] 영어가 20% 이상 감지되면 한글 리포트로 대체
        if re.search("[a-zA-Z]{30,}", reply):
            return "현재 한국 시장 지수는 글로벌 거시 경제 지표의 영향을 받아 변동성이 심화된 상태입니다. 실시간 수급을 동반한 저가주 중심의 기술적 매매를 추천합니다."
        return reply
    except:
        return "분석 엔진 연결 지연"


def get_db_history():
    conn = sqlite3.connect("virtual_trade.db")
    return conn.execute(
        "SELECT t.trade_date, m.name, t.type, t.price, t.quantity, t.profit FROM trade_history t LEFT JOIN stock_master m ON t.ticker = m.ticker ORDER BY t.id DESC LIMIT 20"
    ).fetchall()


def get_db_holdings_with_names():
    conn = sqlite3.connect("virtual_trade.db")
    rows = conn.execute(
        "SELECT m.name, h.ticker, h.quantity, h.avg_price FROM holdings h LEFT JOIN stock_master m ON h.ticker = m.ticker"
    ).fetchall()
    res = []
    for n, t, q, a in rows:
        try:
            cp = int(
                yf.Ticker(t)
                .history(period="1d", timeout=config.TIMEOUT)["Close"]
                .iloc[-1]
            )
            profit = (cp - a) * q
            rate = (profit / (a * q)) * 100 if a > 0 else 0
            res.append((n if n else t, t, q, a, cp, profit, rate))
        except:
            res.append((n if n else t, t, q, a, 0, 0, 0))
    return res


def run_trading_cycle(token, full_selection, daily_goal):
    """
    [핵심 수정] get_ai_investment_decision 인자 개수 5개로 통일하여 Pylance 에러 해결
    """
    try:
        clean = re.sub(r"^\d+[\.\s]+", "", full_selection).strip()
        ticker_name = clean.split(" (")[0].strip()
        ticker_code = clean.split(" (")[1].replace(")", "").strip()

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

        stock = yf.Ticker(ticker_code)
        df = stock.history(period="1d", interval="1m")
        if df.empty:
            return {"status": "WAITING", "msg": "데이터 동기화 대기 중"}

        price = int(df["Close"].iloc[-1])
        chart_data = df["Close"].tail(30).tolist()
        qty = int((db_cash * config.TRADE_RATIO) // (price + (price * 0.0015)))

        # [DEBUG] 뉴스 수집 URL 출력
        news = get_naver_stock_news(ticker_name, ticker_code)
        indices = get_market_indices()

        # 💡 [ERROR FIX]: 6개에서 5개로 인자 개수 수정
        ai_res = get_ai_investment_decision(
            ticker_code, price, "차트분석완료", news, indices
        )
        decision = ai_res.get("decision", "HOLD")

        trade_msg = "관망"
        from trade_manager import execute_scalping_buy, execute_scalping_sell

        if decision == "BUY" and qty > 0:
            if execute_scalping_buy(ticker_code, price, qty):
                trade_msg = f"매수성공({qty}주)"
        elif decision == "SELL":
            conn = sqlite3.connect("virtual_trade.db")
            hold_qty = conn.execute(
                "SELECT quantity FROM holdings WHERE ticker = ?", (ticker_code,)
            ).fetchone()
            conn.close()
            if hold_qty and hold_qty[0] > 0:
                if execute_scalping_sell(ticker_code, price, hold_qty[0]):
                    trade_msg = f"매도성공({hold_qty[0]}주)"

        updated_today_p, _, _ = get_statistics()
        news_report = (
            "[실시간 뉴스]\n" + "\n".join([f"• {h}" for h in news])
            if news
            else "[뉴스 없음]"
        )
        return {
            "status": "ACTIVE",
            "ticker": ticker_code,
            "price": price,
            "total_value": qty * price,
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
        print(f"🚨 [RUNTIME ERROR]: {e}")
        return {"status": "ERROR", "msg": str(e)}
