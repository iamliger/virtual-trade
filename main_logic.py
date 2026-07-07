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

# 404 유발 종목을 제거한 정제된 후보군
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
    """Ollama 서버 구동 확인"""
    try:
        requests.get("http://localhost:11434/api/tags", timeout=2)
        return True
    except:
        return False


def get_market_indices():
    """KOSPI, KOSDAQ 지수 정보 (kd_change 에러 수정 완료)"""
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
        return "시장 지수 실시간 동기화 중..."


def get_kr_realtime_news(ticker_name):
    """네이버 금융 기반 한글 실시간 뉴스 수집"""
    try:
        url = f"https://search.naver.com/search.naver?where=news&query={ticker_name}"
        headers = {"User-Agent": "Mozilla/5.0"}
        res = requests.get(url, headers=headers)
        soup = BeautifulSoup(res.text, "html.parser")
        return [a.text for a in soup.select(".news_tit")[:3]]
    except:
        return []


def refresh_stock_pool_by_capital():
    """자본금에 맞는 종목 동적 발굴 및 DB 업데이트"""
    conn = sqlite3.connect("virtual_trade.db")
    cash = conn.execute("SELECT cash FROM account").fetchone()[0]
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
    """전체 시장 및 핵심 종목 예측 보고서"""
    conn = sqlite3.connect("virtual_trade.db")
    stocks = conn.execute("SELECT name, ticker FROM stock_master LIMIT 3").fetchall()
    conn.close()
    summary = "\n".join([f"- {s[0]}({s[1]})" for s in stocks])
    indices = get_market_indices()
    prompt = f"너는 한국 최고의 수석 전략가이다. 한국어로 현재 지수 {indices}와 종목군 {summary}를 기반으로 오늘 단타 전략을 상세히 보고하라. 영어 금지."
    try:
        res = ollama.chat(
            model="llama3",
            messages=[{"role": "user", "content": prompt}],
            options={"temperature": 0.1},
        )
        reply = res["message"]["content"]
        # 영어가 대량 포함된 경우 사후 처리
        return (
            reply
            if not re.search("[a-zA-Z]{15,}", reply)
            else "시장 지수 변동성이 확대되고 있습니다. 가용 자본금 내에서 분할 매수 관점으로 접근하시기 바랍니다."
        )
    except:
        return "예측 엔진 일시적 연결 지연"


def get_db_history():
    """최근 매매 히스토리 조회 (gui_app.py 필수 함수)"""
    conn = sqlite3.connect("virtual_trade.db")
    cursor = conn.cursor()
    cursor.execute(
        "SELECT trade_date, ticker, type, price, quantity, profit FROM trade_history ORDER BY id DESC LIMIT 20"
    )
    rows = cursor.fetchall()
    conn.close()
    return rows


def get_db_holdings_with_names():
    """보유 종목 현황에 종목명 매칭 및 평가 손익 계산"""
    conn = sqlite3.connect("virtual_trade.db")
    cursor = conn.cursor()
    cursor.execute(
        "SELECT h.ticker, h.quantity, h.avg_price, m.name FROM holdings h LEFT JOIN stock_master m ON h.ticker = m.ticker"
    )
    rows = cursor.fetchall()
    conn.close()
    res = []
    for t, q, a, n in rows:
        try:
            name = n if n else t
            cp = int(yf.Ticker(t).history(period="1d")["Close"].iloc[-1])
            profit = (cp - a) * q
            rate = (profit / (a * q)) * 100 if a > 0 else 0
            res.append((name, t, q, a, cp, profit, rate))
        except:
            res.append(("정보지연", t, q, a, 0, 0, 0))
    return res


def run_trading_cycle(token, target_ticker, daily_goal):
    """실시간 매매 엔진 루프 사이클"""
    try:
        today_p, week_p, month_p = get_statistics()
        conn = sqlite3.connect("virtual_trade.db")
        db_cash = conn.execute("SELECT cash FROM account").fetchone()[0]
        conn.close()

        # [수익 목표 달성 여부 체크]
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

        # 자산 부족 감지
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
                "reason": "현재 가용 자산으로 매수 불가",
                "news": "없음",
                "chart": chart_data,
            }

        # 뉴스 및 지수 기반 판단
        news = get_kr_realtime_news(target_ticker.split(".")[0])
        indices = get_market_indices()
        ai_res = get_ai_investment_decision(
            target_ticker, price, "실시간 차트 분석 완료", news, indices
        )
        decision = ai_res.get("decision", "HOLD")

        # 가용 자본 전체 투입
        qty = db_cash // (price + (price * 0.001))

        trade_msg = "관망"
        if decision == "BUY" and qty > 0:
            if execute_scalping_buy(target_ticker, price, qty):
                trade_msg = f"매수성공({qty}주)"
        elif decision == "SELL":
            conn = sqlite3.connect("virtual_trade.db")
            hold_qty = conn.execute(
                "SELECT quantity FROM holdings WHERE ticker = ?", (target_ticker,)
            ).fetchone()
            conn.close()
            if hold_qty and hold_qty[0] > 0:
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
