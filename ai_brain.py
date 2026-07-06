import json
import re

import ollama


def get_ai_investment_decision(
    ticker, current_price, price_history_str, news_headlines
):
    """100% 한국어 및 소액 투자 최적화 분석"""
    system_instruction = (
        "너는 한국 최고의 주식 단타 전문가이다. 규칙을 엄격히 지켜라.\n"
        "1. 모든 답변은 오직 '한국어'로만 작성한다. 영어는 단 한 단어도 사용하지 마라.\n"
        '2. 출력은 무조건 JSON 형식이다: {"decision": "BUY/SELL/HOLD", "reason": "한글 상세 이유"}\n'
        "3. 현재 자본금이 적으므로, 리스크를 최소화하는 보수적인 단타 전략을 취하라."
    )
    news_text = "\n".join(news_headlines) if news_headlines else "특이 뉴스 없음."
    user_message = f"종목: {ticker}, 현재가: {current_price}원, 추세: {price_history_str}, 뉴스: {news_text}"

    try:
        response = ollama.chat(
            model="llama3",
            messages=[
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": user_message},
            ],
            options={"temperature": 0.1},
        )
        ai_reply = response.get("message", {}).get("content", "").strip()
        json_match = re.search(r"\{.*\}", ai_reply, re.DOTALL)
        if json_match:
            return json.loads(json_match.group())
        return {"decision": "HOLD", "reason": "AI 분석 결과 해석 불가."}
    except Exception as e:
        return {"decision": "HOLD", "reason": f"AI 분석 에러: {str(e)}"}
