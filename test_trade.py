import yfinance as yf

from ai_brain import get_ai_investment_decision
from trade_manager import execute_scalping_buy, execute_scalping_sell

print("1. 실시간 한국 주식 시장 데이터(삼성전자)를 조회합니다...")
samsung = yf.Ticker("005930.KS")
# 최근 5분간의 흐름을 보기 위해 5일치 데이터를 분 단위로 가져옵니다.
df = samsung.history(period="5d", interval="1m")

if not df.empty:
    # 가장 마지막 행의 가격이 '현재가'가 됩니다.
    current_price = int(df["Close"].iloc[-1])

    # 최근 5분간의 주가 흐름을 문자열로 이쁘게 가공하여 AI에게 줄 준비를 합니다.
    recent_prices = df["Close"].tail(5).tolist()
    price_history_str = " -> ".join([f"{int(p):,}원" for p in recent_prices])

    print(f"   - 삼성전자 현재가: {current_price:,}원")
    print(f"   - 최근 5분간의 주가 흐름 데이터: [{price_history_str}]")

    print("\n2. 수집된 데이터를 로컬 AI(Llama3)에게 던져 판단을 의뢰합니다.")
    # AI 브레인 작동!
    ai_result = get_ai_investment_decision(
        "005930.KS", current_price, price_history_str
    )

    # 3. AI가 내린 결론(JSON 데이터)을 화면에 출력합니다.
    decision = ai_result.get("decision")
    reason = ai_result.get("reason")

    print(f"\n📊 [AI 판단 결과 리포트]")
    print(f"   - 최종 결정: **{decision}**")
    print(f"   - 결정 근거(이유): {reason}")

    # 4. AI의 결정에 따라 우리가 만든 가상 계좌 연동 함수를 실행합니다!
    if decision == "BUY":
        print("\n🤖 AI의 지시에 따라 가상 매수를 진행합니다.")
        execute_scalping_buy("005930.KS", current_price, quantity=5)
    elif decision == "SELL":
        print("\n🤖 AI의 지시에 따라 가상 매도를 진행합니다.")
        execute_scalping_sell("005930.KS", current_price, quantity=5)
    else:
        print("\n🤖 AI가 관망(HOLD)을 지시하여 아무런 거래도 하지 않고 대기합니다.")

else:
    print("❌ 주가 데이터를 가져오지 못했습니다. 인터넷 연결을 확인하세요.")
