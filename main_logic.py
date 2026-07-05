import sqlite3
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


def predict_best_stock():
    summary = ""
    for name, ticker in SCAN_POOL.items():
        stock = yf.Ticker(ticker)
        news = stock.news[:1]
        headline = news[0].get("title", "특이사항 없음") if news else "특이사항 없음"
        summary += f"- {name}: {headline}\n"

    # AI에게 한글 리포트를 강제하는 프롬프트
    prompt = (
        f"너는 여의도 최고의 전략가이다. 아래 뉴스 데이터를 분석해서 "
        f"오늘 가장 유망한 섹터와 그 이유, 그리고 원픽 종목을 '한국어'로만 상세히 보고하라. "
        f"절대 영어를 섞지 말고, 한글로만 친절하고 논리적으로 설명해라.\n\n데이터:\n{summary}"
    )

    try:
        response = ollama.chat(
            model="llama3", messages=[{"role": "user", "content": prompt}]
        )
        return response["message"]["content"]
    except:
        return "종목 예측 엔진을 불러올 수 없습니다."


def get_dynamic_stocks():
    return [f"{name} ({ticker})" for name, ticker in SCAN_POOL.items()]


def get_db_history():
    conn = sqlite3.connect("virtual_trade.db")
    cursor = conn.cursor()
    cursor.execute(
        "SELECT trade_date, ticker, type, price, profit FROM trade_history ORDER BY id DESC LIMIT 10"
    )
    rows = cursor.fetchall()
    conn.close()
    return rows


def run_trading_cycle(token, target_ticker):
    try:
        now = datetime.now()
        is_closing_time = now.hour == 15 and 20 <= now.minute <= 30

        stock = yf.Ticker(target_ticker)
        df = stock.history(period="1d", interval="1m")
        if df.empty:
            return {"error": "데이터 수집 불가"}

        current_price = int(df["Close"].iloc[-1])
        recent_prices = df["Close"].tail(5).tolist()
        price_history_str = " -> ".join([f"{int(p):,}원" for p in recent_prices])

        news_data = stock.news[:3] if stock.news else []
        news_headlines = [n.get("title") for n in news_data if n.get("title")]

        if is_closing_time:
            decision, reason = "SELL", "🔔 장 마감 자동 청산"
        else:
            ai_res = get_ai_investment_decision(
                target_ticker, current_price, price_history_str, news_headlines
            )
            decision, reason = ai_res.get("decision", "HOLD"), ai_res.get(
                "reason", "분석중"
            )

        # 30만원 규모 매매
        qty = 300000 // current_price
        if qty < 1:
            qty = 1

        trade_status = "IDLE"
        if decision == "BUY" and execute_scalping_buy(
            target_ticker, current_price, qty
        ):
            trade_status = "BUY_OK"
        elif decision == "SELL" and execute_scalping_sell(
            target_ticker, current_price, qty
        ):
            trade_status = "SELL_OK"

        return {
            "price": current_price,
            "decision": decision,
            "reason": reason,
            "news": "\n".join(news_headlines) if news_headlines else "뉴스 없음",
            "balance": get_mock_cash_balance(token),
            "trade_status": trade_status,
        }
    except Exception as e:
        return {"error": str(e)}
