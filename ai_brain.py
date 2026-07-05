# ai_brain.py

import json

import ollama


def get_ai_investment_decision(
    ticker, current_price, price_history_str, news_headlines
):
    # 1. 시스템 프롬프트(AI의 역할)를 더 구체화합니다.
    system_instruction = (
        "You are a professional stock analyst. "
        "Review the provided stock price data and news carefully. "
        "Your final output must be a JSON object with 'decision' and 'reason'. "
        "**CRITICAL RULE 1: The 'reason' must be a logical, complete sentence in Korean.** "
        "**CRITICAL RULE 2: Avoid broken characters. Use standard business Korean.**"
    )

    # 2. AI가 더 똑똑하게 생각할 수 있도록 뉴스 내용을 정돈합니다.
    news_context = ""
    for i, title in enumerate(news_headlines):
        news_context += f"{i+1}. {title}\n"

    # 3. 사용자 메시지 (데이터 전달)
    user_message = (
        f"Analyze the following data for {ticker}:\n"
        f"- Current Price: {current_price:,} KRW\n"
        f"- Recent 5-min Trend: {price_history_str}\n"
        f"- Recent News:\n{news_context}\n"
        "What is your decision? (BUY/SELL/HOLD)"
    )

    try:
        # 4. Ollama를 호출할 때 'options'를 추가하여 창의성을 조절합니다.
        response = ollama.chat(
            model="llama3",
            messages=[
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": user_message},
            ],
            options={
                "temperature": 0.3
            },  # 0.3으로 낮추면 AI가 헛소리를 덜 하고 더 차분해집니다.
        )

        ai_reply = response["message"]["content"].strip()

        # JSON 파싱 안전장치
        if "{" in ai_reply and "}" in ai_reply:
            start_idx = ai_reply.find("{")
            end_idx = ai_reply.rfind("}") + 1
            ai_reply = ai_reply[start_idx:end_idx]

        return json.loads(ai_reply)

    except Exception as e:
        return {"decision": "HOLD", "reason": f"AI 분석 오류: {e}"}
