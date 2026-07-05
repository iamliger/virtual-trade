# ai_brain.py (전체 교체)

import json

import ollama


def get_ai_investment_decision(
    ticker, current_price, price_history_str, news_headlines
):
    """
    주가 데이터와 최신 뉴스 헤드라인을 종합하여 최종 투자 결정을 내리는 함수
    """

    system_instruction = (
        "You are an expert stock day-trader and news analyst. "
        "Analyze both the price trend AND the news headlines provided. "
        "Determine the impact of news on the stock's future movement. "
        "You MUST respond ONLY in valid JSON format. "
        "The JSON object must have: 'decision' (BUY, SELL, HOLD) and 'reason'. "
        "**CRITICAL RULE: The 'reason' MUST BE IN KOREAN.** "
        "In the 'reason', briefly mention how the news influenced your decision."
    )

    # 뉴스가 없을 경우를 대비한 처리
    news_context = (
        "\n".join(news_headlines) if news_headlines else "최근 관련 뉴스 없음"
    )

    user_message = (
        f"Stock: {ticker}\n"
        f"Current Price: {current_price:,} KRW\n"
        f"Recent Trend: {price_history_str}\n"
        f"Latest News Headlines:\n{news_context}\n"
        f"Please give me your decision (BUY/SELL/HOLD) in JSON."
    )

    print(f"🧠 [AI 분석] {ticker}의 차트와 뉴스를 종합 분석 중...")

    try:
        response = ollama.chat(
            model="llama3",
            messages=[
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": user_message},
            ],
        )

        ai_reply = response["message"]["content"].strip()

        if "{" in ai_reply and "}" in ai_reply:
            start_idx = ai_reply.find("{")
            end_idx = ai_reply.rfind("}") + 1
            ai_reply = ai_reply[start_idx:end_idx]

        return json.loads(ai_reply)

    except Exception as e:
        return {"decision": "HOLD", "reason": f"AI 분석 중 에러 발생: {e}"}
