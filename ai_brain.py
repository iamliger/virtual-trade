# ai_brain.py

import json
import re

import ollama


def get_ai_investment_decision(
    ticker, current_price, price_history_str, news_headlines
):
    # AI 가스라이팅 강화: 이유를 반드시 쓰라고 명령
    system_instruction = (
        "You are a professional stock analyst. "
        "Analyze the price data and news, then decide BUY, SELL, or HOLD. "
        "Your response MUST be a valid JSON object. "
        "**CRITICAL: The 'reason' field MUST be 1-2 sentences in Korean explaining your logic.**"
    )

    news_context = "\n".join(news_headlines) if news_headlines else "관련 뉴스 없음"
    user_message = f"Stock: {ticker}, Price: {current_price}, Trend: {price_history_str}, News: {news_context}"

    try:
        response = ollama.chat(
            model="llama3",
            messages=[
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": user_message},
            ],
            options={"temperature": 0.5},  # 약간의 창의성을 허용하여 문장을 만들게 함
        )

        ai_reply = response.get("message", {}).get("content", "").strip()
        print(f"📥 [AI 원문 응답]: {ai_reply}")

        json_match = re.search(r"\{.*\}", ai_reply, re.DOTALL)
        if json_match:
            return json.loads(json_match.group())

        return {"decision": "HOLD", "reason": "AI 답변 형식 오류로 인한 대기"}

    except Exception as e:
        return {"decision": "HOLD", "reason": f"AI 분석 중 에러: {e}"}
