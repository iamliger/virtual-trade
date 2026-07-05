import time

import yfinance as yf

from ai_brain import get_ai_investment_decision
from kis_api import get_access_token, get_mock_cash_balance
from trade_manager import execute_scalping_buy, execute_scalping_sell

# [설정] 투자할 종목과 한 번에 살 수량
TARGET_TICKER = "005930.KS"  # 삼성전자
TRADE_QUANTITY = 5  # 한 번에 5주씩


def main():
    print("🚀 [시스템] 로컬 AI 자동 매매 엔진을 시작합니다.")

    # 1. 증권사 서버 연결 및 토큰 발급
    print("🌐 [증권사] 한국투자증권 모의투자 서버에 접속 중...")
    token = get_access_token()

    if not token:
        print("❌ [에러] 토큰 발급 실패. .env 파일이나 네트워크를 확인하세요.")
        return

    # 2. 증권사 실제 가상 예수금 확인
    mock_balance = get_mock_cash_balance(token)
    print(f"💰 [잔고 확인] 증권사 가상 예수금: {mock_balance:,}원")
    print(f"📅 [상태] 내일(월요일) 장 개시 준비 완료!")
    print("-" * 50)

    while True:
        try:
            print(f"\n🔍 [{time.strftime('%H:%M:%S')}] 시장 스캐닝 시작...")

            # 3. 실시간 주가 및 뉴스 데이터 가져오기
            stock = yf.Ticker(TARGET_TICKER)
            df = stock.history(period="1d", interval="1m")

            # [추가] 뉴스 헤드라인 가져오기 (최신 3개만)
            news_data = stock.news[:3]
            news_headlines = [item["title"] for item in news_data]

            if df.empty:
                print("⚠️ 시장 데이터 대기 중...")
                time.sleep(60)
                continue

            current_price = int(df["Close"].iloc[-1])
            recent_prices = df["Close"].tail(5).tolist()
            price_history_str = " -> ".join([f"{int(p):,}원" for p in recent_prices])

            # 4. AI 브레인에게 판단 요청 (뉴스 전달 추가)
            ai_result = get_ai_investment_decision(
                TARGET_TICKER, current_price, price_history_str, news_headlines
            )

            decision = ai_result.get("decision")
            reason = ai_result.get("reason")

            print(f"🤖 [AI 판단] 결정: **{decision}**")
            print(f"💡 [AI 이유] {reason}")

            # 5. 판단에 따른 실제 가상 거래 실행
            if decision == "BUY":
                execute_scalping_buy(TARGET_TICKER, current_price, TRADE_QUANTITY)
            elif decision == "SELL":
                execute_scalping_sell(TARGET_TICKER, current_price, TRADE_QUANTITY)
            else:
                print("😴 [관망] AI가 현재는 지켜보기를 권장합니다.")

            print("-" * 50)
            # 6. 1분 대기 (단타 주기에 맞춰 설정)
            print("⏳ 1분간 시장을 모니터링하며 대기합니다...")
            time.sleep(60)

        except Exception as e:
            print(f"🚨 [루프 에러] 작동 중 오류 발생: {e}")
            time.sleep(10)  # 에러 발생 시 잠시 쉬었다가 재시도


if __name__ == "__main__":
    main()
