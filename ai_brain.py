import json

import ollama


def get_ai_investment_decision(ticker, current_price, price_history_str):
    """
    내 컴퓨터의 Ollama(Llama3) 엔진에게 주가 데이터를 주고
    [BUY(매수), SELL(매도), HOLD(관망)] 중 하나를 결정하게 하는 함수.
    """

    # 1. AI에게 부여할 정밀한 역할과 규칙 정의 (시스템 프롬프트 한글 강화 버전)
    system_instruction = (
        "You are an expert stock day-trader robot. "
        "Your job is to analyze the given stock data and make a strict decision: BUY, SELL, or HOLD. "
        "You MUST respond ONLY in valid JSON format. Do not write any markdown or introductory text. "
        "The JSON object must have exactly two keys: 'decision' and 'reason'. "
        "The value of 'decision' must be one of 'BUY', 'SELL', or 'HOLD'. "
        "**CRITICAL RULE: The value of 'reason' MUST BE WRITTEN IN KOREAN LANGUAGE ONLY.** "
        "Do not use English for the 'reason' value. Translate your thoughts into clear Korean."
    )

    # 2. AI에게 넘겨줄 실제 실시간 주가 데이터 조립
    user_message = (
        f"Stock Ticker: {ticker}\n"
        f"Current Price: {current_price:,} KRW\n"
        f"Recent 5-minute price trend: {price_history_str}\n"
        f"Please analyze this data and give me your JSON decision now."
    )

    print(f"\n🤖 [AI 브레인] Llama3에게 {ticker} 분석을 요청하는 중...")

    try:
        # 3. 로컬 Ollama 호출
        response = ollama.chat(
            model="llama3",
            messages=[
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": user_message},
            ],
        )

        # AI가 준 답변 텍스트 추출
        ai_reply = response["message"]["content"].strip()

        # 4. 안전장치: AI가 JSON 외에 쓸데없는 문자를 붙였을 경우를 대비한 파싱
        # (만약 ```json ... ``` 형식으로 감싸왔다면 순수 JSON만 발라냅니다)
        if "{" in ai_reply and "}" in ai_reply:
            start_idx = ai_reply.find("{")
            end_idx = ai_reply.rfind("}") + 1
            ai_reply = ai_reply[start_idx:end_idx]

        # 텍스트를 파이썬 딕셔너리로 변환
        decision_data = json.loads(ai_reply)
        return decision_data

    except Exception as e:
        print(f"❌ [AI 브레인 에러] Llama3 연동 중 오류 발생: {e}")
        # 에러 발생 시 안전하게 'HOLD(관망)' 상태를 반환하여 자산을 보호합니다.
        return {
            "decision": "HOLD",
            "reason": f"AI 통신 에러 발생으로 자산 보호 관망 처리 ({e})",
        }
