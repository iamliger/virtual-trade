# main_logic.py
import sqlite3
import time
from datetime import datetime

import ollama
import yfinance as yf

from ai_brain import get_ai_investment_decision
from kis_api import get_access_token, get_mock_cash_balance
from trade_manager import execute_scalping_buy, execute_scalping_sell

SCAN_POOL = {
    "한화오션": "042660.KS",
    "두산에너빌리티": "034020.KS",
    "HMM": "011200.KS",
    "현대로템": "064350.KS",
    "HLB": "028300.KQ",
    "카카오": "035720.KS",
    "SK하이닉스": "000660.KS",
    "삼성전자": "005930.KS",
}


def setup_db():
    conn = sqlite3.connect("virtual_trade.db")
    cursor = conn.cursor()
    cursor.execute(
        """CREATE TABLE IF NOT EXISTS account (cash INTEGER, updated_at TEXT)"""
    )
    cursor.execute(
        """CREATE TABLE IF NOT EXISTS holdings (ticker TEXT PRIMARY KEY, quantity INTEGER, avg_price INTEGER)"""
    )
    cursor.execute(
        """CREATE TABLE IF NOT EXISTS trade_history (id INTEGER PRIMARY KEY AUTOINCREMENT, trade_date TEXT, ticker TEXT, type TEXT, price INTEGER, quantity INTEGER, profit INTEGER)"""
    )
    cursor.execute(
        """CREATE TABLE IF NOT EXISTS ai_log (id INTEGER PRIMARY KEY AUTOINCREMENT, log_date TEXT, ticker TEXT, decision TEXT, reason TEXT)"""
    )
    cursor.execute(
        """CREATE TABLE IF NOT EXISTS stock_master (ticker TEXT PRIMARY KEY, name TEXT)"""
    )
    conn.commit()
    conn.close()


def get_dynamic_stocks():
    setup_db()
    return [f"{name} ({ticker})" for name, ticker in SCAN_POOL.items()]


def get_db_history():
    conn = sqlite3.connect("virtual_trade.db")
    cursor = conn.cursor()
    cursor.execute(
        "SELECT trade_date, ticker, type, price, profit FROM trade_history ORDER BY id DESC LIMIT 15"
    )
    rows = cursor.fetchall()
    conn.close()
    return rows


def predict_best_stock():
    """AI 시장 예측 리포트 생성 (한글 봉인 강화)"""
    summary = ""
    for name, ticker in SCAN_POOL.items():
        try:
            stock = yf.Ticker(ticker)
            news = stock.news[:1]
            headline = (
                news[0].get("title", "특이 소식 없음") if news else "특이 소식 없음"
            )
            summary += f"- {name}: {headline}\n"
        except:
            summary += f"- {name}: 데이터 지연 중\n"

    # AI에게 '한국어'만 사용하도록 매우 강한 제약을 거는 프롬프트
    prompt = (
        "너는 한국의 펀드매니저이다. 아래 데이터를 분석해서 오늘 가장 유망한 종목 1개를 골라라.\n"
        "반드시 한국어로만 대답하고, 영어는 절대 쓰지 마라. 답변의 시작은 '오늘의 시장 분석 보고서:'로 시작하라.\n"
        f"데이터:\n{summary}"
    )
    try:
        response = ollama.chat(
            model="llama3", messages=[{"role": "user", "content": prompt}]
        )
        reply = response["message"]["content"]
        # 만약 영어가 섞여있다면 강제로 한글로 변환하는 등의 로직은 모델 성능에 의존하나,
        # 프롬프트 강화가 가장 효과적임.
        return reply
    except Exception as e:
        return f"예측 엔진 오류 발생: {str(e)}"


def run_trading_cycle(token, target_ticker, goal_amount):
    try:
        now = datetime.now()
        is_closing = now.hour == 15 and 20 <= now.minute <= 30

        stock = yf.Ticker(target_ticker)
        df = stock.history(period="1d", interval="1m")

        if df.empty:
            return {
                "status": "WAITING",
                "msg": "장이 열리기를 기다리고 있습니다. (09:00 개장)",
            }

        current_price = int(df["Close"].iloc[-1])
        recent_prices = df["Close"].tail(5).tolist()
        price_history_str = " -> ".join([f"{int(p):,}원" for p in recent_prices])

        news_data = stock.news[:3] if stock.news else []
        news_headlines = [n.get("title") for n in news_data if n.get("title")]

        if is_closing:
            decision, reason = "SELL", "🔔 장 마감 수익 확정 자동 매도 시점입니다."
        else:
            ai_res = get_ai_investment_decision(
                target_ticker, current_price, price_history_str, news_headlines
            )
            decision = ai_res.get("decision", "HOLD")
            reason = ai_res.get("reason", "분석 중")

        # 30만원 기준 매수 수량
        qty = 300000 // current_price
        if qty < 1:
            qty = 1

        trade_status = "IDLE"
        if decision == "BUY":
            if execute_scalping_buy(target_ticker, current_price, qty):
                trade_status = f"매수성공({qty}주)"
            else:
                trade_status = "매수실패(예수금부족)"
        elif decision == "SELL":
            if execute_scalping_sell(target_ticker, current_price, qty):
                trade_status = f"매도성공({qty}주)"
            else:
                trade_status = "매도실패(주식부족)"

        return {
            "status": "ACTIVE",
            "price": current_price,
            "decision": decision,
            "reason": reason,
            "news": (
                "\n".join(news_headlines) if news_headlines else "현재 실시간 뉴스 없음"
            ),
            "balance": get_mock_cash_balance(token),
            "trade_status": trade_status,
            "ticker": target_ticker,
        }
    except Exception as e:
        return {"status": "ERROR", "msg": str(e)}
