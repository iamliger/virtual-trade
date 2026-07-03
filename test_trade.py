import time

import yfinance as yf

from trade_manager import execute_scalping_buy, execute_scalping_sell

print("1. 실시간 주가를 가져옵니다...")
samsung = yf.Ticker("005930.KS")
df = samsung.history(period="1d", interval="1m")

if not df.empty:
    current_price = int(df["Close"].iloc[-1])

    print(f"   - 삼성전자 현재가: {current_price:,}원")

    print("\n2. [테스트 1] 10주를 가상 매수합니다.")
    execute_scalping_buy("005930.KS", current_price, quantity=10)

    # 단타의 긴박함을 시뮬레이션하기 위해 2초간 대기
    print("\n⏰ 2초간 단타 타이밍 노리는 중...")
    time.sleep(2)

    # 가격이 살짝 변동되었다고 가정하거나 실시간가로 전량 매도 테스트
    print("\n3. [테스트 2] 보유한 10주를 즉시 전량 매도(단타 종료)합니다.")
    execute_scalping_sell("005930.KS", current_price, quantity=10)

else:
    print("❌ 데이터를 가져오지 못했습니다.")
