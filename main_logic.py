# main_logic.py
import sqlite3
from datetime import datetime

import yfinance as yf

from ai_brain import get_ai_investment_decision
from kis_api import get_access_token, get_mock_cash_balance
from trade_manager import execute_scalping_buy, execute_scalping_sell

# [수정] 단타(스캘핑) 수익을 내기 좋은 1~8만원대 활동성 종목 리스트
WATCH_LIST = {
    "한화오션": "042660.KS",  # 조선/방산 (변동성 좋음)
    "두산에너빌리티": "034020.KS",  # 원전/에너지 (거래량 상위)
    "카카오": "035720.KS",  # IT 대표주 (변동폭 존재)
    "HMM": "011200.KS",  # 해운/물류 (1만원대 적정가)
    "현대로템": "064350.KS",  # 철도/방산 (추세 명확함)
    "HLB": "028300.KQ",  # 바이오 (단타의 꽃, 고변동성)
}


def run_trading_cycle(token, target_ticker):
    try:
        stock = yf.Ticker(target_ticker)
        df = stock.history(period="1d", interval="1m")

        if df.empty:
            return {"error": f"{target_ticker} 데이터 수집 불가"}

        current_price = int(df["Close"].iloc[-1])
        recent_prices = df["Close"].tail(5).tolist()
        price_history_str = " -> ".join([f"{int(p):,}원" for p in recent_prices])

        # 뉴스 수집 및 가공
        raw_news = stock.news[:5] if stock.news else []
        news_headlines = [item.get("title") for item in raw_news if item.get("title")]
        display_news = (
            "\n".join([f"• {h}" for h in news_headlines])
            if news_headlines
            else "• 현재 특이 뉴스 없음"
        )

        # AI 판단 (단타 전략 강조)
        ai_result = get_ai_investment_decision(
            target_ticker, current_price, price_history_str, news_headlines
        )
        decision = ai_result.get("decision", "HOLD")
        reason = ai_result.get("reason", "분석 중...")

        # [수정] 자금 상황에 맞춰 매수 수량 조절 (예: 한 번에 약 100만원치 매수)
        # 만약 돈이 부족하면 1주씩이라도 사도록 설정
        buy_quantity = max(1, 1000000 // current_price)

        if decision == "BUY":
            execute_scalping_buy(target_ticker, current_price, quantity=buy_quantity)
        elif decision == "SELL":
            # 매도는 보유한 만큼 전량 매도 시도 (단타 원칙)
            execute_scalping_sell(target_ticker, current_price, quantity=buy_quantity)

        # DB 기록
        conn = sqlite3.connect("virtual_trade.db")
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO ai_log (log_date, ticker, decision, reason) VALUES (?, ?, ?, ?)",
            (
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                target_ticker,
                decision,
                reason,
            ),
        )
        conn.commit()
        conn.close()

        return {
            "ticker": target_ticker,
            "price": current_price,
            "decision": decision,
            "reason": reason,
            "news": display_news,
            "balance": get_mock_cash_balance(token),
        }
    except Exception as e:
        return {"error": str(e)}
