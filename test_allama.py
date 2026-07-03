import yfinance as yf
import ollama

print("1. 로컬 데이터 수집 중...")
# 삼성전자 주가 가져오기
samsung = yf.Ticker("005930.KS")
df = samsung.history(period="1d", interval="1m")
current_price = int(df['Close'].iloc[-1]) if not df.empty else 75000

print(f"   - 삼성전자 현재가: {current_price:,}원")

print("\n2. 로컬 Ollama(Llama3) 엔진 구동 테스트 중...")
prompt = f"삼성전자의 현재 주가는 {current_price:,}원입니다. 개발자 입장에서 이 데이터를 인지했음을 알리는 짧은 확인 로그 메시지를 한 줄로 출력해줘."

try:
    # 내 컴퓨터에 설치된 llama3 모델 호출
    response = ollama.chat(model='llama3', messages=[
        {
            'role': 'user',
            'content': prompt,
        },
    ])
    print(f"\n🤖 Ollama 응답:\n{response['message']['content']}")
    print("\n✅ 로컬 AI 및 데이터 연동 성공!")
except Exception as e:
    print(f"\n❌ Ollama 연동 실패. Ollama가 켜져 있는지 확인하세요. 에러 내용: {e}")
